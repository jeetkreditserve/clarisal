from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import weasyprint
from django.template import Context, Template

from . import FilingGenerationResult, decimal_to_string, get_employee_identifier

FORM_12BB_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  @page { size: A4; margin: 1cm; }
  body { font-family: Arial, sans-serif; font-size: 10pt; color: #000; margin: 0; padding: 0; }
  .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 12px; }
  .header h1 { font-size: 16pt; margin: 0; }
  .header h2 { font-size: 12pt; margin: 4px 0; }
  .meta-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 9pt; }
  .meta-table td { padding: 3px 6px; vertical-align: top; }
  .meta-table .label { font-weight: bold; width: 140px; }
  .section-title { background: #d0d0d0; font-weight: bold; padding: 4px 6px; border: 1px solid #666; font-size: 10pt; }
  .data-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 9pt; }
  .data-table th, .data-table td { border: 1px solid #666; padding: 4px 6px; text-align: left; }
  .data-table th { background: #e8e8e8; font-weight: bold; }
  .data-table .col-amount { text-align: right; width: 120px; }
  .col-sno { width: 30px; text-align: center; }
  .col-desc { width: auto; }
  .col-proof { width: 80px; text-align: center; }
  .subsection-title { background: #f0f0f0; font-weight: bold; padding: 3px 6px; border: 1px solid #999; margin-top: 8px; font-size: 9pt; }
  .declaration-box { border: 1px solid #666; padding: 8px; margin-top: 12px; background: #fafafa; }
  .declaration-box p { margin: 4px 0; font-size: 9pt; }
  .signature-row { margin-top: 30px; display: flex; justify-content: space-between; }
  .signature-block { width: 45%; }
  .signature-block .place { margin-bottom: 30px; border-bottom: 1px solid #666; height: 20px; }
  .signature-block .name { font-weight: bold; }
  .signature-block .date { font-size: 9pt; color: #444; }
  .footer-note { font-size: 8pt; color: #666; margin-top: 12px; text-align: center; }
  .empty-section { font-style: italic; color: #888; padding: 8px; }
  .summary-box { border: 1px solid #666; padding: 8px; margin-bottom: 10px; background: #f5f5f5; }
  .summary-box table { width: auto; margin: 0 auto; border-collapse: collapse; }
  .summary-box td { padding: 2px 12px; }
  .summary-box .total-label { font-weight: bold; text-align: right; }
  .summary-box .total-value { font-weight: bold; text-align: right; }
  .warn { color: #c00; font-weight: bold; }
</style>
</head>
<body>
<div class="header">
  <h1>Form 12BB</h1>
  <h2>Statement of declarations under Section 192(2) for claiming deduction(s) from salary</h2>
</div>

<table class="meta-table">
  <tr>
    <td class="label">Financial Year:</td>
    <td>{{ fiscal_year }}</td>
    <td class="label">Assessment Year:</td>
    <td>{{ assessment_year }}</td>
  </tr>
  <tr>
    <td class="label">Employee Name:</td>
    <td>{{ employee_name }}</td>
    <td class="label">PAN:</td>
    <td>{{ employee_pan }}</td>
  </tr>
  <tr>
    <td class="label">Employer Name:</td>
    <td>{{ employer_name }}</td>
    <td class="label">TAN:</td>
    <td>{{ employer_tan }}</td>
  </tr>
  <tr>
    <td class="label">Employer Address:</td>
    <td colspan="3">{{ employer_address }}</td>
  </tr>
</table>

{# Section A: HRA #}
<div class="section-title">Section A: House Rent Allowance (HRA)</div>
{% if hra_rows %}
  <table class="data-table">
    <thead>
      <tr>
        <th class="col-sno">S.No.</th>
        <th class="col-desc">Landlord Name</th>
        <th>PAN of Landlord</th>
        <th>Address of Landlord</th>
        <th class="col-amount">Rent Amount (Rs.)</th>
        <th class="col-proof">PAN Attached</th>
      </tr>
    </thead>
    <tbody>
      {% for row in hra_rows %}
      <tr>
        <td class="col-sno">{{ forloop.counter }}</td>
        <td>{{ row.landlord_name }}</td>
        <td>{{ row.landlord_pan }}</td>
        <td>{{ row.landlord_address }}</td>
        <td class="col-amount">{{ row.amount }}</td>
        <td class="col-proof">{{ row.pan_attached|default:"—" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <div class="empty-section">No HRA declarations submitted.</div>
{% endif %}

{# Section B: LTA #}
<div class="section-title">Section B: Leave Travel Allowance (LTA)</div>
{% if lta_rows %}
  <table class="data-table">
    <thead>
      <tr>
        <th class="col-sno">S.No.</th>
        <th>Bill No./Reference</th>
        <th>Description (Place of Travel)</th>
        <th>Date of Travel</th>
        <th class="col-amount">Amount Claimed (Rs.)</th>
        <th class="col-proof">Bill Attached</th>
      </tr>
    </thead>
    <tbody>
      {% for row in lta_rows %}
      <tr>
        <td class="col-sno">{{ forloop.counter }}</td>
        <td>{{ row.reference|default:"—" }}</td>
        <td>{{ row.description }}</td>
        <td>{{ row.travel_date|default:"—" }}</td>
        <td class="col-amount">{{ row.amount }}</td>
        <td class="col-proof">{{ row.bill_attached|default:"—" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <div class="empty-section">No LTA declarations submitted.</div>
{% endif %}

{# Section C: Interest on Home Loan #}
<div class="section-title">Section C: Deduction for Interest on Home Loan (Section 24)</div>
{% if home_loan_rows %}
  <table class="data-table">
    <thead>
      <tr>
        <th class="col-sno">S.No.</th>
        <th>Name of Lender</th>
        <th>Lender Type</th>
        <th>PAN of Lender (if applicable)</th>
        <th class="col-amount">Interest Paid (Rs.)</th>
        <th class="col-proof">Certificate Attached</th>
      </tr>
    </thead>
    <tbody>
      {% for row in home_loan_rows %}
      <tr>
        <td class="col-sno">{{ forloop.counter }}</td>
        <td>{{ row.lender_name }}</td>
        <td>{{ row.lender_type|default:"Financial Institution" }}</td>
        <td>{{ row.lender_pan|default:"—" }}</td>
        <td class="col-amount">{{ row.amount }}</td>
        <td class="col-proof">{{ row.certificate_attached|default:"—" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <div class="empty-section">No home loan interest declarations submitted.</div>
{% endif %}

{# Section D: Chapter VI-A Deductions #}
<div class="section-title">Section D: Other Deductions under Chapter VI-A</div>
{% if chapter_via_rows %}
  <table class="data-table">
    <thead>
      <tr>
        <th class="col-sno">S.No.</th>
        <th>Section</th>
        <th>Description</th>
        <th class="col-amount">Amount Claimed (Rs.)</th>
        <th class="col-proof">Proof Attached</th>
      </tr>
    </thead>
    <tbody>
      {% for row in chapter_via_rows %}
      <tr>
        <td class="col-sno">{{ forloop.counter }}</td>
        <td>{{ row.section }}</td>
        <td>{{ row.description }}</td>
        <td class="col-amount">{{ row.amount }}</td>
        <td class="col-proof">{{ row.proof_attached|default:"—" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <div class="empty-section">No Chapter VI-A declarations submitted.</div>
{% endif %}

{# Summary #}
<div class="summary-box">
  <strong>Declaration Summary</strong>
  <table>
    <tr><td>HRA Total:</td><td class="total-value">{{ hra_total }}</td></tr>
    <tr><td>LTA Total:</td><td class="total-value">{{ lta_total }}</td></tr>
    <tr><td>Home Loan Interest Total:</td><td class="total-value">{{ home_loan_total }}</td></tr>
    <tr><td>Chapter VI-A Deductions Total:</td><td class="total-value">{{ chapter_via_total }}</td></tr>
    <tr>
      <td class="total-label">Grand Total Declared:</td>
      <td class="total-value">{{ grand_total }}</td>
    </tr>
  </table>
</div>

{# Declaration #}
<div class="declaration-box">
  <strong>Declaration under Section 192(2)</strong>
  <p>I hereby declare that the above statements are true and correct to the best of my knowledge and belief.
     I undertake to inform the employer immediately if there is any change in the above information.</p>
  <div class="signature-row">
    <div class="signature-block">
      <div class="place">{{ declaration_date|default:"________________" }}</div>
      <div>Date</div>
    </div>
    <div class="signature-block">
      <div class="place">&nbsp;</div>
      <div>Employee Signature</div>
      <div class="name">{{ employee_name }}</div>
      <div class="date">Employee Code: {{ employee_code }}</div>
    </div>
  </div>
</div>

<div class="footer-note">
  This is a computer-generated Form 12BB. No signature required as per e-filing guidelines.
  Generated on {{ generated_date }} for FY {{ fiscal_year }}.
</div>
</body>
</html>
"""


@dataclass(slots=True)
class Form12BBSectionRow:
    section: str
    description: str
    amount: Decimal
    proof_attached: str = ""
    landlord_name: str = ""
    landlord_pan: str = ""
    landlord_address: str = ""
    reference: str = ""
    travel_date: str = ""
    lender_name: str = ""
    lender_type: str = ""
    lender_pan: str = ""
    certificate_attached: str = ""
    bill_attached: str = ""
    pan_attached: str = ""


@dataclass(slots=True)
class Form12BBData:
    fiscal_year: str
    employee_name: str
    employee_code: str
    employee_pan: str
    employer_name: str
    employer_tan: str
    employer_address: str
    hra_rows: list[Form12BBSectionRow] = field(default_factory=list)
    lta_rows: list[Form12BBSectionRow] = field(default_factory=list)
    home_loan_rows: list[Form12BBSectionRow] = field(default_factory=list)
    chapter_via_rows: list[Form12BBSectionRow] = field(default_factory=list)

    @property
    def assessment_year(self) -> str:
        fy_start = self.fiscal_year.split("-")[0]
        return f"{int(fy_start) + 1}-{int(fy_start) + 2}"

    @property
    def hra_total(self) -> Decimal:
        return sum(r.amount for r in self.hra_rows)

    @property
    def lta_total(self) -> Decimal:
        return sum(r.amount for r in self.lta_rows)

    @property
    def home_loan_total(self) -> Decimal:
        return sum(r.amount for r in self.home_loan_rows)

    @property
    def chapter_via_total(self) -> Decimal:
        return sum(r.amount for r in self.chapter_via_rows)

    @property
    def grand_total(self) -> Decimal:
        return self.hra_total + self.lta_total + self.home_loan_total + self.chapter_via_total


def _render_form12bb_html(data: Form12BBData) -> str:
    template = Template(FORM_12BB_HTML_TEMPLATE)
    context = Context(
        {
            "fiscal_year": data.fiscal_year,
            "assessment_year": data.assessment_year,
            "employee_name": data.employee_name,
            "employee_code": data.employee_code,
            "employee_pan": data.employee_pan,
            "employer_name": data.employer_name,
            "employer_tan": data.employer_tan or "N/A",
            "employer_address": data.employer_address or "N/A",
            "hra_rows": [
                {
                    "landlord_name": r.landlord_name,
                    "landlord_pan": r.landlord_pan or "—",
                    "landlord_address": r.landlord_address or "—",
                    "amount": decimal_to_string(r.amount),
                    "pan_attached": r.pan_attached or False,
                }
                for r in data.hra_rows
            ],
            "lta_rows": [
                {
                    "reference": r.reference,
                    "description": r.description,
                    "travel_date": r.travel_date,
                    "amount": decimal_to_string(r.amount),
                    "bill_attached": r.bill_attached or False,
                }
                for r in data.lta_rows
            ],
            "home_loan_rows": [
                {
                    "lender_name": r.lender_name,
                    "lender_type": r.lender_type,
                    "lender_pan": r.lender_pan,
                    "amount": decimal_to_string(r.amount),
                    "certificate_attached": r.certificate_attached or False,
                }
                for r in data.home_loan_rows
            ],
            "chapter_via_rows": [
                {
                    "section": r.section,
                    "description": r.description,
                    "amount": decimal_to_string(r.amount),
                    "proof_attached": r.proof_attached or False,
                }
                for r in data.chapter_via_rows
            ],
            "hra_total": decimal_to_string(data.hra_total),
            "lta_total": decimal_to_string(data.lta_total),
            "home_loan_total": decimal_to_string(data.home_loan_total),
            "chapter_via_total": decimal_to_string(data.chapter_via_total),
            "grand_total": decimal_to_string(data.grand_total),
            "generated_date": date.today().strftime("%d/%m/%Y"),
        }
    )
    return template.render(context)


def _collect_declarations(employee, fiscal_year: str) -> dict[str, list[dict[str, Any]]]:
    from apps.payroll.models import InvestmentDeclaration

    declarations = InvestmentDeclaration.objects.filter(
        employee=employee,
        fiscal_year=fiscal_year,
    ).select_related("employee", "employee__user")

    collected: dict[str, list[dict[str, Any]]] = {
        "HRA": [],
        "LTA": [],
        "HOME_LOAN": [],
        "80C": [],
        "80D": [],
        "80G": [],
        "80E": [],
        "80TTA": [],
        "OTHER": [],
    }

    for decl in declarations:
        proof = "Yes" if decl.proof_file_key else "No"
        row = {
            "section": decl.section,
            "description": decl.description,
            "amount": decl.declared_amount,
            "proof_attached": proof,
            "landlord_name": "",
            "landlord_pan": "",
            "landlord_address": "",
            "reference": "",
            "travel_date": "",
            "lender_name": "",
            "lender_type": "",
            "lender_pan": "",
            "certificate_attached": "",
            "bill_attached": "",
        }
        if decl.section == "HRA":
            collected["HRA"].append(row)
        elif decl.section == "LTA":
            collected["LTA"].append(row)
        elif decl.section in ("80C", "80D", "80TTA", "80G", "OTHER"):
            collected[decl.section].append(row)
        else:
            collected["OTHER"].append(row)

    return collected


def _build_form12bb_data(employee, fiscal_year: str) -> Form12BBData:
    from apps.organisations.models import OrganisationAddressType

    organisation = employee.organisation
    pan = get_employee_identifier(employee, id_type="PAN")

    org_address_parts = []
    reg_address = (
        organisation.addresses.filter(
            address_type=OrganisationAddressType.REGISTERED,
            is_active=True,
        )
        .order_by("-is_active")
        .first()
    )
    if reg_address:
        org_address_parts.append(reg_address.line1)
        if reg_address.line2:
            org_address_parts.append(reg_address.line2)
        org_address_parts.append(reg_address.city)
        if reg_address.state:
            org_address_parts.append(reg_address.state)
        if reg_address.pincode:
            org_address_parts.append(reg_address.pincode)
    employer_address = ", ".join(org_address_parts) or "N/A"

    declarations_by_section = _collect_declarations(employee, fiscal_year)

    def _rows(section: str) -> list[Form12BBSectionRow]:
        rows_data = declarations_by_section.get(section, [])
        return [
            Form12BBSectionRow(
                section=r["section"],
                description=r["description"],
                amount=r["amount"],
                proof_attached=r["proof_attached"],
                landlord_name=r.get("landlord_name", ""),
                landlord_pan=r.get("landlord_pan", ""),
                landlord_address=r.get("landlord_address", ""),
                reference=r.get("reference", ""),
                travel_date=r.get("travel_date", ""),
                lender_name=r.get("lender_name", ""),
                lender_type=r.get("lender_type", ""),
                lender_pan=r.get("lender_pan", ""),
                certificate_attached=r.get("certificate_attached", ""),
                bill_attached=r.get("bill_attached", ""),
            )
            for r in rows_data
        ]

    def _chapter_via_rows() -> list[Form12BBSectionRow]:
        all_rows = []
        for section_key in ("80C", "80D", "80TTA", "80G", "OTHER"):
            for r in declarations_by_section.get(section_key, []):
                all_rows.append(
                    Form12BBSectionRow(
                        section=r["section"],
                        description=r["description"],
                        amount=r["amount"],
                        proof_attached=r["proof_attached"],
                    )
                )
        return all_rows

    return Form12BBData(
        fiscal_year=fiscal_year,
        employee_name=employee.user.full_name,
        employee_code=employee.employee_code or "",
        employee_pan=pan or "Not Available",
        employer_name=organisation.name or "",
        employer_tan=organisation.tan_number or "",
        employer_address=employer_address,
        hra_rows=_rows("HRA"),
        lta_rows=_rows("LTA"),
        home_loan_rows=_rows("HOME_LOAN"),
        chapter_via_rows=_chapter_via_rows(),
    )


def generate_form12bb_pdf(*, employee, fiscal_year: str) -> FilingGenerationResult:
    from apps.payroll.models import InvestmentDeclaration

    blockers: list[str] = []
    if not employee.user.full_name:
        blockers.append("Employee name is not available.")

    declarations = InvestmentDeclaration.objects.filter(employee=employee, fiscal_year=fiscal_year)
    if not declarations.exists():
        blockers.append(f"No investment declarations found for FY {fiscal_year}.")

    data = _build_form12bb_data(employee, fiscal_year)
    html_content = _render_form12bb_html(data)
    pdf_bytes = b"" if blockers else weasyprint.HTML(string=html_content).write_pdf()

    return FilingGenerationResult(
        artifact_format="PDF",
        content_type="application/pdf",
        file_name=f"form12bb-{data.employee_code}-{fiscal_year}.pdf",
        structured_payload={
            "filing_type": "FORM12BB",
            "fiscal_year": fiscal_year,
            "employee_code": data.employee_code,
            "employee_name": data.employee_name,
            "employee_pan": data.employee_pan,
            "hra_total": decimal_to_string(data.hra_total),
            "lta_total": decimal_to_string(data.lta_total),
            "home_loan_total": decimal_to_string(data.home_loan_total),
            "chapter_via_total": decimal_to_string(data.chapter_via_total),
            "grand_total": decimal_to_string(data.grand_total),
            "declaration_count": len(data.hra_rows)
            + len(data.lta_rows)
            + len(data.home_loan_rows)
            + len(data.chapter_via_rows),
        },
        metadata={
            "employee_id": str(employee.id),
            "fiscal_year": fiscal_year,
        },
        validation_errors=blockers,
        artifact_binary=pdf_bytes,
    )
