from datetime import date
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeProfile, EmployeeStatus, GenderChoice, GovernmentIdType
from apps.employees.services import upsert_government_id
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.payroll.models import PayrollTDSChallan, StatutoryFilingStatus
from apps.payroll.services import (
    assign_employee_compensation,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    finalize_pay_run,
    generate_statutory_filing_batch,
)

from .test_service_setup import _attach_registered_and_billing_addresses

FIXTURES_DIR = Path(__file__).with_name("fixtures")
TEST_USER_PASSWORD = "pass123!"  # pragma: allowlist secret
TEST_EMPLOYEE_PAN = "ABCDE1234F"  # pragma: allowlist secret
TEST_STATEMENT_RECEIPT_NUMBER = "123456789012345"  # pragma: allowlist secret


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def _create_org_with_admin():
    organisation = Organisation.objects.create(
        name="Northstar Labs",
        pan_number="AACCN1234F",
        tan_number="BLRN12345A",
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    _attach_registered_and_billing_addresses(organisation)
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month="99.00",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
    admin = User.objects.create_user(
        email="payroll-admin@test.com",
        password=TEST_USER_PASSWORD,
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        first_name="Nina",
        last_name="Admin",
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=admin,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    return organisation, admin


def _create_employee(organisation):
    employee_user = User.objects.create_user(
        email="priya.sharma@test.com",
        password=TEST_USER_PASSWORD,
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        first_name="Priya",
        last_name="Sharma",
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code="EMP001",
        designation="Analyst",
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 4, 1),
    )
    EmployeeProfile.objects.create(
        employee=employee,
        gender=GenderChoice.MALE,
        uan_number="100200300400",
        esic_ip_number="1234567890",
    )
    upsert_government_id(
        employee,
        GovernmentIdType.PAN,
        TEST_EMPLOYEE_PAN,
        actor=employee_user,
        name_on_id="Priya Sharma",
    )
    return employee


def _finalize_run(*, organisation, admin, employee, period_year, period_month, monthly_amount):
    template = create_compensation_template(
        organisation,
        name=f"Template {period_year}-{period_month:02d}",
        description="Filing fixture",
        lines=[
            {
                "component_code": "BASIC",
                "name": "Basic Pay",
                "component_type": "EARNING",
                "monthly_amount": str(monthly_amount),
                "is_taxable": True,
            }
        ],
        actor=admin,
    )
    assign_employee_compensation(
        employee,
        template,
        effective_from=date(period_year, period_month, 1),
        actor=admin,
        auto_approve=True,
    )
    pay_run = create_payroll_run(
        organisation,
        period_year=period_year,
        period_month=period_month,
        actor=admin,
        requester_user=admin,
    )
    from apps.payroll.services import calculate_pay_run

    calculate_pay_run(pay_run, actor=admin)
    finalize_pay_run(pay_run, actor=admin, skip_approval=True)
    return pay_run


def _create_tds_challan(
    *,
    organisation,
    fiscal_year,
    period_year,
    period_month,
    tax_deposited,
    statement_receipt_number=TEST_STATEMENT_RECEIPT_NUMBER,
):
    return PayrollTDSChallan.objects.create(
        organisation=organisation,
        fiscal_year=fiscal_year,
        bsr_code="0510032",
        challan_serial_number=f"{period_month:05d}",
        deposit_date=date(period_year, period_month, 7),
        period_year=period_year,
        period_month=period_month,
        tax_deposited=tax_deposited,
        interest_amount="0.00",
        fee_amount="0.00",
        statement_receipt_number=statement_receipt_number,
    )


@pytest.fixture
def filing_fixture(db):
    call_command("seed_statutory_masters")
    organisation, admin = _create_org_with_admin()
    create_tax_slab_set(
        fiscal_year="2026-2027",
        name="FY 2026 Master",
        country_code="IN",
        slabs=[
            {"min_income": "0", "max_income": "300000", "rate_percent": "0"},
            {"min_income": "300000", "max_income": "700000", "rate_percent": "5"},
            {"min_income": "700000", "max_income": None, "rate_percent": "10"},
        ],
        actor=admin,
    )
    ensure_org_payroll_setup(organisation, actor=admin)
    employee = _create_employee(organisation)
    april_run = _finalize_run(
        organisation=organisation,
        admin=admin,
        employee=employee,
        period_year=2026,
        period_month=4,
        monthly_amount="20000",
    )
    may_run = _finalize_run(
        organisation=organisation,
        admin=admin,
        employee=employee,
        period_year=2026,
        period_month=5,
        monthly_amount="25000",
    )
    return {
        "organisation": organisation,
        "admin": admin,
        "employee": employee,
        "april_run": april_run,
        "may_run": may_run,
    }


@pytest.mark.django_db
class TestStatutoryFilings:
    def test_pf_ecr_matches_fixture(self, filing_fixture):
        batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="PF_ECR",
            actor=filing_fixture["admin"],
            period_year=2026,
            period_month=4,
        )

        assert batch.status == StatutoryFilingStatus.GENERATED
        assert batch.artifact_text == _read_fixture("pf_ecr_2026_04.csv")

    def test_esi_export_matches_fixture_and_preserves_continued_eligibility(self, filing_fixture):
        batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="ESI_MONTHLY",
            actor=filing_fixture["admin"],
            period_year=2026,
            period_month=5,
        )

        assert batch.status == StatutoryFilingStatus.GENERATED
        assert batch.artifact_text == _read_fixture("esi_2026_05.csv")
        assert batch.structured_payload["rows"][0]["eligibility_mode"] == "CONTINUED"

    def test_esi_export_surfaces_branch_code_warnings_and_includes_configured_value(self, filing_fixture):
        blank_branch_batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="ESI_MONTHLY",
            actor=filing_fixture["admin"],
            period_year=2026,
            period_month=5,
        )

        assert blank_branch_batch.status == StatutoryFilingStatus.GENERATED
        assert blank_branch_batch.metadata["warnings"] == ["Organisation ESI branch code is blank for this filing."]
        assert blank_branch_batch.structured_payload["rows"][0]["esi_branch_code"] == ""

        filing_fixture["organisation"].esi_branch_code = "ESI-BLR-001"
        filing_fixture["organisation"].save(update_fields=["esi_branch_code", "modified_at"])

        configured_branch_batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="ESI_MONTHLY",
            actor=filing_fixture["admin"],
            period_year=2026,
            period_month=5,
        )

        assert configured_branch_batch.status == StatutoryFilingStatus.GENERATED
        assert configured_branch_batch.metadata.get("warnings", []) == []
        assert configured_branch_batch.structured_payload["rows"][0]["esi_branch_code"] == "ESI-BLR-001"
        assert "ESI-BLR-001" in configured_branch_batch.artifact_text

    def test_professional_tax_export_matches_fixture(self, filing_fixture):
        batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="PROFESSIONAL_TAX",
            actor=filing_fixture["admin"],
            period_year=2026,
            period_month=4,
        )

        assert batch.status == StatutoryFilingStatus.GENERATED
        assert batch.artifact_text == _read_fixture("professional_tax_2026_04.csv")

    def test_form24q_json_matches_fixture(self, filing_fixture):
        batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="FORM24Q",
            actor=filing_fixture["admin"],
            fiscal_year="2026-2027",
            quarter="Q1",
        )

        assert batch.status == StatutoryFilingStatus.GENERATED
        expected = _read_fixture("form24q_2026_2027_q1.json").replace("__DYNAMIC__", str(filing_fixture["employee"].id))
        assert batch.artifact_text.strip() == expected.strip()

    def test_form16_xml_and_pdf_outputs_generate(self, filing_fixture):
        xml_batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="FORM16",
            actor=filing_fixture["admin"],
            fiscal_year="2026-2027",
            artifact_format="XML",
        )
        pdf_batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="FORM16",
            actor=filing_fixture["admin"],
            fiscal_year="2026-2027",
            artifact_format="PDF",
        )

        assert xml_batch.status == StatutoryFilingStatus.GENERATED
        assert xml_batch.artifact_text == _read_fixture("form16_2026_2027.xml")
        assert pdf_batch.status == StatutoryFilingStatus.GENERATED
        assert bytes(pdf_batch.artifact_binary).startswith(b"%PDF-1.4")

    def test_form24q_uses_decrypted_pan_and_real_challan_details(self, filing_fixture):
        april_payslip = filing_fixture["april_run"].payslips.get(employee=filing_fixture["employee"])
        april_item = april_payslip.pay_run_item
        april_item.income_tax = "3500.00"
        april_item.snapshot = {**april_item.snapshot, "income_tax": "3500.00"}
        april_item.save(update_fields=["income_tax", "snapshot", "modified_at"])
        april_payslip.snapshot = {**april_payslip.snapshot, "income_tax": "3500.00"}
        april_payslip.save(update_fields=["snapshot", "modified_at"])

        may_payslip = filing_fixture["may_run"].payslips.get(employee=filing_fixture["employee"])
        may_item = may_payslip.pay_run_item
        may_item.income_tax = "4200.00"
        may_item.snapshot = {**may_item.snapshot, "income_tax": "4200.00"}
        may_item.save(update_fields=["income_tax", "snapshot", "modified_at"])
        may_payslip.snapshot = {**may_payslip.snapshot, "income_tax": "4200.00"}
        may_payslip.save(update_fields=["snapshot", "modified_at"])

        _create_tds_challan(
            organisation=filing_fixture["organisation"],
            fiscal_year="2026-2027",
            period_year=2026,
            period_month=4,
            tax_deposited="3500.00",
        )
        _create_tds_challan(
            organisation=filing_fixture["organisation"],
            fiscal_year="2026-2027",
            period_year=2026,
            period_month=5,
            tax_deposited="4200.00",
        )

        batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="FORM24Q",
            actor=filing_fixture["admin"],
            fiscal_year="2026-2027",
            quarter="Q1",
        )

        assert batch.status == StatutoryFilingStatus.GENERATED
        assert batch.structured_payload["employees"][0]["employee_pan"] == TEST_EMPLOYEE_PAN
        assert batch.structured_payload["challans"] == [
            {
                "period": "2026-04",
                "bsr_code": "0510032",
                "challan_serial_number": "00004",
                "deposit_date": "2026-04-07",
                "tax_deposited": "3500.00",
                "interest_amount": "0.00",
                "fee_amount": "0.00",
                "statement_receipt_number": TEST_STATEMENT_RECEIPT_NUMBER,
            },
            {
                "period": "2026-05",
                "bsr_code": "0510032",
                "challan_serial_number": "00005",
                "deposit_date": "2026-05-07",
                "tax_deposited": "4200.00",
                "interest_amount": "0.00",
                "fee_amount": "0.00",
                "statement_receipt_number": TEST_STATEMENT_RECEIPT_NUMBER,
            },
        ]

    def test_form24q_blocks_when_tds_exists_without_matching_challans(self, filing_fixture):
        april_payslip = filing_fixture["april_run"].payslips.get(employee=filing_fixture["employee"])
        april_item = april_payslip.pay_run_item
        april_item.income_tax = "3500.00"
        april_item.snapshot = {**april_item.snapshot, "income_tax": "3500.00"}
        april_item.save(update_fields=["income_tax", "snapshot", "modified_at"])
        april_payslip.snapshot = {**april_payslip.snapshot, "income_tax": "3500.00"}
        april_payslip.save(update_fields=["snapshot", "modified_at"])

        batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="FORM24Q",
            actor=filing_fixture["admin"],
            fiscal_year="2026-2027",
            quarter="Q1",
        )

        assert batch.status == StatutoryFilingStatus.BLOCKED
        assert "missing TDS challan" in batch.validation_errors[0]

    def test_form16_outputs_include_decrypted_pan_and_challan_summary(self, filing_fixture):
        april_payslip = filing_fixture["april_run"].payslips.get(employee=filing_fixture["employee"])
        april_item = april_payslip.pay_run_item
        april_item.income_tax = "3500.00"
        april_item.snapshot = {**april_item.snapshot, "income_tax": "3500.00"}
        april_item.save(update_fields=["income_tax", "snapshot", "modified_at"])
        april_payslip.snapshot = {**april_payslip.snapshot, "income_tax": "3500.00"}
        april_payslip.save(update_fields=["snapshot", "modified_at"])

        _create_tds_challan(
            organisation=filing_fixture["organisation"],
            fiscal_year="2026-2027",
            period_year=2026,
            period_month=4,
            tax_deposited="3500.00",
        )

        batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="FORM16",
            actor=filing_fixture["admin"],
            fiscal_year="2026-2027",
            artifact_format="XML",
        )

        assert batch.status == StatutoryFilingStatus.GENERATED
        assert batch.structured_payload["employees"][0]["employee_pan"] == TEST_EMPLOYEE_PAN
        assert batch.structured_payload["employees"][0]["quarter_summaries"] == [
            {
                "quarter": "Q1",
                "statement_receipt_number": TEST_STATEMENT_RECEIPT_NUMBER,
                "amount_paid": "45000.00",
                "tax_deducted": "3500.00",
                "tax_deposited": "3500.00",
            }
        ]
        assert batch.structured_payload["employees"][0]["challan_details"] == [
            {
                "period": "2026-04",
                "tax_deposited_for_employee": "3500.00",
                "bsr_code": "0510032",
                "challan_serial_number": "00004",
                "deposit_date": "2026-04-07",
            }
        ]

    def test_missing_identifiers_block_exports(self, filing_fixture):
        employee_profile = filing_fixture["employee"].profile
        employee_profile.uan_number = ""
        employee_profile.esic_ip_number = ""
        employee_profile.save(update_fields=["uan_number", "esic_ip_number", "modified_at"])
        filing_fixture["organisation"].tan_number = ""
        filing_fixture["organisation"].save(update_fields=["tan_number"])

        pf_batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="PF_ECR",
            actor=filing_fixture["admin"],
            period_year=2026,
            period_month=4,
        )
        esi_batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="ESI_MONTHLY",
            actor=filing_fixture["admin"],
            period_year=2026,
            period_month=5,
        )
        form24q_batch = generate_statutory_filing_batch(
            filing_fixture["organisation"],
            filing_type="FORM24Q",
            actor=filing_fixture["admin"],
            fiscal_year="2026-2027",
            quarter="Q1",
        )

        assert pf_batch.status == StatutoryFilingStatus.BLOCKED
        assert "missing UAN number" in pf_batch.validation_errors[0]
        assert esi_batch.status == StatutoryFilingStatus.BLOCKED
        assert "missing ESIC IP number" in esi_batch.validation_errors[0]
        assert form24q_batch.status == StatutoryFilingStatus.BLOCKED
        assert "Organisation TAN is required" in form24q_batch.validation_errors[0]


