from django.db import models

from apps.common.models import AuditedBaseModel


class CycleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ACTIVE = 'ACTIVE', 'Active'
    CLOSED = 'CLOSED', 'Closed'


class GoalStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ReviewType(models.TextChoices):
    SELF = 'SELF', 'Self Review'
    MANAGER = 'MANAGER', 'Manager Review'
    REVIEW_360 = '360', '360° Review'


class ReviewRelationship(models.TextChoices):
    SELF = 'SELF', 'Self'
    MANAGER = 'MANAGER', 'Manager'
    PEER = 'PEER', 'Peer'
    SKIP_LEVEL = 'SKIP_LEVEL', 'Skip Level'
    DIRECT_REPORT = 'DIRECT_REPORT', 'Direct Report'


class ReviewStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'


class FeedbackStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    DECLINED = 'DECLINED', 'Declined'


class GoalCycle(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='goal_cycles',
    )
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=CycleStatus.choices, default=CycleStatus.DRAFT)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['organisation', 'start_date', 'end_date']),
        ]

    def __str__(self):
        return f'{self.name} ({self.status})'


class Goal(AuditedBaseModel):
    cycle = models.ForeignKey(GoalCycle, on_delete=models.CASCADE, related_name='goals')
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='goals',
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    target = models.TextField(blank=True, help_text='Measurable target / key result')
    metric = models.CharField(max_length=100, blank=True, help_text='Unit of measurement')
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    status = models.CharField(max_length=20, choices=GoalStatus.choices, default=GoalStatus.NOT_STARTED)
    due_date = models.DateField(null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['cycle', 'employee']),
        ]

    def __str__(self):
        return f'{self.title} - {self.employee}'


class AppraisalCycle(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='appraisal_cycles',
    )
    name = models.CharField(max_length=200)
    review_type = models.CharField(max_length=20, choices=ReviewType.choices, default=ReviewType.SELF)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=CycleStatus.choices, default=CycleStatus.DRAFT)
    is_probation_review = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['organisation', 'is_probation_review']),
        ]

    def __str__(self):
        return f'{self.name} ({self.review_type})'


class AppraisalReview(AuditedBaseModel):
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE, related_name='reviews')
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='appraisal_reviews',
    )
    reviewer = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='reviews_given',
        null=True,
        blank=True,
    )
    relationship = models.CharField(max_length=20, choices=ReviewRelationship.choices)
    ratings = models.JSONField(default=dict, help_text='{"competency_id": rating_score, ...}')
    comments = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['cycle', 'employee', 'reviewer', 'relationship'],
                name='unique_appraisal_review_per_cycle_employee_reviewer_relationship',
            ),
        ]
        indexes = [
            models.Index(fields=['cycle', 'employee']),
            models.Index(fields=['reviewer', 'status']),
        ]


class FeedbackRequest(AuditedBaseModel):
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE, related_name='feedback_requests')
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='feedback_requests_received',
    )
    requested_from = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='feedback_requests_to_give',
    )
    status = models.CharField(max_length=20, choices=FeedbackStatus.choices, default=FeedbackStatus.REQUESTED)
    due_date = models.DateField(null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cycle', 'status']),
            models.Index(fields=['requested_from', 'status']),
        ]
