# P11 — Recruitment Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an Applicant Tracking System (ATS) with job postings, candidate management, interview scheduling, offer letters, and automatic employee onboarding on hire acceptance.

**Architecture:** New `recruitment` Django app. When an offer letter is accepted (`OfferLetter.status = ACCEPTED`), a service function auto-creates an `Employee` with `INVITED` status and dispatches an invitation email via the existing Celery infrastructure. All views use workspace-scoped permission checks.

**Tech Stack:** Django 4.2 · DRF · Celery 5.4 · React 19 · TypeScript · TanStack Query v5

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/apps/recruitment/__init__.py` | Create | App package |
| `backend/apps/recruitment/apps.py` | Create | App config |
| `backend/apps/recruitment/models.py` | Create | JobPosting, Candidate, Application, Interview, OfferLetter |
| `backend/apps/recruitment/services.py` | Create | Business logic: stage transitions, hire onboarding |
| `backend/apps/recruitment/serializers.py` | Create | API serializers |
| `backend/apps/recruitment/views.py` | Create | CRUD views |
| `backend/apps/recruitment/urls.py` | Create | URL patterns |
| `backend/apps/recruitment/tests/test_services.py` | Create | Service unit tests |
| `backend/apps/employees/services.py` | Modify | Add `create_employee_from_offer()` |
| `backend/clarisal/settings/base.py` | Modify | Add to INSTALLED_APPS |
| `backend/clarisal/urls.py` | Modify | Register URLs |
| `frontend/src/lib/api/recruitment.ts` | Create | API functions |
| `frontend/src/pages/org/JobPostingsPage.tsx` | Create | Job postings list |
| `frontend/src/pages/org/ApplicationsPage.tsx` | Create | Applications pipeline |
| `frontend/src/pages/org/CandidateDetailPage.tsx` | Create | Candidate detail / interview log |

---

## Task 1 — `recruitment` App and Models

**Files:**
- Create: `backend/apps/recruitment/models.py`

- [ ] **Step 1: Create app**

```bash
cd backend && python manage.py startapp recruitment apps/recruitment
```

Update `apps.py`:
```python
from django.apps import AppConfig

class RecruitmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recruitment'
    label = 'recruitment'
```

Add `'apps.recruitment'` to `LOCAL_APPS` in `backend/clarisal/settings/base.py`.

- [ ] **Step 2: Write `models.py`**

```python
# backend/apps/recruitment/models.py
from django.db import models
from apps.common.models import AuditedBaseModel


class JobPostingStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    OPEN = 'OPEN', 'Open'
    PAUSED = 'PAUSED', 'Paused'
    CLOSED = 'CLOSED', 'Closed'
    FILLED = 'FILLED', 'Filled'