@pytest.mark.django_db
def test_generate_payslip_pdf_returns_valid_pdf_bytes(filing_fixture):
    """generate_payslip_pdf_bytes returns valid PDF bytes starting with %PDF."""
    from apps.payroll.filings.payslip_pdf import generate_payslip_pdf_bytes
    from apps.payroll.models import Payslip

    payslip = Payslip.objects.filter(
        employee=filing_fixture["employee"],
        pay_run=filing_fixture["april_run"],
    ).first()

    pdf_bytes = generate_payslip_pdf_bytes(payslip)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 1000


@pytest.mark.django_db
def test_generate_payslip_pdf_has_minimum_size(filing_fixture):
    """PDF bytes are a non-trivial size, indicating meaningful content."""
    from apps.payroll.filings.payslip_pdf import generate_payslip_pdf_bytes
    from apps.payroll.models import Payslip

    payslip = Payslip.objects.filter(
        employee=filing_fixture["employee"],
        pay_run=filing_fixture["april_run"],
    ).first()

    pdf_bytes = generate_payslip_pdf_bytes(payslip)

    assert len(pdf_bytes) > 5000


@pytest.mark.django_db
def test_download_payslip_pdf_response_returns_correct_content_type(filing_fixture):
    """download_payslip_pdf_response returns application/pdf with correct filename."""
    from apps.payroll.filings.payslip_pdf import download_payslip_pdf_response
    from apps.payroll.models import Payslip

    payslip = Payslip.objects.filter(
        employee=filing_fixture["employee"],
        pay_run=filing_fixture["april_run"],
    ).first()

    response = download_payslip_pdf_response(payslip)

    assert response["Content-Type"] == "application/pdf"
    assert payslip.slip_number.replace("/", "-") + ".pdf" in response["Content-Disposition"]


