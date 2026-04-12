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
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='job_postings',
    )
    title = models.CharField(max_length=200)
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_postings',
    )
    location = models.ForeignKey(
        'locations.OfficeLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_postings',
    )
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=JobPostingStatus.choices, default=JobPostingStatus.DRAFT)
    posted_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['organisation', 'posted_at']),
        ]

    def __str__(self):
        return f'{self.title} ({self.status})'


class Candidate(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='candidates',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    resume_file_key = models.CharField(max_length=500, blank=True, help_text='S3 object key')
    source = models.CharField(max_length=100, blank=True, help_text='LinkedIn, Naukri, Referral, etc.')
    converted_to_employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sourced_candidates',
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['organisation', 'email'], name='unique_candidate_email_per_org'),
        ]
        indexes = [
            models.Index(fields=['organisation', 'email']),
        ]

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
        ordering = ['-applied_at']
        constraints = [
            models.UniqueConstraint(fields=['candidate', 'job_posting'], name='unique_candidate_job_application'),
        ]
        indexes = [
            models.Index(fields=['job_posting', 'stage']),
            models.Index(fields=['candidate', 'stage']),
        ]

    def __str__(self):
        return f'{self.candidate} -> {self.job_posting} ({self.stage})'


class Interview(AuditedBaseModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interviewer = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interviews_conducted',
    )
    scheduled_at = models.DateTimeField()
    format = models.CharField(max_length=20, choices=InterviewFormat.choices, default=InterviewFormat.VIDEO)
    feedback = models.TextField(blank=True)
    outcome = models.CharField(max_length=20, choices=InterviewOutcome.choices, default=InterviewOutcome.PENDING)
    meet_link = models.URLField(blank=True)

    class Meta:
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['application', 'scheduled_at']),
            models.Index(fields=['interviewer', 'scheduled_at']),
        ]


class OfferLetter(AuditedBaseModel):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='offer_letter')
    ctc_annual = models.DecimalField(max_digits=14, decimal_places=2)
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=OfferStatus.choices, default=OfferStatus.DRAFT)
    template_text = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    onboarded_employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offer_letter',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'expires_at']),
        ]
