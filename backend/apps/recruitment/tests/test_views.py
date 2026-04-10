from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import ApprovalRequestKind, ApprovalWorkflow
from apps.employees.models import Employee, EmployeeStatus
from apps.invitations.models import Invitation
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.recruitment.models import (
    Application,
    ApplicationStage,
    Candidate,
    Interview,
    JobPosting,
    JobPostingStatus,
    OfferLetter,
)


def _seed_default_workflows(organisation, actor):
    for request_kind, label in (
        (ApprovalRequestKind.LEAVE, 'Leave'),
        (ApprovalRequestKind.ON_DUTY, 'On Duty'),
        (ApprovalRequestKind.ATTENDANCE_REGULARIZATION, 'Attendance Regularization'),
    ):
        ApprovalWorkflow.objects.create(
            organisation=organisation,
            name=f'Default {label} Workflow',
            is_default=True,
            default_request_kind=request_kind,
            is_active=True,
            created_by=actor,
        )


@pytest.fixture
def recruitment_api_setup(db):
    organisation = Organisation.objects.create(
        name='Recruitment API Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    org_admin_user = User.objects.create_user(
        email='recruitment-admin@test.com',
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

    _seed_default_workflows(organisation, org_admin_user)
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        created_by=org_admin_user,
    )
    mark_licence_batch_paid(batch, paid_by=org_admin_user, paid_at=date(2026, 4, 1))

    client = APIClient()
    client.force_authenticate(user=org_admin_user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()

    interviewer_user = User.objects.create_user(
        email='interviewer@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    interviewer = Employee.objects.create(
        organisation=organisation,
        user=interviewer_user,
        employee_code='EMP-INT-001',
        designation='Engineering Manager',
        status=EmployeeStatus.ACTIVE,
    )

    posting = JobPosting.objects.create(
        organisation=organisation,
        title='Backend Engineer',
        description='Build ATS flows',
        status=JobPostingStatus.OPEN,
    )
    candidate = Candidate.objects.create(
        organisation=organisation,
        first_name='Priya',
        last_name='Nair',
        email='priya@example.com',
    )
    application = Application.objects.create(
        candidate=candidate,
        job_posting=posting,
        stage=ApplicationStage.APPLIED,
    )

    return {
        'organisation': organisation,
        'org_admin_user': org_admin_user,
        'client': client,
        'interviewer': interviewer,
        'posting': posting,
        'candidate': candidate,
        'application': application,
    }


@pytest.mark.django_db
def test_org_admin_can_create_and_list_job_postings(recruitment_api_setup):
    client = recruitment_api_setup['client']

    create_response = client.post(
        '/api/v1/org/recruitment/jobs/',
        {
            'title': 'Product Designer',
            'description': 'Design internal workflows',
            'requirements': 'Figma, systems thinking',
        },
        format='json',
    )
    list_response = client.get('/api/v1/org/recruitment/jobs/')

    assert create_response.status_code == 201
    assert create_response.data['status'] == JobPostingStatus.DRAFT
    assert list_response.status_code == 200
    assert len(list_response.data) == 2


@pytest.mark.django_db
def test_org_admin_can_filter_applications_by_stage(recruitment_api_setup):
    client = recruitment_api_setup['client']
    application = recruitment_api_setup['application']
    application.stage = ApplicationStage.INTERVIEW
    application.save(update_fields=['stage', 'modified_at'])

    response = client.get('/api/v1/org/recruitment/applications/', {'stage': ApplicationStage.INTERVIEW})

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['candidate_name'] == 'Priya Nair'


@pytest.mark.django_db
def test_org_admin_can_advance_application_stage(recruitment_api_setup):
    client = recruitment_api_setup['client']
    application = recruitment_api_setup['application']

    response = client.post(
        f'/api/v1/org/recruitment/applications/{application.id}/stage/',
        {'stage': ApplicationStage.SCREENING},
        format='json',
    )

    application.refresh_from_db()
    assert response.status_code == 200
    assert response.data['stage'] == ApplicationStage.SCREENING
    assert application.stage == ApplicationStage.SCREENING


@pytest.mark.django_db
def test_org_admin_can_schedule_interview_for_application(recruitment_api_setup):
    client = recruitment_api_setup['client']
    application = recruitment_api_setup['application']
    interviewer = recruitment_api_setup['interviewer']

    response = client.post(
        f'/api/v1/org/recruitment/applications/{application.id}/interviews/',
        {
            'interviewer_id': str(interviewer.id),
            'scheduled_at': '2026-04-15T10:30:00Z',
            'format': 'VIDEO',
            'meet_link': 'https://meet.example.com/recruitment-round-1',
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['format'] == 'VIDEO'
    assert Interview.objects.filter(application=application).count() == 1


@pytest.mark.django_db
def test_org_admin_can_create_offer_letter(recruitment_api_setup):
    client = recruitment_api_setup['client']
    application = recruitment_api_setup['application']
    application.stage = ApplicationStage.OFFER
    application.save(update_fields=['stage', 'modified_at'])

    response = client.post(
        f'/api/v1/org/recruitment/applications/{application.id}/offer/',
        {
            'ctc_annual': '1450000.00',
            'joining_date': '2026-05-15',
            'template_text': 'Offer details',
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['status'] == 'DRAFT'
    assert OfferLetter.objects.filter(application=application).exists()


@pytest.mark.django_db
def test_org_admin_can_accept_offer_and_onboard_candidate(recruitment_api_setup):
    client = recruitment_api_setup['client']
    application = recruitment_api_setup['application']
    application.stage = ApplicationStage.OFFER
    application.save(update_fields=['stage', 'modified_at'])
    offer = OfferLetter.objects.create(
        application=application,
        ctc_annual=Decimal('1450000.00'),
        joining_date=date(2026, 5, 15),
    )

    response = client.post(f'/api/v1/org/recruitment/offers/{offer.id}/accept/', format='json')

    offer.refresh_from_db()
    application.refresh_from_db()
    assert response.status_code == 200
    assert response.data['status'] == 'INVITED'
    assert offer.onboarded_employee is not None
    assert application.stage == ApplicationStage.HIRED
    assert Invitation.objects.filter(organisation=recruitment_api_setup['organisation']).count() == 1
