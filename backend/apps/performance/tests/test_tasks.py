from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.performance.models import AppraisalCycle, AppraisalReview, ReviewRelationship, ReviewType
from apps.performance.tasks import auto_schedule_probation_reviews


def _create_organisation(name='Performance Task Org'):
    return Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


def _create_user(email, *, organisation=None, role=UserRole.EMPLOYEE, is_superuser=False, is_staff=False):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.CONTROL_TOWER if is_superuser else AccountType.WORKFORCE,
        role=UserRole.CONTROL_TOWER if is_superuser else role,
        organisation=organisation,
        is_active=True,
        is_superuser=is_superuser,
        is_staff=is_staff,
    )


@pytest.mark.django_db
def test_auto_schedule_probation_reviews_returns_error_without_superuser():
    result = auto_schedule_probation_reviews()

    assert result == {'status': 'ERROR', 'reason': 'No superuser found for system actor'}


@pytest.mark.django_db
def test_auto_schedule_probation_reviews_creates_missing_cycles():
    organisation = _create_organisation()
    system_user = _create_user('system@test.com', is_superuser=True, is_staff=True)
    manager_user = _create_user('manager-task@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
    manager_employee = Employee.objects.create(
        organisation=organisation,
        user=manager_user,
        employee_code='EMP300',
        status=EmployeeStatus.ACTIVE,
    )
    employee_user = _create_user('probation-task@test.com', organisation=organisation)
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP301',
        status=EmployeeStatus.ACTIVE,
        reporting_to=manager_employee,
        probation_end_date=date.today() + timedelta(days=7),
    )

    result = auto_schedule_probation_reviews()

    assert system_user.is_superuser is True
    assert result == {'status': 'OK', 'scheduled': 1}
    cycle = AppraisalCycle.objects.get(organisation=organisation, is_probation_review=True)
    assert cycle.review_type == ReviewType.MANAGER
    review = AppraisalReview.objects.get(cycle=cycle)
    assert review.employee == employee
    assert review.relationship == ReviewRelationship.MANAGER


@pytest.mark.django_db
def test_auto_schedule_probation_reviews_skips_existing_probation_review():
    organisation = _create_organisation()
    system_user = _create_user('system-skip@test.com', is_superuser=True, is_staff=True)
    manager_user = _create_user('manager-skip@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
    manager_employee = Employee.objects.create(
        organisation=organisation,
        user=manager_user,
        employee_code='EMP400',
        status=EmployeeStatus.ACTIVE,
    )
    employee_user = _create_user('probation-skip@test.com', organisation=organisation)
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP401',
        status=EmployeeStatus.ACTIVE,
        reporting_to=manager_employee,
        probation_end_date=date.today() + timedelta(days=7),
    )
    cycle = AppraisalCycle.objects.create(
        organisation=organisation,
        name='Existing probation review',
        review_type=ReviewType.MANAGER,
        start_date=date.today() + timedelta(days=7),
        end_date=date.today() + timedelta(days=7),
        is_probation_review=True,
    )
    AppraisalReview.objects.create(
        cycle=cycle,
        employee=employee,
        reviewer=manager_employee,
        relationship=ReviewRelationship.MANAGER,
    )

    result = auto_schedule_probation_reviews()

    assert system_user.is_superuser is True
    assert result == {'status': 'OK', 'scheduled': 0}
    assert AppraisalCycle.objects.filter(organisation=organisation, is_probation_review=True).count() == 1