class ApplicationStage(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SCREENING = 'SCREENING', 'Screening'
    INTERVIEW = 'INTERVIEW', 'Interview'
    OFFER = 'OFFER', 'Offer'
    HIRED = 'HIRED', 'Hired'
    REJECTED = 'REJECTED', 'Rejected'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'


class InterviewFormat(models.TextChoices):
    PHONE = 'PHONE', 'Phone'
    VIDEO = 'VIDEO', 'Video'
    IN_PERSON = 'IN_PERSON', 'In Person'
    TECHNICAL = 'TECHNICAL', 'Technical'


class InterviewOutcome(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PASSED = 'PASSED', 'Passed'
    FAILED = 'FAILED', 'Failed'
    NO_SHOW = 'NO_SHOW', 'No Show'


class OfferStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SENT = 'SENT', 'Sent'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    DECLINED = 'DECLINED', 'Declined'
    EXPIRED = 'EXPIRED', 'Expired'
    REVOKED = 'REVOKED', 'Revoked'


class JobPosting(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation', on_delete=models.CASCADE, related_name='job_postings'
    )
    title = models.CharField(max_length=200)
    department = models.ForeignKey(
        'departments.Department', on_delete=models.SET_NULL, null=True, blank=True
    )
    location = models.ForeignKey(
        'locations.Location', on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=JobPostingStatus.choices, default=JobPostingStatus.DRAFT)
    posted_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.title} ({self.status})'


class Candidate(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation', on_delete=models.CASCADE, related_name='candidates'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    resume_file_key = models.CharField(max_length=500, blank=True, help_text='S3 object key')
    source = models.CharField(max_length=100, blank=True, help_text='LinkedIn, Naukri, Referral, etc.')

    class Meta:
        unique_together = [('organisation', 'email')]

    def __str__(self):
        return f'{self.first_name} {self.last_name} <{self.email}>'


class Application(AuditedBaseModel):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    stage = models.CharField(max_length=20, choices=ApplicationStage.choices, default=ApplicationStage.APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        unique_together = [('candidate', 'job_posting')]

    def __str__(self):
        return f'{self.candidate} → {self.job_posting} ({self.stage})'


class Interview(AuditedBaseModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interviewer = models.ForeignKey(
        'employees.Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='interviews_conducted'
    )
    scheduled_at = models.DateTimeField()
    format = models.CharField(max_length=20, choices=InterviewFormat.choices, default=InterviewFormat.VIDEO)
    feedback = models.TextField(blank=True)
    outcome = models.CharField(max_length=20, choices=InterviewOutcome.choices, default=InterviewOutcome.PENDING)
    meet_link = models.URLField(blank=True)


class OfferLetter(AuditedBaseModel):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='offer_letter')
    ctc_annual = models.DecimalField(max_digits=14, decimal_places=2)
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=OfferStatus.choices, default=OfferStatus.DRAFT)
    template_text = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    # FK to created employee (set after onboarding handoff)
    onboarded_employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offer_letter',
    )
```

- [ ] **Step 3: Generate and apply migration**

```bash
cd backend && python manage.py makemigrations recruitment --name initial
cd backend && python manage.py migrate
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/recruitment/ backend/clarisal/settings/base.py
git commit -m "feat(recruitment): create recruitment app with JobPosting, Candidate, Application, Interview, OfferLetter models"
```

---

## Task 2 — Recruitment Service Layer

**Files:**
- Create: `backend/apps/recruitment/services.py`
- Modify: `backend/apps/employees/services.py`
- Create: `backend/apps/recruitment/tests/__init__.py`
- Create: `backend/apps/recruitment/tests/test_services.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/recruitment/tests/test_services.py
from datetime import date
from decimal import Decimal
from django.test import TestCase
from apps.recruitment.models import (
    JobPosting, Candidate, Application, ApplicationStage,
    OfferLetter, OfferStatus, JobPostingStatus,
)
from apps.recruitment.services import (
    create_job_posting,
    add_candidate,
    advance_application_stage,
    create_offer_letter,
    accept_offer_and_onboard,
)
from apps.employees.models import Employee, EmployeeStatus
from apps.accounts.tests.factories import UserFactory, OrganisationFactory


class TestJobPosting(TestCase):
    def test_create_job_posting_draft(self):
        org = OrganisationFactory()
        user = UserFactory()
        posting = create_job_posting(
            organisation=org,
            title='Software Engineer',
            description='Build features',
            actor=user,
        )
        self.assertEqual(posting.status, JobPostingStatus.DRAFT)
        self.assertEqual(posting.title, 'Software Engineer')


class TestApplicationStageAdvance(TestCase):
    def setUp(self):
        self.org = OrganisationFactory()
        self.user = UserFactory()
        self.posting = JobPosting.objects.create(
            organisation=self.org, title='Eng', status=JobPostingStatus.OPEN
        )
        self.candidate = Candidate.objects.create(
            organisation=self.org, first_name='Jane', last_name='Doe', email='jane@example.com'
        )
        self.application = Application.objects.create(
            candidate=self.candidate, job_posting=self.posting, stage=ApplicationStage.APPLIED
        )

    def test_advance_stage_from_applied_to_screening(self):
        advance_application_stage(self.application, ApplicationStage.SCREENING, actor=self.user)
        self.application.refresh_from_db()
        self.assertEqual(self.application.stage, ApplicationStage.SCREENING)

    def test_cannot_advance_rejected_application(self):
        self.application.stage = ApplicationStage.REJECTED
        self.application.save()
        with self.assertRaises(ValueError):
            advance_application_stage(self.application, ApplicationStage.SCREENING, actor=self.user)


class TestOfferAndOnboarding(TestCase):
    def setUp(self):
        self.org = OrganisationFactory()
        self.user = UserFactory()
        self.posting = JobPosting.objects.create(
            organisation=self.org, title='Eng', status=JobPostingStatus.OPEN
        )
        self.candidate = Candidate.objects.create(
            organisation=self.org, first_name='Bob', last_name='Smith',
            email='bob@example.com',
        )
        self.application = Application.objects.create(
            candidate=self.candidate, job_posting=self.posting, stage=ApplicationStage.OFFER
        )

    def test_accept_offer_creates_employee_with_invited_status(self):
        offer = create_offer_letter(
            application=self.application,
            ctc_annual=Decimal('1200000'),
            joining_date=date(2024, 5, 1),
            actor=self.user,
        )
        employee = accept_offer_and_onboard(offer, actor=self.user)
        self.assertIsNotNone(employee)
        self.assertEqual(employee.status, EmployeeStatus.INVITED)
        self.assertEqual(employee.user.email, 'bob@example.com')

    def test_accept_offer_sets_application_stage_to_hired(self):
        offer = create_offer_letter(
            application=self.application,
            ctc_annual=Decimal('1200000'),
            joining_date=date(2024, 5, 1),
            actor=self.user,
        )
        accept_offer_and_onboard(offer, actor=self.user)
        self.application.refresh_from_db()
        self.assertEqual(self.application.stage, ApplicationStage.HIRED)
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && python -m pytest apps/recruitment/tests/test_services.py -v
```

Expected: FAIL.

- [ ] **Step 3: Create `recruitment/services.py`**

```python
# backend/apps/recruitment/services.py
from __future__ import annotations
from datetime import date
from decimal import Decimal
from django.utils import timezone

from .models import (
    JobPosting, JobPostingStatus, Candidate, Application, ApplicationStage,
    OfferLetter, OfferStatus,
)

TERMINAL_STAGES = {ApplicationStage.HIRED, ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN}


def create_job_posting(organisation, title: str, description: str = '', actor=None, **kwargs) -> JobPosting:
    return JobPosting.objects.create(
        organisation=organisation,
        title=title,
        description=description,
        status=JobPostingStatus.DRAFT,
        created_by=actor,
        **kwargs,
    )


def publish_job_posting(posting: JobPosting, actor) -> JobPosting:
    posting.status = JobPostingStatus.OPEN
    posting.posted_at = timezone.now()
    posting.modified_by = actor
    posting.save(update_fields=['status', 'posted_at', 'modified_at', 'modified_by'])
    return posting


def add_candidate(organisation, first_name: str, last_name: str, email: str, actor=None, **kwargs) -> Candidate:
    candidate, _ = Candidate.objects.get_or_create(
        organisation=organisation,
        email=email,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'created_by': actor,
            **kwargs,
        },
    )
    return candidate


