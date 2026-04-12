from __future__ import annotations

import base64
import io
from decimal import Decimal
from typing import cast

import qrcode
import weasyprint
from django.http import HttpResponse
from django.template import Context, Template


def _fmt_inr(value) -> str:
    if value is None:
        value = "0"
    val = str(value).replace(",", "").strip()
    try:
        number = Decimal(val)
    except (ArithmeticError, TypeError, ValueError):
        number = Decimal("0")
    sign = "-" if number < 0 else ""
    abs_num = abs(number)
    int_part = int(abs_num)
    dec_part = str(abs_num - int_part)[2:]
    dec_part = dec_part.ljust(2, "0")[:2]
    int_formatted = f"{int_part:,}"
    return f"{sign}₹.{int_formatted}.{dec_part}"


def _mask_pan(pan: str) -> str:
    if not pan or len(pan) < 10:
        return pan
    return pan[:5] + "****" + pan[-1]


def _build_qr_code_data(payslip_id: str, employee_code: str, net_pay: str, period_label: str) -> str:
    return "CLARISAL|" + payslip_id + "|" + employee_code + "|" + period_label + "|NET:" + net_pay


def _generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _load_template() -> Template:
    from apps.payroll.templates.payroll.payslip import payslip_template_source
    return Template(payslip_template_source)


def _resolve_employee_meta(employee):
    user = employee.user
    designation_name = (
        employee.designation_ref.name if employee.designation_ref_id else employee.designation or ""
    )
    department_name = employee.department.name if employee.department_id else ""
    pan = getattr(user, "pan_number", "") or ""
    uan = getattr(employee, "uan_number", "") or "N/A"
    esi = getattr(employee, "esic_ip_number", "") or "N/A"
    return {
        "designation": designation_name,
        "department": department_name,
        "pan": _mask_pan(pan),
        "uan": uan,
        "esi_ip": esi,
    }


def _merge_snapshot(payslip):
    item_snapshot = payslip.pay_run_item.snapshot or {}
    payslip_snapshot = payslip.snapshot or {}
    return {**item_snapshot, **payslip_snapshot}


def _build_earnings_rows(snapshot):
    lines = snapshot.get("lines", [])
    rows = []
    for line in lines:
        if line.get("component_type") == "EARNING":
            rows.append({"name": line.get("component_name", ""), "amount": _fmt_inr(line.get("monthly_amount", "0"))})
    arrears = snapshot.get("arrears", "0")
    if arrears and Decimal(str(arrears).replace(",", "")) > Decimal("0"):
        rows.append({"name": "Arrears", "amount": _fmt_inr(arrears)})
    return rows


def _build_deductions_rows(snapshot):
    lines = snapshot.get("lines", [])
    rows = []
    for line in lines:
        if line.get("component_type") == "EMPLOYEE_DEDUCTION" and line.get("component_code") not in ("", None):
            rows.append({"name": line.get("component_name", ""), "amount": _fmt_inr(line.get("monthly_amount", "0"))})
    lop_deduction = snapshot.get("lop_deduction", "0")
    if lop_deduction and Decimal(str(lop_deduction).replace(",", "")) > Decimal("0"):
        rows.append({"name": "LOP (" + str(snapshot.get("lop_days", "0")) + " day(s))", "amount": _fmt_inr(lop_deduction)})
    income_tax = snapshot.get("income_tax", "0")
    rows.append({"name": "TDS (Income Tax)", "amount": _fmt_inr(income_tax)})
    return rows


def _build_employer_rows(snapshot):
    lines = snapshot.get("lines", [])
    rows = []
    for line in lines:
        if line.get("component_type") == "EMPLOYER_CONTRIBUTION" and line.get("component_code") not in ("", None):
            rows.append({"name": line.get("component_name", ""), "amount": _fmt_inr(line.get("monthly_amount", "0"))})
    return rows


def _build_tax_summary(snapshot):
    rows = []
    ann_gross = snapshot.get("annual_taxable_gross")
    if ann_gross:
        rows.append({"label": "Gross Taxable Income", "value": _fmt_inr(ann_gross)})
        rows.append({"label": "Less: Standard Deduction", "value": _fmt_inr(snapshot.get("annual_standard_deduction", "0"))})
        rows.append({"label": "Net Taxable Income", "value": _fmt_inr(snapshot.get("annual_taxable_after_sd", "0"))})
        rows.append({"label": "Income Tax (as per slabs)", "value": _fmt_inr(snapshot.get("annual_tax_before_rebate", "0"))})
        if Decimal(str(snapshot.get("annual_surcharge", "0")).replace(",", "")) > Decimal("0"):
            rows.append({"label": "Surcharge", "value": _fmt_inr(snapshot.get("annual_surcharge", "0"))})
        rows.append({"label": "Health & Education Cess (4%)", "value": _fmt_inr(snapshot.get("annual_cess", "0"))})
        rows.append({"label": "Total Annual Tax (TDS)", "value": _fmt_inr(snapshot.get("annual_tax_total", "0"))})
    return rows


def generate_payslip_pdf_bytes(payslip) -> bytes:
    merged = _merge_snapshot(payslip)
    org = payslip.organisation
    employee = payslip.employee
    user = employee.user
    emp_meta = _resolve_employee_meta(employee)

    period_label = merged.get("period_label", str(payslip.period_year))
    paid_days = str(merged.get("paid_days", ""))
    total_days = str(merged.get("total_days_in_period", ""))
    days_detail = ""
    if paid_days and total_days:
        days_detail = paid_days + " of " + total_days + " days"

    earnings_rows = _build_earnings_rows(merged)
    deductions_rows = _build_deductions_rows(merged)
    employer_rows = _build_employer_rows(merged)
    tax_rows = _build_tax_summary(merged)

    qr_data = _build_qr_code_data(
        str(payslip.id),
        employee.employee_code or "",
        _fmt_inr(merged.get("net_pay", "0")),
        period_label,
    )
    qr_base64 = _generate_qr_base64(qr_data)

    context = Context({
        "org_name": org.name,
        "org_logo_url": org.logo_url or "",
        "org_address": org.address or "",
        "org_cin": getattr(org, "cin_number", "") or "",
        "period_label": period_label,
        "slip_number": payslip.slip_number,
        "payment_date": payslip.created_at.strftime("%d %b %Y") if payslip.created_at else "",
        "employee_name": user.full_name,
        "employee_code": employee.employee_code or "",
        "designation": emp_meta["designation"],
        "department": emp_meta["department"],
        "pan": emp_meta["pan"],
        "uan": emp_meta["uan"],
        "esi_ip": emp_meta["esi_ip"],
        "tax_regime": merged.get("tax_regime", "NEW"),
        "days_detail": days_detail,
        "gross_salary": _fmt_inr(merged.get("gross_pay", "0")),
        "total_deductions": _fmt_inr(merged.get("total_deductions", "0")),
        "net_pay": _fmt_inr(merged.get("net_pay", "0")),
        "earnings_rows": earnings_rows,
        "deductions_rows": deductions_rows,
        "employer_rows": employer_rows,
        "tax_rows": tax_rows,
        "qr_base64": qr_base64,
    })

    template = _load_template()
    html = template.render(context)
    pdf_bytes = cast(bytes, weasyprint.HTML(string=html).write_pdf())
    return pdf_bytes


def download_payslip_pdf_response(payslip, *, filename=None) -> HttpResponse:
    pdf_bytes = generate_payslip_pdf_bytes(payslip)
    if filename is None:
        safe_slip = payslip.slip_number.replace("/", "-")
        filename = safe_slip + ".pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="' + filename + '"'
    return response
