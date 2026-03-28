import uuid
from django.conf import settings
from django.db import models


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


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='documents',
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.document_type} - {self.employee.employee_code}'