@pytest.mark.django_db
def test_generate_form12bb_pdf_returns_valid_pdf_bytes(filing_fixture):
    """generate_form12bb_pdf returns valid PDF bytes."""
    from apps.payroll.filings.form12bb import generate_form12bb_pdf
    from apps.payroll.models import InvestmentDeclaration, InvestmentSection

    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.SECTION_80C,
        description="Public Provident Fund",
        declared_amount="50000.00",
    )

    result = generate_form12bb_pdf(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
    )

    assert result.artifact_format == "PDF"
    assert result.content_type == "application/pdf"
    assert result.artifact_binary.startswith(b"%PDF")
    assert len(result.artifact_binary) > 1000
    assert result.file_name == f"form12bb-{filing_fixture['employee'].employee_code}-2026-2027.pdf"
    assert result.validation_errors == []


@pytest.mark.django_db
def test_generate_form12bb_pdf_blocks_when_no_declarations(filing_fixture):
    """generate_form12bb_pdf returns blocked result when no declarations exist."""
    from apps.payroll.filings.form12bb import generate_form12bb_pdf

    result = generate_form12bb_pdf(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
    )

    assert result.validation_errors == ["No investment declarations found for FY 2026-2027."]
    assert len(result.artifact_binary) == 0


@pytest.mark.django_db
def test_generate_form12bb_pdf_populates_all_section_types(filing_fixture):
    """Form 12BB aggregates declarations from all section types."""
    from apps.payroll.filings.form12bb import generate_form12bb_pdf
    from apps.payroll.models import InvestmentDeclaration, InvestmentSection

    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.HRA,
        description="Rent paid to landlord",
        declared_amount="120000.00",
    )
    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.SECTION_80C,
        description="Life Insurance Premium",
        declared_amount="25000.00",
    )
    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.SECTION_80D,
        description="Health Insurance - Self",
        declared_amount="15000.00",
    )
    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.LTA,
        description="Domestic travel",
        declared_amount="10000.00",
    )

    result = generate_form12bb_pdf(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
    )

    assert result.validation_errors == []
    assert result.structured_payload["hra_total"] == "120000.00"
    assert result.structured_payload["lta_total"] == "10000.00"
    assert result.structured_payload["chapter_via_total"] == "40000.00"
    assert result.structured_payload["grand_total"] == "170000.00"
    assert result.structured_payload["declaration_count"] == 4
    assert result.structured_payload["employee_name"] == "Priya Sharma"