def apply_to_posting(candidate: Candidate, posting: JobPosting, actor=None) -> Application:
    app, created = Application.objects.get_or_create(
        candidate=candidate,
        job_posting=posting,
        defaults={'stage': ApplicationStage.APPLIED, 'created_by': actor},
    )
    if not created:
        raise ValueError('Candidate has already applied to this posting.')
    return app


def advance_application_stage(application: Application, new_stage: str, actor=None) -> Application:
    if application.stage in TERMINAL_STAGES:
        raise ValueError(f'Cannot advance a {application.stage} application.')
    application.stage = new_stage
    application.modified_by = actor
    application.save(update_fields=['stage', 'modified_at', 'modified_by'])
    return application


def create_offer_letter(
    application: Application,
    ctc_annual: Decimal,
    joining_date: date = None,
    actor=None,
) -> OfferLetter:
    offer = OfferLetter.objects.create(
        application=application,
        ctc_annual=ctc_annual,
        joining_date=joining_date,
        status=OfferStatus.DRAFT,
        created_by=actor,
    )
    return offer


def accept_offer_and_onboard(offer: OfferLetter, actor=None):
    """
    Accept an offer letter and automatically create an Employee (INVITED status).
    Sends invitation email via existing employee invitation system.
    """
    from apps.employees.services import create_employee_from_offer

    offer.status = OfferStatus.ACCEPTED
    offer.accepted_at = timezone.now()
    offer.modified_by = actor
    offer.save(update_fields=['status', 'accepted_at', 'modified_at', 'modified_by'])

    # Advance application to HIRED
    advance_application_stage(offer.application, ApplicationStage.HIRED, actor=actor)

    # Create the employee
    employee = create_employee_from_offer(offer, actor=actor)
    offer.onboarded_employee = employee
    offer.save(update_fields=['onboarded_employee'])

    return employee
