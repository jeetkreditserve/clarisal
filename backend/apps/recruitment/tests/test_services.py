from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import ApprovalRequestKind, ApprovalWorkflow
from apps.employees.models import EmployeeStatus
from apps.invitations.models import Invitation, InvitationRole, InvitationStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.recruitment.models import (
    Application,
    ApplicationStage,
    Candidate,
    JobPosting,
    JobPostingStatus,
    OfferStatus,
)


def _create_organisation(name='Recruitment Org'):
    organisation = Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    return organisation


def _create_user(email, *, organisation=None, role=UserRole.ORG_ADMIN):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=role,
        organisation=organisation,
        is_active=True,
    )


def _seed_licences(organisation, actor):
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        created_by=actor,
    )
    mark_licence_batch_paid(batch, paid_by=actor, paid_at=date(2026, 4, 1))


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


@pytest.mark.django_db
class TestJobPosting:
    def test_create_job_posting_draft(self):
        from apps.recruitment.services import create_job_posting

        organisation = _create_organisation()
        user = _create_user('recruiter@test.com', organisation=organisation)

        posting = create_job_posting(
            organisation=organisation,
            title='Software Engineer',
            description='Build features',
            actor=user,
        )

        assert posting.status == JobPostingStatus.DRAFT
        assert posting.title == 'Software Engineer'


@pytest.mark.django_db
class TestApplicationStageAdvance:
    def test_advance_stage_from_applied_to_screening(self):
        from apps.recruitment.services import advance_application_stage

        organisation = _create_organisation()
        user = _create_user('stage-actor@test.com', organisation=organisation)
        posting = JobPosting.objects.create(
            organisation=organisation,
            title='Engineer',
            status=JobPostingStatus.OPEN,
        )
        candidate = Candidate.objects.create(
            organisation=organisation,
            first_name='Jane',
            last_name='Doe',
            email='jane@example.com',
        )
        application = Application.objects.create(
            candidate=candidate,
            job_posting=posting,
            stage=ApplicationStage.APPLIED,
        )

        advance_application_stage(application, ApplicationStage.SCREENING, actor=user)
        application.refresh_from_db()

        assert application.stage == ApplicationStage.SCREENING

    def test_cannot_advance_rejected_application(self):
        from apps.recruitment.services import advance_application_stage

        organisation = _create_organisation()
        user = _create_user('stage-reject@test.com', organisation=organisation)
        posting = JobPosting.objects.create(
            organisation=organisation,
            title='Engineer',
            status=JobPostingStatus.OPEN,
        )
        candidate = Candidate.objects.create(
            organisation=organisation,
            first_name='Jane',
            last_name='Doe',
            email='jane2@example.com',
        )
        application = Application.objects.create(
            candidate=candidate,
            job_posting=posting,
            stage=ApplicationStage.REJECTED,
        )

        with pytest.raises(ValueError, match='Cannot advance'):
            advance_application_stage(application, ApplicationStage.SCREENING, actor=user)


@pytest.mark.django_db
class TestOfferAndOnboarding:
    def test_accept_offer_creates_employee_with_invited_status_and_invitation(self):
        from apps.recruitment.services import accept_offer_and_onboard, create_offer_letter

        organisation = _create_organisation()
        user = _create_user('offer-actor@test.com', organisation=organisation)
        _seed_licences(organisation, user)
        _seed_default_workflows(organisation, user)
        posting = JobPosting.objects.create(
            organisation=organisation,
            title='Engineer',
            status=JobPostingStatus.OPEN,
        )
        candidate = Candidate.objects.create(
            organisation=organisation,
            first_name='Bob',
            last_name='Smith',
            email='bob@example.com',
        )
        application = Application.objects.create(
            candidate=candidate,
            job_posting=posting,
            stage=ApplicationStage.OFFER,
        )

        offer = create_offer_letter(
            application=application,
            ctc_annual=Decimal('1200000'),
            joining_date=date(2026, 5, 1),
            actor=user,
        )
        employee = accept_offer_and_onboard(offer, actor=user)

        assert employee.status == EmployeeStatus.INVITED
        assert employee.user.email == 'bob@example.com'
        assert employee.date_of_joining == date(2026, 5, 1)
        invitation = Invitation.objects.get(user=employee.user, organisation=organisation, role=InvitationRole.EMPLOYEE)
        assert invitation.status == InvitationStatus.PENDING

    def test_accept_offer_sets_application_stage_to_hired(self):
        from apps.recruitment.services import accept_offer_and_onboard, create_offer_letter

        organisation = _create_organisation()
        user = _create_user('offer-stage@test.com', organisation=organisation)
        _seed_licences(organisation, user)
        _seed_default_workflows(organisation, user)
        posting = JobPosting.objects.create(
            organisation=organisation,
            title='Engineer',
            status=JobPostingStatus.OPEN,
        )
        candidate = Candidate.objects.create(
            organisation=organisation,
            first_name='Bob',
            last_name='Smith',
            email='bob2@example.com',
        )
        application = Application.objects.create(
            candidate=candidate,
            job_posting=posting,
            stage=ApplicationStage.OFFER,
        )

        offer = create_offer_letter(
            application=application,
            ctc_annual=Decimal('1200000'),
            joining_date=date(2026, 5, 1),
            actor=user,
        )
        accept_offer_and_onboard(offer, actor=user)
        application.refresh_from_db()
        offer.refresh_from_db()

        assert application.stage == ApplicationStage.HIRED
        assert offer.status == OfferStatus.ACCEPTED
        assert offer.onboarded_employee is not None