@pytest.mark.django_db
def test_generate_form12bb_pdf_empty_declaration_edge_case(filing_fixture):
    """Form 12BB handles employee with zero declarations gracefully."""
    from apps.payroll.filings.form12bb import generate_form12bb_pdf

    result = generate_form12bb_pdf(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
    )

    assert result.validation_errors == ["No investment declarations found for FY 2026-2027."]
    assert result.artifact_binary == b""
import io
import zipfile
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.payroll.models import InvestmentDeclaration, InvestmentSection
from apps.payroll.services import generate_form12bb_zip_for_organisation


@pytest.mark.django_db
def test_generate_form12bb_zip_returns_valid_zip(filing_fixture):
    """generate_form12bb_zip_for_organisation returns a valid ZIP containing PDFs."""
    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.SECTION_80C,
        description="PPF",
        declared_amount="50000.00",
    )

    zip_bytes, structured_payloads = generate_form12bb_zip_for_organisation(
        filing_fixture["organisation"],
        fiscal_year="2026-2027",
        actor=filing_fixture["admin"],
    )

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    zip_buffer = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        assert zf.testzip() is None
        file_names = zf.namelist()
        assert len(file_names) >= 1
        pdf_files = [f for f in file_names if f.endswith(".pdf")]
        assert len(pdf_files) == 1
        pdf_content = zf.read(pdf_files[0])
        assert pdf_content.startswith(b"%PDF")

    assert len(structured_payloads) == 1
    assert structured_payloads[0]["filing_type"] == "FORM12BB"