```

- [ ] **Step 4: Add `create_employee_from_offer` to `employees/services.py`**

Open `backend/apps/employees/services.py`. Add:

```python
def create_employee_from_offer(offer, actor=None):
    """
    Create an Employee with INVITED status from a recruitment OfferLetter.
    Reuses existing invitation infrastructure.
    """
    from django.contrib.auth import get_user_model
    from apps.invitations.services import create_invitation_for_user
    from .models import Employee, EmployeeStatus

    User = get_user_model()
    candidate = offer.application.candidate
    organisation = offer.application.job_posting.organisation

    # Get or create Django user for candidate
    user, created = User.objects.get_or_create(
        email=candidate.email,
        defaults={
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'username': candidate.email,
        },
    )

    employee = Employee.objects.create(
        organisation=organisation,
        user=user,
        status=EmployeeStatus.INVITED,
        date_of_joining=offer.joining_date,
        created_by=actor,
    )

    # Send invitation email
    try:
        create_invitation_for_user(user=user, organisation=organisation, actor=actor)
    except Exception:
        pass  # Do not fail employee creation if email fails

    return employee
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest apps/recruitment/tests/test_services.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/recruitment/services.py \
        backend/apps/recruitment/tests/ \
        backend/apps/employees/services.py
git commit -m "feat(recruitment): recruitment service layer — job postings, applications, offer acceptance, employee onboarding"
```

---

## Task 3 — Recruitment API Endpoints

**Files:**
- Create: `backend/apps/recruitment/serializers.py`
- Create: `backend/apps/recruitment/views.py`
- Create: `backend/apps/recruitment/urls.py`
- Modify: `backend/clarisal/urls.py`

- [ ] **Step 1: Create `serializers.py`**

```python
# backend/apps/recruitment/serializers.py
from rest_framework import serializers
from .models import JobPosting, Candidate, Application, Interview, OfferLetter


class JobPostingSerializer(serializers.ModelSerializer):
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = JobPosting
        fields = ['id', 'title', 'department', 'location', 'description', 'requirements',
                  'status', 'posted_at', 'closes_at', 'application_count', 'created_at']
        read_only_fields = ['id', 'application_count', 'created_at']

    def get_application_count(self, obj):
        return obj.applications.count()


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'source', 'created_at']
        read_only_fields = ['id', 'created_at']


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ['id', 'candidate', 'candidate_name', 'job_posting', 'stage', 'applied_at', 'notes']
        read_only_fields = ['id', 'applied_at', 'candidate_name']

    def get_candidate_name(self, obj):
        return f'{obj.candidate.first_name} {obj.candidate.last_name}'


class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = ['id', 'application', 'interviewer', 'scheduled_at', 'format',
                  'feedback', 'outcome', 'meet_link']
        read_only_fields = ['id']


class OfferLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferLetter
        fields = ['id', 'application', 'ctc_annual', 'joining_date', 'status',
                  'template_text', 'sent_at', 'accepted_at', 'expires_at', 'onboarded_employee']
        read_only_fields = ['id', 'sent_at', 'accepted_at', 'onboarded_employee']
```

- [ ] **Step 2: Create `views.py`**

```python
# backend/apps/recruitment/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from .models import JobPosting, Candidate, Application, ApplicationStage, OfferLetter
from .serializers import (
    JobPostingSerializer, CandidateSerializer, ApplicationSerializer,
    InterviewSerializer, OfferLetterSerializer,
)
from .services import (
    create_job_posting, publish_job_posting,
    add_candidate, apply_to_posting, advance_application_stage,
    create_offer_letter, accept_offer_and_onboard,
)


class OrgJobPostingListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        org = get_active_admin_organisation(request, request.user)
        postings = JobPosting.objects.filter(organisation=org).order_by('-created_at')
        return Response(JobPostingSerializer(postings, many=True).data)

    def post(self, request):
        org = get_active_admin_organisation(request, request.user)
        serializer = JobPostingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        posting = create_job_posting(
            organisation=org, title=d['title'],
            description=d.get('description', ''),
            actor=request.user, **{k: v for k, v in d.items() if k not in ('title', 'description')}
        )
        return Response(JobPostingSerializer(posting).data, status=status.HTTP_201_CREATED)


class OrgApplicationListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        org = get_active_admin_organisation(request, request.user)
        stage = request.query_params.get('stage')
        qs = Application.objects.filter(
            job_posting__organisation=org
        ).select_related('candidate', 'job_posting')
        if stage:
            qs = qs.filter(stage=stage)
        return Response(ApplicationSerializer(qs, many=True).data)


