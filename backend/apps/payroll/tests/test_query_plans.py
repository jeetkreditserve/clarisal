from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.payroll.models import (
    CompensationAssignment,
    CompensationAssignmentStatus,
    CompensationTemplate,
    CompensationTemplateStatus,
)


def _create_organisation(*, name: str) -> Organisation:
    return Organisation.objects.create(
        name=name,
        slug=name.lower().replace(" ", "-") + "-" + uuid4().hex[:6],
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


def _bulk_create_users(*, prefix: str, organisation: Organisation, count: int) -> list[User]:
    users = [
        User(
            email=f"{prefix}-{index}-{uuid4().hex[:6]}@test.com",
            password="!",
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=organisation,
            is_active=True,
        )
        for index in range(count)
    ]
    return User.objects.bulk_create(users, batch_size=1000)


def _bulk_create_employees(
    *,
    organisation: Organisation,
    users: list[User],
    status: str,
    code_prefix: str,
) -> None:
    employees = [
        Employee(
            organisation=organisation,
            user=user,
            employee_code=f"{code_prefix}{index:05d}",
            status=status,
            date_of_joining=date(2025, 4, 1),
        )
        for index, user in enumerate(users, start=1)
    ]
    Employee.objects.bulk_create(employees, batch_size=1000)


@pytest.mark.django_db(transaction=True)
def test_payroll_run_employee_query_uses_covering_index():
    target_org = _create_organisation(name="Explain Payroll Org")
    other_org = _create_organisation(name="Explain Payroll Other")

    target_active_users = _bulk_create_users(prefix="target-active", organisation=target_org, count=250)
    target_inactive_users = _bulk_create_users(prefix="target-inactive", organisation=target_org, count=250)
    other_org_users = _bulk_create_users(prefix="other-org", organisation=other_org, count=10000)

    _bulk_create_employees(
        organisation=target_org,
        users=target_active_users,
        status=EmployeeStatus.ACTIVE,
        code_prefix="ACT",
    )
    _bulk_create_employees(
        organisation=target_org,
        users=target_inactive_users,
        status=EmployeeStatus.TERMINATED,
        code_prefix="INA",
    )
    _bulk_create_employees(
        organisation=other_org,
        users=other_org_users,
        status=EmployeeStatus.ACTIVE,
        code_prefix="OTH",
    )

    queryset = Employee.objects.filter(
        organisation=target_org,
        status=EmployeeStatus.ACTIVE,
    ).select_related(
        "user",
        "office_location__organisation_address",
        "profile",
    ).order_by("date_of_joining", "id")

    plan = queryset.explain(analyze=True, verbose=True)

    assert "employee_org_status_doj_idx" in plan


@pytest.mark.django_db(transaction=True)
def test_effective_compensation_assignment_query_uses_covering_index():
    organisation = _create_organisation(name="Explain Compensation Org")
    employee_user = User.objects.create(
        email=f"assignment-{uuid4().hex[:6]}@test.com",
        password="!",
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code="EXPINDEX001",
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 4, 1),
    )
    template = CompensationTemplate.objects.create(
        organisation=organisation,
        name="Explain Template",
        status=CompensationTemplateStatus.APPROVED,
    )
    assignments = [
        CompensationAssignment(
            employee=employee,
            template=template,
            effective_from=date(2024, 4, 1) + timedelta(days=index),
            version=1,
            status=CompensationAssignmentStatus.APPROVED,
        )
        for index in range(2500)
    ]
    CompensationAssignment.objects.bulk_create(assignments, batch_size=500)

    queryset = employee.compensation_assignments.filter(
        effective_from__lte=date(2030, 3, 31),
        status=CompensationAssignmentStatus.APPROVED,
    ).order_by("-effective_from", "-version", "-created_at")[:1]

    plan = queryset.explain(analyze=True, verbose=True)

    assert "comp_assign_emp_status_eff_idx" in plan
