from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.performance.models import (
    AppraisalCycle,
    AppraisalReview,
    CycleStatus,
    FeedbackRequest,
    Goal,
    GoalCycle,
    GoalStatus,
    ReviewRelationship,
    ReviewStatus,
    ReviewType,
)


@pytest.fixture
def performance_setup(db):
    organisation = Organisation.objects.create(
        name='Acme Performance',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    org_admin_user = User.objects.create_user(
        email='performance-admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=org_admin_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    organisation.primary_admin_user = org_admin_user
    organisation.save(update_fields=['primary_admin_user', 'modified_at'])
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        created_by=org_admin_user,
    )
    mark_licence_batch_paid(batch, paid_by=org_admin_user, paid_at=date(2026, 4, 1))

    manager_user = User.objects.create_user(
        email='manager-review@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    manager_employee = Employee.objects.create(
        organisation=organisation,
        user=manager_user,
        employee_code='EMP200',
        designation='Manager',
        status=EmployeeStatus.ACTIVE,
    )

    employee_user = User.objects.create_user(
        email='performance-employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP100',
        designation='Engineer',
        status=EmployeeStatus.ACTIVE,
        reporting_to=manager_employee,
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=org_admin_user)
    admin_session = admin_client.session
    admin_session['active_workspace_kind'] = 'ADMIN'
    admin_session['active_admin_org_id'] = str(organisation.id)
    admin_session.save()

    employee_client = APIClient()
    employee_client.force_authenticate(user=employee_user)
    employee_session = employee_client.session
    employee_session['active_workspace_kind'] = 'EMPLOYEE'
    employee_session['active_employee_org_id'] = str(organisation.id)
    employee_session.save()

    return {
        'organisation': organisation,
        'org_admin_user': org_admin_user,
        'manager_user': manager_user,
        'manager_employee': manager_employee,
        'employee_user': employee_user,
        'employee': employee,
        'admin_client': admin_client,
        'employee_client': employee_client,
    }


@pytest.mark.django_db
def test_org_admin_can_create_and_list_goal_cycles(performance_setup):
    client = performance_setup['admin_client']

    create_response = client.post(
        '/api/v1/org/performance/goal-cycles/',
        {
            'name': 'Q2 2026',
            'start_date': '2026-04-01',
            'end_date': '2026-06-30',
        },
        format='json',
    )
    list_response = client.get('/api/v1/org/performance/goal-cycles/')

    assert create_response.status_code == 201
    assert create_response.data['status'] == CycleStatus.DRAFT
    assert list_response.status_code == 200
    assert len(list_response.data) == 1


@pytest.mark.django_db
def test_org_admin_can_create_and_list_appraisal_cycles(performance_setup):
    client = performance_setup['admin_client']

    create_response = client.post(
        '/api/v1/org/performance/appraisal-cycles/',
        {
            'name': 'FY 2026 Appraisal',
            'review_type': ReviewType.SELF,
            'start_date': '2026-10-01',
            'end_date': '2026-12-31',
        },
        format='json',
    )
    list_response = client.get('/api/v1/org/performance/appraisal-cycles/')

    assert create_response.status_code == 201
    assert create_response.data['review_type'] == ReviewType.SELF
    assert list_response.status_code == 200
    assert len(list_response.data) == 1


@pytest.mark.django_db
def test_employee_can_list_goals_and_update_progress(performance_setup):
    employee = performance_setup['employee']
    client = performance_setup['employee_client']
    cycle = GoalCycle.objects.create(
        organisation=performance_setup['organisation'],
        name='Q2 Goals',
        start_date=date(2026, 4, 1),
        end_date=date(2026, 6, 30),
        status=CycleStatus.ACTIVE,
    )
    goal = Goal.objects.create(
        cycle=cycle,
        employee=employee,
        title='Ship payroll dashboard',
        status=GoalStatus.NOT_STARTED,
        progress_percent=0,
    )

    list_response = client.get('/api/v1/me/performance/goals/')
    update_response = client.patch(
        f'/api/v1/me/performance/goals/{goal.id}/progress/',
        {'progress_percent': 60},
        format='json',
    )

    assert list_response.status_code == 200
    assert len(list_response.data) == 1
    assert update_response.status_code == 200
    assert update_response.data['progress_percent'] == 60
    assert update_response.data['status'] == GoalStatus.IN_PROGRESS


@pytest.mark.django_db
def test_employee_can_list_reviews_and_submit_owned_review(performance_setup):
    employee = performance_setup['employee']
    client = performance_setup['employee_client']
    cycle = AppraisalCycle.objects.create(
        organisation=performance_setup['organisation'],
        name='Mid Year Review',
        review_type=ReviewType.SELF,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        status=CycleStatus.ACTIVE,
    )
    review = AppraisalReview.objects.create(
        cycle=cycle,
        employee=employee,
        reviewer=employee,
        relationship=ReviewRelationship.SELF,
        status=ReviewStatus.PENDING,
    )

    list_response = client.get('/api/v1/me/performance/reviews/')
    submit_response = client.post(
        f'/api/v1/me/performance/reviews/{review.id}/submit/',
        {
            'ratings': {'ownership': 4},
            'comments': 'Delivered the planned work.',
        },
        format='json',
    )

    assert list_response.status_code == 200
    assert len(list_response.data) == 1
    assert submit_response.status_code == 200
    assert submit_response.data['status'] == ReviewStatus.SUBMITTED
    assert submit_response.data['comments'] == 'Delivered the planned work.'


@pytest.mark.django_db
def test_employee_self_assessment_submit_locks_editing(performance_setup):
    employee = performance_setup['employee']
    client = performance_setup['employee_client']
    cycle = AppraisalCycle.objects.create(
        organisation=performance_setup['organisation'],
        name='Self Review Cycle',
        review_type=ReviewType.SELF,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        status=CycleStatus.SELF_ASSESSMENT,
    )
    AppraisalReview.objects.create(
        cycle=cycle,
        employee=employee,
        reviewer=employee,
        relationship=ReviewRelationship.SELF,
        status=ReviewStatus.PENDING,
    )

    save_response = client.put(
        f'/api/v1/me/performance/review-cycles/{cycle.id}/self-assessment/',
        {
            'ratings': {'ownership': 4},
            'comments': 'Delivered planned work.',
        },
        format='json',
    )
    submit_response = client.post(
        f'/api/v1/me/performance/review-cycles/{cycle.id}/self-assessment/submit/',
        format='json',
    )
    locked_response = client.put(
        f'/api/v1/me/performance/review-cycles/{cycle.id}/self-assessment/',
        {
            'ratings': {'ownership': 5},
            'comments': 'Trying to edit after submit.',
        },
        format='json',
    )

    assert save_response.status_code == 200
    assert save_response.data['status'] == ReviewStatus.IN_PROGRESS
    assert submit_response.status_code == 200
    assert submit_response.data['status'] == ReviewStatus.SUBMITTED
    assert locked_response.status_code == 400
    assert locked_response.data['error'] == 'Submitted self-assessments cannot be edited.'


@pytest.mark.django_db
def test_feedback_summary_only_visible_after_manager_review_phase(performance_setup):
    from apps.performance.models import FeedbackResponse

    organisation = performance_setup['organisation']
    employee = performance_setup['employee']
    manager_employee = performance_setup['manager_employee']
    admin_client = performance_setup['admin_client']
    cycle = AppraisalCycle.objects.create(
        organisation=organisation,
        name='360 Summary Cycle',
        review_type=ReviewType.REVIEW_360,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        status=CycleStatus.PEER_REVIEW,
    )
    request_record = FeedbackRequest.objects.create(
        cycle=cycle,
        employee=employee,
        requested_from=manager_employee,
    )
    FeedbackResponse.objects.create(
        request=request_record,
        ratings={'ownership': 4},
        comments='Strong cross-team partner.',
    )

    early_response = admin_client.get(
        f'/api/v1/org/performance/appraisal-cycles/{cycle.id}/employees/{employee.id}/feedback-summary/'
    )

    cycle.status = CycleStatus.MANAGER_REVIEW
    cycle.save(update_fields=['status', 'modified_at'])

    ready_response = admin_client.get(
        f'/api/v1/org/performance/appraisal-cycles/{cycle.id}/employees/{employee.id}/feedback-summary/'
    )

    assert early_response.status_code == 400
    assert early_response.data['error'] == 'Feedback summaries are available after manager review starts.'
    assert ready_response.status_code == 200
    assert ready_response.data['response_count'] == 1
    assert ready_response.data['comments'] == ['Strong cross-team partner.']


@pytest.mark.django_db
def test_calibration_adjustments_require_org_admin(performance_setup):
    from apps.performance.services import create_calibration_session

    organisation = performance_setup['organisation']
    employee = performance_setup['employee']
    manager_employee = performance_setup['manager_employee']
    admin_client = performance_setup['admin_client']
    employee_client = performance_setup['employee_client']
    cycle = AppraisalCycle.objects.create(
        organisation=organisation,
        name='Calibration Access Cycle',
        review_type=ReviewType.MANAGER,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        status=CycleStatus.CALIBRATION,
    )
    cycle.reviews.create(
        employee=employee,
        reviewer=manager_employee,
        relationship=ReviewRelationship.MANAGER,
        ratings={'delivery': 3, 'collaboration': 3},
        status=ReviewStatus.SUBMITTED,
    )
    session = create_calibration_session(cycle, actor=performance_setup['org_admin_user'])

    employee_response = employee_client.patch(
        f'/api/v1/org/performance/calibration-sessions/{session.id}/employees/{employee.id}/rating/',
        {
            'rating': 4.0,
            'reason': 'Not allowed',
        },
        format='json',
    )
    admin_response = admin_client.patch(
        f'/api/v1/org/performance/calibration-sessions/{session.id}/employees/{employee.id}/rating/',
        {
            'rating': 4.0,
            'reason': 'Adjusted after moderation',
        },
        format='json',
    )

    assert employee_response.status_code == 403
    assert admin_response.status_code == 200
    assert admin_response.data['current_rating'] == 4.0
    assert admin_response.data['reason'] == 'Adjusted after moderation'