class OrgApplicationStageView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        org = get_active_admin_organisation(request, request.user)
        application = get_object_or_404(Application, id=pk, job_posting__organisation=org)
        new_stage = request.data.get('stage')
        if not new_stage:
            return Response({'error': 'stage is required'}, status=400)
        try:
            application = advance_application_stage(application, new_stage, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)
        return Response(ApplicationSerializer(application).data)


class OrgOfferLetterView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, application_id):
        org = get_active_admin_organisation(request, request.user)
        application = get_object_or_404(Application, id=application_id, job_posting__organisation=org)
        serializer = OfferLetterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        offer = create_offer_letter(
            application=application,
            ctc_annual=d['ctc_annual'],
            joining_date=d.get('joining_date'),
            actor=request.user,
        )
        return Response(OfferLetterSerializer(offer).data, status=status.HTTP_201_CREATED)


class OrgOfferAcceptView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        org = get_active_admin_organisation(request, request.user)
        offer = get_object_or_404(OfferLetter, id=pk, application__job_posting__organisation=org)
        try:
            employee = accept_offer_and_onboard(offer, actor=request.user)
        except Exception as exc:
            return Response({'error': str(exc)}, status=400)
        return Response({'employee_id': str(employee.id), 'status': employee.status})
```

- [ ] **Step 3: Create `urls.py`**

```python
# backend/apps/recruitment/urls.py
from django.urls import path
from .views import (
    OrgJobPostingListCreateView, OrgApplicationListView,
    OrgApplicationStageView, OrgOfferLetterView, OrgOfferAcceptView,
)

urlpatterns = [
    path('recruitment/jobs/', OrgJobPostingListCreateView.as_view()),
    path('recruitment/applications/', OrgApplicationListView.as_view()),
    path('recruitment/applications/<uuid:pk>/stage/', OrgApplicationStageView.as_view()),
    path('recruitment/applications/<uuid:application_id>/offer/', OrgOfferLetterView.as_view()),
    path('recruitment/offers/<uuid:pk>/accept/', OrgOfferAcceptView.as_view()),
]
```

- [ ] **Step 4: Register in `clarisal/urls.py`**

Add `path('org/', include('apps.recruitment.urls'))` to both legacy and versioned includes.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/recruitment/serializers.py backend/apps/recruitment/views.py \
        backend/apps/recruitment/urls.py backend/clarisal/urls.py
git commit -m "feat(recruitment): REST API for job postings, applications, offer letters, onboarding handoff"
```

---

## Task 4 — Frontend Recruitment Pages

**Files:**
- Create: `frontend/src/lib/api/recruitment.ts`
- Create: `frontend/src/pages/org/JobPostingsPage.tsx`
- Create: `frontend/src/pages/org/ApplicationsPage.tsx`

- [ ] **Step 1: Create API file**

```typescript
// frontend/src/lib/api/recruitment.ts
import { apiClient } from './client';

export interface JobPosting {
  id: string;
  title: string;
  status: string;
  posted_at: string | null;
  application_count: number;
}

export interface Application {
  id: string;
  candidate_name: string;
  job_posting: string;
  stage: string;
  applied_at: string;
}

export const recruitmentApi = {
  getJobPostings: () => apiClient.get('/api/org/recruitment/jobs/').then(r => r.data as JobPosting[]),
  createJobPosting: (data: Partial<JobPosting>) =>
    apiClient.post('/api/org/recruitment/jobs/', data).then(r => r.data),
  getApplications: (stage?: string) =>
    apiClient.get('/api/org/recruitment/applications/', { params: stage ? { stage } : {} })
      .then(r => r.data as Application[]),
  advanceStage: (applicationId: string, newStage: string) =>
    apiClient.post(`/api/org/recruitment/applications/${applicationId}/stage/`, { stage: newStage })
      .then(r => r.data),
  createOffer: (applicationId: string, data: object) =>
    apiClient.post(`/api/org/recruitment/applications/${applicationId}/offer/`, data).then(r => r.data),
  acceptOffer: (offerId: string) =>
    apiClient.post(`/api/org/recruitment/offers/${offerId}/accept/`).then(r => r.data),
};
```

- [ ] **Step 2: Create `JobPostingsPage.tsx`**