@pytest.mark.django_db
def test_generate_form12bb_zip_empty_when_no_declarations(filing_fixture):
    """ZIP is empty when no employee has declarations for the fiscal year."""
    zip_bytes, structured_payloads = generate_form12bb_zip_for_organisation(
        filing_fixture["organisation"],
        fiscal_year="2026-2027",
        actor=filing_fixture["admin"],
    )

    zip_buffer = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        file_names = zf.namelist()
        assert len(file_names) == 0

    assert len(structured_payloads) == 1
    assert structured_payloads[0]["filing_type"] == "FORM12BB"
    assert structured_payloads[0]["employee_code"] == "EMP001"


@pytest.mark.django_db
def test_my_form12bb_download_returns_pdf(filing_fixture):
    """MyForm12BBDownloadView returns a PDF for a valid fiscal year with declarations."""
    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.HRA,
        description="Rent",
        declared_amount="120000.00",
    )

    client = APIClient()
    client.force_authenticate(user=filing_fixture["employee"].user)

    response = client.get("/api/me/payroll/form12bb/2026-2027/download/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"%PDF" in response.content
    assert "form12bb-EMP001-2026-2027.pdf" in response["Content-Disposition"]


@pytest.mark.django_db
def test_my_form12bb_download_returns_400_when_blocked(filing_fixture):
    """MyForm12BBDownloadView returns 400 when org operations are blocked."""
    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.HRA,
        description="Rent",
        declared_amount="120000.00",
    )

    client = APIClient()
    client.force_authenticate(user=filing_fixture["employee"].user)

    with patch(
        "apps.approvals.services.get_org_operations_guard",
        return_value={"approval_actions_blocked": True, "reason": "Licence expired."},
    ):
        response = client.get("/api/me/payroll/form12bb/2026-2027/download/")

    assert response.status_code == 400
    assert "Licence expired" in response.json()["error"]


