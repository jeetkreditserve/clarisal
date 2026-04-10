import pytest
from datetime import date, datetime
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.employees.models import Employee, EmployeeOffboardingProcess, OffboardingProcessStatus
from apps.employees.services import (
    create_exit_interview_template,
    schedule_exit_interview,
    record_exit_interview_response,
    complete_exit_interview,
    get_exit_interview_summary,
    create_or_update_offboarding_process,
)


@pytest.fixture
def org_admin(db):
    return User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )


@pytest.fixture
def employee_user(db):
    return User.objects.create_user(
        email='john@org.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )


@pytest.fixture
def organisation(db, org_admin):
    from apps.organisations.models import Organisation, OrganisationAccessState, OrganisationBillingStatus, OrganisationStatus
    return Organisation.objects.create(
        name='Test Org',
        created_by=org_admin,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def employee(db, organisation, employee_user):
    return Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP001',
    )


@pytest.fixture
def offboarding_process(db, employee, org_admin):
    return create_or_update_offboarding_process(
        employee=employee,
        exit_status='NOTICE_PERIOD',
        date_of_exit=date(2026, 4, 30),
        actor=org_admin,
    )


class TestExitInterviewTemplateService:
    def test_create_template(self, organisation, org_admin):
        template = create_exit_interview_template(
            organisation=organisation,
            name="Standard Exit Interview",
            description="Standard questions for all exits",
            questions=[
                {'question_text': 'Why are you leaving?', 'question_type': 'TEXT'},
                {'question_text': 'Rate your manager', 'question_type': 'RATING'},
            ],
            actor=org_admin,
        )
        assert template.name == "Standard Exit Interview"
        assert template.questions.count() == 2

    def test_create_template_without_questions(self, organisation, org_admin):
        template = create_exit_interview_template(
            organisation=organisation,
            name="Simple Template",
            actor=org_admin,
        )
        assert template.questions.count() == 0


class TestExitInterviewService:
    def test_schedule_interview(self, organisation, offboarding_process, org_admin):
        template = create_exit_interview_template(
            organisation=organisation,
            name="Test Template",
            actor=org_admin,
        )
        
        scheduled_time = timezone.now()
        interview = schedule_exit_interview(
            process=offboarding_process,
            scheduled_date=scheduled_time,
            stage='EXIT',
            template=template,
            actor=org_admin,
        )
        
        assert interview.stage == 'EXIT'
        assert interview.template == template
        assert interview.scheduled_date is not None

    def test_record_response_rating(self, organisation, offboarding_process, org_admin):
        template = create_exit_interview_template(
            organisation=organisation,
            name="Test Template",
            questions=[
                {'question_text': 'Rate overall experience', 'question_type': 'RATING', 'order': 1},
            ],
            actor=org_admin,
        )
        interview = schedule_exit_interview(
            process=offboarding_process,
            scheduled_date=timezone.now(),
            template=template,
            actor=org_admin,
        )
        question = template.questions.first()
        
        response = record_exit_interview_response(
            interview=interview,
            question=question,
            rating_value=4,
            actor=org_admin,
        )
        
        assert response.rating_value == 4

    def test_record_response_text(self, organisation, offboarding_process, org_admin):
        template = create_exit_interview_template(
            organisation=organisation,
            name="Test Template",
            questions=[
                {'question_text': 'Why leaving?', 'question_type': 'TEXT', 'order': 1},
            ],
            actor=org_admin,
        )
        interview = schedule_exit_interview(
            process=offboarding_process,
            scheduled_date=timezone.now(),
            template=template,
            actor=org_admin,
        )
        question = template.questions.first()
        
        response = record_exit_interview_response(
            interview=interview,
            question=question,
            text_value="Better opportunity",
            actor=org_admin,
        )
        
        assert response.text_value == "Better opportunity"

    def test_complete_interview(self, organisation, offboarding_process, org_admin):
        template = create_exit_interview_template(
            organisation=organisation,
            name="Test Template",
            actor=org_admin,
        )
        interview = schedule_exit_interview(
            process=offboarding_process,
            scheduled_date=timezone.now(),
            template=template,
            actor=org_admin,
        )
        
        completed = complete_exit_interview(
            interview=interview,
            notes="Good exit process",
            overall_rating=4,
            conducted_by=org_admin,
            actor=org_admin,
        )
        
        assert completed.overall_rating == 4
        assert completed.conducted_date is not None

    def test_get_interview_summary(self, organisation, offboarding_process, org_admin):
        template = create_exit_interview_template(
            organisation=organisation,
            name="Test Template",
            questions=[
                {'question_text': 'Rate work', 'question_type': 'RATING', 'order': 1},
            ],
            actor=org_admin,
        )
        interview = schedule_exit_interview(
            process=offboarding_process,
            scheduled_date=timezone.now(),
            template=template,
            actor=org_admin,
        )
        
        question = template.questions.first()
        record_exit_interview_response(
            interview=interview,
            question=question,
            rating_value=5,
            actor=org_admin,
        )
        
        summary = get_exit_interview_summary(interview)
        assert summary['employee_name'] is not None
        assert summary['response_count'] == 1
        assert summary['responses'][0]['rating_value'] == 5
