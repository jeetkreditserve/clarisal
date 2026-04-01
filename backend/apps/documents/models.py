from django.conf import settings
from django.db import models

from apps.common.models import AuditedBaseModel


class DocumentType(models.TextChoices):
    PAN = 'PAN', 'PAN Card'
    AADHAAR = 'AADHAAR', 'Aadhaar Card'
    EDUCATION_CERT = 'EDUCATION_CERT', 'Education Certificate'
    EMPLOYMENT_LETTER = 'EMPLOYMENT_LETTER', 'Employment Letter'
    OTHER = 'OTHER', 'Other'


class DocumentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    VERIFIED = 'VERIFIED', 'Verified'
    REJECTED = 'REJECTED', 'Rejected'


class OnboardingDocumentCategory(models.TextChoices):
    IDENTITY_TAX = 'IDENTITY_TAX', 'Identity & Tax'
    ADDRESS = 'ADDRESS', 'Address'
    BANKING_PAYROLL = 'BANKING_PAYROLL', 'Banking & Payroll'
    EDUCATION = 'EDUCATION', 'Education'
    PREVIOUS_EMPLOYMENT = 'PREVIOUS_EMPLOYMENT', 'Previous Employment'
    STATUTORY_BENEFITS = 'STATUTORY_BENEFITS', 'Statutory Benefits'
    FAMILY_NOMINEE = 'FAMILY_NOMINEE', 'Family & Nominee'
    MEDICAL_SAFETY = 'MEDICAL_SAFETY', 'Medical & Safety'
    POLICY_ACK = 'POLICY_ACK', 'Policy Acknowledgement'
    ROLE_COMPLIANCE = 'ROLE_COMPLIANCE', 'Role Compliance'
    CUSTOM = 'CUSTOM', 'Custom'


class EmployeeDocumentRequestStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    VERIFIED = 'VERIFIED', 'Verified'
    REJECTED = 'REJECTED', 'Rejected'
    WAIVED = 'WAIVED', 'Waived'


class OnboardingDocumentType(AuditedBaseModel):
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=OnboardingDocumentCategory.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_custom = models.BooleanField(default=False)
    requires_identifier = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_onboarding_document_types',
    )
    class Meta:
        db_table = 'onboarding_document_types'
        ordering = ['category', 'sort_order', 'name']

    def __str__(self):
        return self.name


class EmployeeDocumentRequest(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='document_requests',
    )
    document_type_ref = models.ForeignKey(
        OnboardingDocumentType,
        on_delete=models.PROTECT,
        related_name='employee_requests',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='requested_employee_documents',
    )
    is_required = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=EmployeeDocumentRequestStatus.choices,
        default=EmployeeDocumentRequestStatus.REQUESTED,
    )
    note = models.TextField(blank=True)
    rejection_note = models.TextField(blank=True)
    latest_uploaded_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_employee_document_requests',
    )
    waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='waived_employee_document_requests',
    )
    class Meta:
        db_table = 'employee_document_requests'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'document_type_ref'],
                name='unique_document_request_per_employee_type',
            ),
        ]
        indexes = [
            models.Index(fields=['employee', 'status']),
        ]

    def __str__(self):
        return f'{self.employee} - {self.document_type_ref.name}'


class Document(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='documents',
    )
    document_request = models.ForeignKey(
        EmployeeDocumentRequest,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    document_type = models.CharField(max_length=60)
    file_key = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_documents',
    )
    metadata = models.JSONField(default=dict, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)
    version = models.PositiveIntegerField(default=1)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_documents',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.document_type} - {self.employee.employee_code}'
