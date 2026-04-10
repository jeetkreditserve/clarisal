import hashlib
import os
import uuid

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_audit_event

from .models import (
    Document,
    DocumentStatus,
    EmployeeDocumentRequest,
    EmployeeDocumentRequestStatus,
    OnboardingDocumentCategory,
    OnboardingDocumentType,
)
from .s3 import generate_presigned_url, upload_file

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024
SIGNATURES_BY_EXTENSION = {
    '.pdf': (b'%PDF-',),
    '.png': (b'\x89PNG\r\n\x1a\n',),
    '.jpg': (b'\xff\xd8\xff',),
    '.jpeg': (b'\xff\xd8\xff',),
}

DEFAULT_ONBOARDING_DOCUMENT_TYPES = [
    {'code': 'AADHAAR_CARD', 'name': 'Aadhaar Card', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'requires_identifier': True, 'sort_order': 10},
    {'code': 'PAN_CARD', 'name': 'PAN Card', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'requires_identifier': True, 'sort_order': 20},
    {'code': 'PASSPORT', 'name': 'Passport', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'sort_order': 30},
    {'code': 'VOTER_ID', 'name': 'Voter ID', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'sort_order': 40},
    {'code': 'DRIVING_LICENCE', 'name': 'Driving Licence', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'sort_order': 50},
    {'code': 'WORK_PERMIT_OR_VISA', 'name': 'Work Permit / Visa / OCI', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'sort_order': 60},
    {'code': 'PASSPORT_PHOTO', 'name': 'Passport Photo', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'sort_order': 70},
    {'code': 'SIGNATURE_SPECIMEN', 'name': 'Signature Specimen', 'category': OnboardingDocumentCategory.IDENTITY_TAX, 'sort_order': 80},
    {'code': 'ADDRESS_PROOF', 'name': 'Address Proof', 'category': OnboardingDocumentCategory.ADDRESS, 'sort_order': 110},
    {'code': 'RENTAL_AGREEMENT', 'name': 'Rental Agreement', 'category': OnboardingDocumentCategory.ADDRESS, 'sort_order': 120},
    {'code': 'UTILITY_BILL', 'name': 'Utility Bill', 'category': OnboardingDocumentCategory.ADDRESS, 'sort_order': 130},
    {'code': 'CANCELLED_CHEQUE', 'name': 'Cancelled Cheque', 'category': OnboardingDocumentCategory.BANKING_PAYROLL, 'sort_order': 210},
    {'code': 'BANK_PASSBOOK', 'name': 'Bank Passbook / Statement', 'category': OnboardingDocumentCategory.BANKING_PAYROLL, 'sort_order': 220},
    {'code': 'UAN_PROOF', 'name': 'UAN / PF Proof', 'category': OnboardingDocumentCategory.STATUTORY_BENEFITS, 'sort_order': 310},
    {'code': 'ESIC_PROOF', 'name': 'ESIC Proof', 'category': OnboardingDocumentCategory.STATUTORY_BENEFITS, 'sort_order': 320},
    {'code': 'PRAN_NPS_PROOF', 'name': 'PRAN / NPS Proof', 'category': OnboardingDocumentCategory.STATUTORY_BENEFITS, 'sort_order': 330},
    {'code': 'TENTH_MARKSHEET', 'name': '10th Marksheet', 'category': OnboardingDocumentCategory.EDUCATION, 'sort_order': 410},
    {'code': 'TWELFTH_MARKSHEET', 'name': '12th Marksheet', 'category': OnboardingDocumentCategory.EDUCATION, 'sort_order': 420},
    {'code': 'DEGREE_CERTIFICATE', 'name': 'Degree / Provisional Certificate', 'category': OnboardingDocumentCategory.EDUCATION, 'sort_order': 430},
    {'code': 'ACADEMIC_TRANSCRIPT', 'name': 'Academic Transcript', 'category': OnboardingDocumentCategory.EDUCATION, 'sort_order': 440},
    {'code': 'PROFESSIONAL_CERTIFICATE', 'name': 'Professional Certificate / Licence', 'category': OnboardingDocumentCategory.EDUCATION, 'sort_order': 450},
    {'code': 'APPOINTMENT_LETTER', 'name': 'Previous Appointment / Offer Letter', 'category': OnboardingDocumentCategory.PREVIOUS_EMPLOYMENT, 'sort_order': 510},
    {'code': 'EXPERIENCE_LETTER', 'name': 'Experience Letter', 'category': OnboardingDocumentCategory.PREVIOUS_EMPLOYMENT, 'sort_order': 520},
    {'code': 'RELIEVING_LETTER', 'name': 'Relieving Letter', 'category': OnboardingDocumentCategory.PREVIOUS_EMPLOYMENT, 'sort_order': 530},
    {'code': 'SALARY_SLIPS', 'name': 'Recent Salary Slips', 'category': OnboardingDocumentCategory.PREVIOUS_EMPLOYMENT, 'sort_order': 540},
    {'code': 'FORM_16', 'name': 'Form 16', 'category': OnboardingDocumentCategory.PREVIOUS_EMPLOYMENT, 'sort_order': 550},
    {'code': 'BACKGROUND_CHECK_CONSENT', 'name': 'Background Check Consent', 'category': OnboardingDocumentCategory.POLICY_ACK, 'sort_order': 610},
    {'code': 'NDA_ACKNOWLEDGEMENT', 'name': 'NDA / Policy Acknowledgement', 'category': OnboardingDocumentCategory.POLICY_ACK, 'sort_order': 620},
    {'code': 'MEDICAL_FITNESS', 'name': 'Medical Fitness / Vaccination Record', 'category': OnboardingDocumentCategory.MEDICAL_SAFETY, 'sort_order': 710},
    {'code': 'BLOOD_GROUP_PROOF', 'name': 'Blood Group Proof', 'category': OnboardingDocumentCategory.MEDICAL_SAFETY, 'sort_order': 720},
    {'code': 'MARRIAGE_CERTIFICATE', 'name': 'Marriage Certificate', 'category': OnboardingDocumentCategory.FAMILY_NOMINEE, 'sort_order': 810},
    {'code': 'DEPENDENT_PROOF', 'name': 'Dependent / Nominee Proof', 'category': OnboardingDocumentCategory.FAMILY_NOMINEE, 'sort_order': 820},
    {'code': 'POLICE_VERIFICATION', 'name': 'Police Verification', 'category': OnboardingDocumentCategory.ROLE_COMPLIANCE, 'sort_order': 910},
    {'code': 'SAFETY_CERTIFICATE', 'name': 'Safety / Role Compliance Certificate', 'category': OnboardingDocumentCategory.ROLE_COMPLIANCE, 'sort_order': 920},
    {'code': 'ASSET_ACKNOWLEDGEMENT', 'name': 'Asset / Device Acknowledgement', 'category': OnboardingDocumentCategory.ROLE_COMPLIANCE, 'sort_order': 930},
]


