import hashlib
import os
import uuid

from django.utils import timezone

from apps.audit.services import log_audit_event

from .models import Document, DocumentStatus
from .repositories import list_documents
from .s3 import generate_presigned_url, upload_file

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024


def _validate_upload(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Only PDF, PNG, JPG, and JPEG files are allowed.')
    if file_obj.size > MAX_FILE_SIZE:
        raise ValueError('Files must be 5 MB or smaller.')


def _build_key(employee, document_type, original_filename):
    ext = os.path.splitext(original_filename)[1].lower()
    safe_name = os.path.basename(original_filename).replace(' ', '-')
    return (
        f"organisations/{employee.organisation.slug}/employees/{employee.employee_code}/"
        f"{document_type.lower()}/{uuid.uuid4().hex}-{safe_name}{'' if safe_name.endswith(ext) else ext}"
    )


def upload_document(employee, file_obj, document_type, uploaded_by, metadata=None):
    _validate_upload(file_obj)
    file_bytes = file_obj.read()
    file_obj.seek(0)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    key = _build_key(employee, document_type, file_obj.name)
    upload_file(file_obj, key, getattr(file_obj, 'content_type', 'application/octet-stream'))
    document = Document.objects.create(
        employee=employee,
        document_type=document_type,
        file_key=key,
        file_name=file_obj.name,
        file_size=file_obj.size,
        mime_type=getattr(file_obj, 'content_type', 'application/octet-stream'),
        uploaded_by=uploaded_by,
        metadata=metadata or {},
        file_hash=file_hash,
    )
    log_audit_event(uploaded_by, 'document.uploaded', organisation=employee.organisation, target=document, payload={'document_type': document_type})
    return document


def generate_download_url(document):
    return generate_presigned_url(document.file_key)


def verify_document(document, reviewed_by):
    if document.status == DocumentStatus.VERIFIED:
        raise ValueError('Document is already verified.')
    document.status = DocumentStatus.VERIFIED
    document.reviewed_by = reviewed_by
    document.reviewed_at = timezone.now()
    document.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
    log_audit_event(reviewed_by, 'document.verified', organisation=document.employee.organisation, target=document)
    return document


def reject_document(document, reviewed_by, note=''):
    document.status = DocumentStatus.REJECTED
    document.reviewed_by = reviewed_by
    document.reviewed_at = timezone.now()
    metadata = document.metadata or {}
    metadata['rejection_note'] = note
    document.metadata = metadata
    document.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'metadata', 'updated_at'])
    log_audit_event(reviewed_by, 'document.rejected', organisation=document.employee.organisation, target=document, payload={'note': note})
    return document