@pytest.mark.django_db
def test_my_form12bb_download_returns_400_when_no_declarations(filing_fixture):
    """MyForm12BBDownloadView returns 400 when no declarations exist for the fiscal year."""
    client = APIClient()
    client.force_authenticate(user=filing_fixture["employee"].user)

    response = client.get("/api/me/payroll/form12bb/2026-2027/download/")

    assert response.status_code == 400
    assert "No investment declarations found" in response.json()["error"]


@pytest.mark.django_db
def test_org_form12bb_bulk_download_returns_zip(filing_fixture):
    """OrgForm12BBBulkDownloadView returns a ZIP file for the org."""
    InvestmentDeclaration.objects.create(
        employee=filing_fixture["employee"],
        fiscal_year="2026-2027",
        section=InvestmentSection.SECTION_80C,
        description="PPF",
        declared_amount="50000.00",
    )

    client = APIClient()
    client.force_authenticate(user=filing_fixture["admin"])
    client.session["active_admin_org_id"] = str(filing_fixture["organisation"].id)

    response = client.get("/api/org/payroll/form12bb/2026-2027/download/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert "form12bb-bulk-2026-2027.zip" in response["Content-Disposition"]

    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        pdf_files = [f for f in zf.namelist() if f.endswith(".pdf")]
        assert len(pdf_files) == 1


@pytest.mark.django_db
def test_org_form12bb_bulk_download_returns_400_when_blocked(filing_fixture):
    """OrgForm12BBBulkDownloadView returns 400 when org operations are blocked."""
    client = APIClient()
    client.force_authenticate(user=filing_fixture["admin"])

    client.session["active_admin_org_id"] = str(filing_fixture["organisation"].id)
    with patch(
        "apps.approvals.services.get_org_operations_guard",
        return_value={"approval_actions_blocked": True, "reason": "Licence expired."},
    ):
        response = client.get("/api/org/payroll/form12bb/2026-2027/download/")

    assert response.status_code == 400
    assert "Licence expired" in response.json()["error"]