```tsx
// frontend/src/pages/org/JobPostingsPage.tsx
import { useQuery } from '@tanstack/react-query';
import { recruitmentApi, JobPosting } from '@/lib/api/recruitment';
import { AppButton } from '@/components/ui/AppButton';

const STATUS_COLOURS: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-600',
  OPEN: 'bg-green-100 text-green-700',
  PAUSED: 'bg-yellow-100 text-yellow-700',
  CLOSED: 'bg-red-100 text-red-600',
  FILLED: 'bg-blue-100 text-blue-700',
};

export default function JobPostingsPage() {
  const { data: postings = [], isLoading } = useQuery({
    queryKey: ['job-postings'],
    queryFn: recruitmentApi.getJobPostings,
  });

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Job Postings</h1>
        <AppButton>New Posting</AppButton>
      </div>
      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : postings.length === 0 ? (
        <div className="text-center py-16 text-gray-400">No job postings yet.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-gray-500">
              <tr>
                <th className="py-3 pr-4">Title</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Posted</th>
                <th className="py-3">Applications</th>
              </tr>
            </thead>
            <tbody>
              {postings.map((p: JobPosting) => (
                <tr key={p.id} className="border-b hover:bg-gray-50 cursor-pointer">
                  <td className="py-3 pr-4 font-medium">{p.title}</td>
                  <td className="py-3 pr-4">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOURS[p.status] ?? 'bg-gray-100'}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-gray-500">
                    {p.posted_at ? new Date(p.posted_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="py-3 text-gray-600">{p.application_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create `ApplicationsPage.tsx`**

```tsx
// frontend/src/pages/org/ApplicationsPage.tsx
import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recruitmentApi, Application } from '@/lib/api/recruitment';
import toast from 'react-hot-toast';

const STAGES = ['APPLIED', 'SCREENING', 'INTERVIEW', 'OFFER', 'HIRED', 'REJECTED'];

export default function ApplicationsPage() {
  const [filterStage, setFilterStage] = React.useState('');
  const qc = useQueryClient();
  const { data: applications = [] } = useQuery({
    queryKey: ['applications', filterStage],
    queryFn: () => recruitmentApi.getApplications(filterStage || undefined),
  });

  const stageMutation = useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: string }) =>
      recruitmentApi.advanceStage(id, stage),
    onSuccess: () => {
      toast.success('Stage updated');
      qc.invalidateQueries({ queryKey: ['applications'] });
    },
    onError: () => toast.error('Failed to update stage'),
  });

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold mb-6">Applications</h1>
      <div className="mb-4">
        <label htmlFor="stage-filter" className="text-sm font-medium mr-2">Filter by stage:</label>
        <select
          id="stage-filter"
          className="border rounded-md px-2 py-1.5 text-sm"
          value={filterStage}
          onChange={e => setFilterStage(e.target.value)}
        >
          <option value="">All</option>
          {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-gray-500">
            <tr>
              <th className="py-3 pr-4">Candidate</th>
              <th className="py-3 pr-4">Current Stage</th>
              <th className="py-3 pr-4">Applied</th>
              <th className="py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {applications.map((app: Application) => (
              <tr key={app.id} className="border-b hover:bg-gray-50">
                <td className="py-3 pr-4 font-medium">{app.candidate_name}</td>
                <td className="py-3 pr-4">{app.stage}</td>
                <td className="py-3 pr-4 text-gray-500">
                  {new Date(app.applied_at).toLocaleDateString()}
                </td>
                <td className="py-3">
                  <select
                    className="border rounded text-xs px-1.5 py-1"
                    defaultValue={app.stage}
                    aria-label={`Move ${app.candidate_name} to stage`}
                    onChange={e => stageMutation.mutate({ id: app.id, stage: e.target.value })}
                  >
                    {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add routes and nav items**

In `frontend/src/routes/index.tsx`:
```tsx
{ path: '/org/recruitment/jobs', element: <JobPostingsPage /> }
{ path: '/org/recruitment/applications', element: <ApplicationsPage /> }
```

Add "Recruitment" group to `OrgLayout.tsx` with items: Job Postings, Applications.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/recruitment.ts \
        frontend/src/pages/org/JobPostingsPage.tsx \
        frontend/src/pages/org/ApplicationsPage.tsx \
        frontend/src/routes/index.tsx \
        frontend/src/components/layouts/OrgLayout.tsx
git commit -m "feat(recruitment): frontend pages for job postings and applications pipeline"
```

---

## Verification

```bash
cd backend && python -m pytest apps/recruitment/ -v
# Expected: all pass

python manage.py check
# Expected: no errors

# Test hire onboarding flow
python manage.py shell -c "
from apps.recruitment.tests.test_services import *
print('Import OK')
"
```