def _validate_upload(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Only PDF, PNG, JPG, and JPEG files are allowed.')
    if file_obj.size > MAX_FILE_SIZE:
        raise ValueError('Files must be 5 MB or smaller.')
    header = file_obj.read(16)
    file_obj.seek(0)
    allowed_signatures = SIGNATURES_BY_EXTENSION.get(ext, ())
    if not header or not any(header.startswith(signature) for signature in allowed_signatures):
        raise ValueError('The uploaded file content does not match the selected file type.')


def ensure_default_document_types():
    for payload in DEFAULT_ONBOARDING_DOCUMENT_TYPES:
        OnboardingDocumentType.objects.update_or_create(
            code=payload['code'],
            defaults=payload,
        )


def list_onboarding_document_types(include_inactive=False):
    ensure_default_document_types()
    queryset = OnboardingDocumentType.objects.all()
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset.order_by('category', 'sort_order', 'name')


def get_document_types_by_ids(document_type_ids):
    ensure_default_document_types()
    if not document_type_ids:
        return []
    queryset = OnboardingDocumentType.objects.filter(id__in=document_type_ids, is_active=True)
    if queryset.count() != len(set(str(item) for item in document_type_ids)):
        raise ValueError('One or more requested document types are invalid.')
    return list(queryset.order_by('category', 'sort_order', 'name'))


def _build_key(employee, document_type_code, original_filename):
    ext = os.path.splitext(original_filename)[1].lower()
    safe_name = os.path.basename(original_filename).replace(' ', '-')
    employee_bucket = employee.employee_code or str(employee.id)
    return (
        f"organisations/{employee.organisation.slug}/employees/{employee_bucket}/"
        f"{document_type_code.lower()}/{uuid.uuid4().hex}-{safe_name}{'' if safe_name.endswith(ext) else ext}"
    )


def assign_document_requests(employee, document_type_ids, actor=None):
    document_types = get_document_types_by_ids(document_type_ids)
    created_requests = []
    with transaction.atomic():
        for document_type in document_types:
            request, _ = EmployeeDocumentRequest.objects.get_or_create(
                employee=employee,
                document_type_ref=document_type,
                defaults={
                    'requested_by': actor,
                    'is_required': True,
                    'status': EmployeeDocumentRequestStatus.REQUESTED,
                },
            )
            if request.requested_by_id is None and actor is not None:
                request.requested_by = actor
                request.save(update_fields=['requested_by', 'modified_at'])
            created_requests.append(request)
    return created_requests


def list_document_requests(employee):
    return employee.document_requests.select_related('document_type_ref', 'verified_by').prefetch_related('submissions__uploaded_by', 'submissions__reviewed_by')


def get_document_request(employee, request_id):
    return list_document_requests(employee).get(id=request_id)


def _upload_document_record(employee, file_obj, document_type_code, uploaded_by, metadata=None, document_request=None):
    _validate_upload(file_obj)
    file_bytes = file_obj.read()
    file_obj.seek(0)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    key = _build_key(employee, document_type_code, file_obj.name)
    upload_file(file_obj, key, getattr(file_obj, 'content_type', 'application/octet-stream'))
    version = 1
    if document_request is not None:
        version = document_request.submissions.count() + 1
    document = Document.objects.create(
        employee=employee,
        document_request=document_request,
        document_type=document_type_code,
        file_key=key,
        file_name=file_obj.name,
        file_size=file_obj.size,
        mime_type=getattr(file_obj, 'content_type', 'application/octet-stream'),
        uploaded_by=uploaded_by,
        metadata=metadata or {},
        file_hash=file_hash,
        version=version,
    )
    log_audit_event(
        uploaded_by,
        'document.uploaded',
        organisation=employee.organisation,
        target=document,
        payload={'document_type': document_type_code, 'request_id': str(document_request.id) if document_request else None},
    )
    return document


def upload_document_request(employee, document_request, file_obj, uploaded_by, metadata=None):
    with transaction.atomic():
        document = _upload_document_record(
            employee,
            file_obj,
            document_request.document_type_ref.code,
            uploaded_by=uploaded_by,
            metadata=metadata,
            document_request=document_request,
        )
        document_request.status = EmployeeDocumentRequestStatus.SUBMITTED
        document_request.rejection_note = ''
        document_request.latest_uploaded_at = timezone.now()
        document_request.verified_by = None
        document_request.verified_at = None
        document_request.save(
            update_fields=['status', 'rejection_note', 'latest_uploaded_at', 'verified_by', 'verified_at', 'modified_at']
        )
    return document


def upload_document(employee, file_obj, document_type, uploaded_by, metadata=None):
    document_type_obj = OnboardingDocumentType.objects.filter(code=document_type).first()
    request = None
    if document_type_obj:
        request, _ = EmployeeDocumentRequest.objects.get_or_create(
            employee=employee,
            document_type_ref=document_type_obj,
            defaults={
                'requested_by': uploaded_by,
                'status': EmployeeDocumentRequestStatus.REQUESTED,
            },
        )
        return upload_document_request(employee, request, file_obj, uploaded_by, metadata=metadata)
    return _upload_document_record(employee, file_obj, document_type, uploaded_by, metadata=metadata)


def generate_download_url(document, *, accessed_by=None, request=None, access_context='DIRECT', expiry=900):
    url = generate_presigned_url(document.file_key, expiry=expiry)
    if accessed_by is not None:
        log_audit_event(
            accessed_by,
            'document.download_url_generated',
            organisation=document.employee.organisation,
            target=document,
            payload={
                'document_type': document.document_type,
                'access_context': access_context,
                'expires_in_seconds': expiry,
            },
            request=request,
        )
    return url


def verify_document(document, reviewed_by):
    if document.status == DocumentStatus.VERIFIED:
        raise ValueError('Document is already verified.')
    with transaction.atomic():
        document.status = DocumentStatus.VERIFIED
        document.reviewed_by = reviewed_by
        document.reviewed_at = timezone.now()
        document.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'modified_at'])
        if document.document_request_id:
            document.document_request.status = EmployeeDocumentRequestStatus.VERIFIED
            document.document_request.verified_by = reviewed_by
            document.document_request.verified_at = timezone.now()
            document.document_request.rejection_note = ''
            document.document_request.save(
                update_fields=['status', 'verified_by', 'verified_at', 'rejection_note', 'modified_at']
            )
    log_audit_event(reviewed_by, 'document.verified', organisation=document.employee.organisation, target=document)
    return document


def reject_document(document, reviewed_by, note=''):
    with transaction.atomic():
        document.status = DocumentStatus.REJECTED
        document.reviewed_by = reviewed_by
        document.reviewed_at = timezone.now()
        metadata = document.metadata or {}
        metadata['rejection_note'] = note
        document.metadata = metadata
        document.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'metadata', 'modified_at'])
        if document.document_request_id:
            document.document_request.status = EmployeeDocumentRequestStatus.REJECTED
            document.document_request.rejection_note = note
            document.document_request.verified_by = None
            document.document_request.verified_at = None
            document.document_request.save(
                update_fields=['status', 'rejection_note', 'verified_by', 'verified_at', 'modified_at']
            )
    log_audit_event(
        reviewed_by,
        'document.rejected',
        organisation=document.employee.organisation,
        target=document,
        payload={'note': note},
    )
    return document
