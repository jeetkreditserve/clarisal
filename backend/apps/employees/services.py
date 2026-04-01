import re
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountType, User
from apps.accounts.workspaces import sync_user_role
from apps.approvals.services import ensure_default_workflow_configured
from apps.audit.services import log_audit_event
from apps.common.security import encrypt_value, mask_value
from apps.departments.models import Department
from apps.documents.models import EmployeeDocumentRequestStatus
from apps.documents.services import assign_document_requests
from apps.invitations.models import InvitationRole, InvitationStatus
from apps.invitations.services import create_employee_invitation
from apps.locations.models import OfficeLocation
from apps.organisations.services import get_org_licence_summary, mark_employee_invited

from .models import (
    BloodTypeChoice,
    EducationRecord,
    Employee,
    EmployeeBankAccount,
    EmployeeEmergencyContact,
    EmployeeFamilyMember,
    EmployeeGovernmentId,
    EmployeeOnboardingStatus,
    EmployeeProfile,
    EmployeeStatus,
    FamilyRelationChoice,
    GovernmentIdType,
)

PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
AADHAAR_PATTERN = re.compile(r'^[0-9]{12}$')
IFSC_PATTERN = re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$')
LICENCE_CONSUMING_STATUSES = [
    EmployeeStatus.INVITED,
    EmployeeStatus.PENDING,
    EmployeeStatus.ACTIVE,
]
TERMINAL_EMPLOYEE_STATUSES = [
    EmployeeStatus.RESIGNED,
    EmployeeStatus.RETIRED,
    EmployeeStatus.TERMINATED,
]
ONBOARDING_COMPLETE_DOCUMENT_STATUSES = [
    EmployeeDocumentRequestStatus.SUBMITTED,
    EmployeeDocumentRequestStatus.VERIFIED,
    EmployeeDocumentRequestStatus.WAIVED,
]


def _get_department(organisation, department_id):
    if not department_id:
        return None
    return Department.objects.get(organisation=organisation, id=department_id, is_active=True)


def _get_location(organisation, location_id):
    if not location_id:
        return None
    return OfficeLocation.objects.get(organisation=organisation, id=location_id, is_active=True)


def _get_reporting_employee(organisation, reporting_to_employee_id):
    if not reporting_to_employee_id:
        return None
    return Employee.objects.select_related('user').get(organisation=organisation, id=reporting_to_employee_id)


def _next_employee_code(organisation):
    existing_codes = set(
        Employee.all_objects.filter(organisation=organisation)
        .exclude(employee_code__isnull=True)
        .exclude(employee_code='')
        .values_list('employee_code', flat=True)
    )
    counter = 1
    while True:
        code = f'EMP{counter:03d}'
        if code not in existing_codes:
            return code
        counter += 1


def get_next_employee_code(organisation):
    return _next_employee_code(organisation)


def _basic_onboarding_complete(employee):
    profile = getattr(employee, 'profile', None)
    if not profile:
        return False

    government_ids = {item.id_type for item in employee.government_ids.all()}
    has_address = bool(
        profile.address_line1
        and profile.city
        and profile.state
        and profile.country
        and profile.pincode
    )
    has_identity = {GovernmentIdType.PAN, GovernmentIdType.AADHAAR}.issubset(government_ids)
    has_personal_details = bool(
        profile.date_of_birth
        and profile.phone_personal
        and profile.gender
        and profile.blood_type
    )
    has_family_details = employee.family_members.exists()
    has_emergency_contact = employee.emergency_contacts.exists()

    return all([has_address, has_identity, has_personal_details, has_family_details, has_emergency_contact])


def _required_documents_complete(employee):
    required_requests = employee.document_requests.filter(is_required=True)
    if not required_requests.exists():
        return True
    return not required_requests.exclude(status__in=ONBOARDING_COMPLETE_DOCUMENT_STATUSES).exists()


def get_profile_completion(employee):
    completed_sections = []
    missing_sections = []
    profile = getattr(employee, 'profile', None)

    def check(section, condition):
        if condition:
            completed_sections.append(section)
        else:
            missing_sections.append(section)

    check(
        'personal_details',
        bool(profile and profile.date_of_birth and profile.phone_personal and profile.address_line1 and profile.city and profile.blood_type),
    )
    check('education', employee.education_records.exists())
    government_ids = {item.id_type for item in employee.government_ids.all()}
    check('government_ids', {GovernmentIdType.PAN, GovernmentIdType.AADHAAR}.issubset(government_ids))
    check('bank_account', employee.bank_accounts.filter(is_primary=True).exists())
    check('family_details', employee.family_members.exists())
    check('emergency_contacts', employee.emergency_contacts.exists())
    check(
        'documents',
        not employee.document_requests.filter(is_required=True).exclude(status__in=ONBOARDING_COMPLETE_DOCUMENT_STATUSES).exists(),
    )

    total_sections = len(completed_sections) + len(missing_sections)
    percent = int((len(completed_sections) / total_sections) * 100) if total_sections else 0
    return {
        'percent': percent,
        'completed_sections': completed_sections,
        'missing_sections': missing_sections,
    }


def compute_onboarding_status(employee):
    if employee.status == EmployeeStatus.ACTIVE or employee.status in TERMINAL_EMPLOYEE_STATUSES:
        return EmployeeOnboardingStatus.COMPLETE
    if not _basic_onboarding_complete(employee):
        return EmployeeOnboardingStatus.BASIC_DETAILS_PENDING
    if not _required_documents_complete(employee):
        return EmployeeOnboardingStatus.DOCUMENTS_PENDING
    return EmployeeOnboardingStatus.COMPLETE


def refresh_employee_onboarding_status(employee, actor=None):
    new_status = compute_onboarding_status(employee)
    update_fields = []
    if employee.onboarding_status != new_status:
        employee.onboarding_status = new_status
        update_fields.append('onboarding_status')
    if new_status == EmployeeOnboardingStatus.COMPLETE and employee.onboarding_completed_at is None:
        employee.onboarding_completed_at = timezone.now()
        update_fields.append('onboarding_completed_at')
    if employee.status == EmployeeStatus.INVITED and new_status == EmployeeOnboardingStatus.COMPLETE:
        employee.status = EmployeeStatus.PENDING
        update_fields.append('status')
    if update_fields:
        update_fields.extend(['updated_at'])
        employee.save(update_fields=update_fields)
        log_audit_event(
            actor,
            'employee.onboarding.status_updated',
            organisation=employee.organisation,
            target=employee,
            payload={'onboarding_status': employee.onboarding_status, 'employee_status': employee.status},
        )
    return employee


def get_onboarding_summary(employee):
    refresh_employee_onboarding_status(employee)
    return {
        'employee_id': str(employee.id),
        'employee_status': employee.status,
        'onboarding_status': employee.onboarding_status,
        'profile_completion': get_profile_completion(employee),
        'required_document_count': employee.document_requests.filter(is_required=True).count(),
        'submitted_document_count': employee.document_requests.filter(
            is_required=True,
            status__in=ONBOARDING_COMPLETE_DOCUMENT_STATUSES,
        ).count(),
    }


def invite_employee(
    organisation,
    company_email,
    first_name,
    last_name,
    designation='',
    employment_type='FULL_TIME',
    date_of_joining=None,
    department_id=None,
    office_location_id=None,
    required_document_type_ids=None,
    invited_by=None,
):
    ensure_default_workflow_configured(organisation)
    licence_summary = get_org_licence_summary(organisation)
    if licence_summary['available'] <= 0:
        raise ValueError('No licences are available for this organisation.')

    department = _get_department(organisation, department_id)
    office_location = _get_location(organisation, office_location_id)

    with transaction.atomic():
        user, _ = User.objects.get_or_create(
            email=company_email,
            account_type=AccountType.WORKFORCE,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': 'EMPLOYEE',
                'is_active': False,
            },
        )
        user.first_name = first_name
        user.last_name = last_name
        if not user.is_active:
            user.is_active = False
        user.save(update_fields=['first_name', 'last_name', 'is_active', 'updated_at'])

        employee = Employee.objects.filter(user=user, organisation=organisation).first()
        if employee and employee.status not in [EmployeeStatus.INVITED, EmployeeStatus.PENDING]:
            raise ValueError('This user already exists in the organisation and cannot be reinvited.')
        if employee is None:
            employee = Employee.objects.create(
                user=user,
                organisation=organisation,
                designation=designation,
                employment_type=employment_type,
                date_of_joining=date_of_joining,
                department=department,
                office_location=office_location,
                status=EmployeeStatus.INVITED,
                onboarding_status=EmployeeOnboardingStatus.NOT_STARTED,
            )
        employee.designation = designation
        employee.employment_type = employment_type
        employee.date_of_joining = date_of_joining
        employee.department = department
        employee.office_location = office_location
        employee.status = EmployeeStatus.INVITED
        employee.onboarding_status = EmployeeOnboardingStatus.NOT_STARTED
        employee.save()

        EmployeeProfile.objects.get_or_create(employee=employee)
        assign_document_requests(employee, required_document_type_ids or [], actor=invited_by)
        invitation = create_employee_invitation(organisation, user, invited_by)
        mark_employee_invited(organisation, invited_by, employee)
        sync_user_role(user)
        log_audit_event(
            invited_by,
            'employee.invited',
            organisation=organisation,
            target=employee,
            payload={
                'email': company_email,
                'status': employee.status,
                'required_document_count': len(required_document_type_ids or []),
            },
        )
        return employee, invitation


def update_employee(employee, actor=None, **fields):
    department_id = fields.pop('department_id', None) if 'department_id' in fields else None
    office_location_id = fields.pop('office_location_id', None) if 'office_location_id' in fields else None
    if department_id is not None:
        employee.department = _get_department(employee.organisation, department_id)
    if office_location_id is not None:
        employee.office_location = _get_location(employee.organisation, office_location_id)
    if 'employee_code' in fields:
        fields['employee_code'] = (fields['employee_code'] or '').strip().upper() or None
    for attr, value in fields.items():
        setattr(employee, attr, value)
    employee.save()
    log_audit_event(actor, 'employee.updated', organisation=employee.organisation, target=employee, payload=fields)
    return employee


def mark_employee_joined(employee, employee_code, date_of_joining, designation, reporting_to_employee_id, actor=None):
    if employee.status != EmployeeStatus.PENDING:
        raise ValueError('Only pending employees can be marked as joined.')

    normalized_code = (employee_code or '').strip().upper()
    if not normalized_code:
        raise ValueError('Employee code is required when marking an employee as joined.')
    if not date_of_joining:
        raise ValueError('Date of joining is required when marking an employee as joined.')
    if not (designation or '').strip():
        raise ValueError('Designation is required when marking an employee as joined.')
    if not reporting_to_employee_id:
        raise ValueError('Reporting manager is required when marking an employee as joined.')
    reporting_to = _get_reporting_employee(employee.organisation, reporting_to_employee_id)
    if Employee.all_objects.filter(
        organisation=employee.organisation,
        employee_code=normalized_code,
    ).exclude(id=employee.id).exists():
        raise ValueError('Employee code already exists in this organisation.')

    employee.employee_code = normalized_code
    employee.date_of_joining = date_of_joining
    employee.designation = designation.strip()
    employee.reporting_to = reporting_to
    employee.status = EmployeeStatus.ACTIVE
    employee.onboarding_status = EmployeeOnboardingStatus.COMPLETE
    if employee.onboarding_completed_at is None:
        employee.onboarding_completed_at = timezone.now()
    employee.save(
        update_fields=[
            'employee_code',
            'date_of_joining',
            'designation',
            'reporting_to',
            'status',
            'onboarding_status',
            'onboarding_completed_at',
            'updated_at',
        ]
    )
    log_audit_event(
        actor,
        'employee.joined',
        organisation=employee.organisation,
        target=employee,
        payload={
            'employee_code': normalized_code,
            'date_of_joining': date_of_joining.isoformat(),
            'designation': employee.designation,
            'reporting_to_employee_id': str(reporting_to.id),
        },
    )
    return employee


def end_employment(employee, end_status, date_of_exit, actor=None):
    if employee.status != EmployeeStatus.ACTIVE:
        raise ValueError('Only active employees can end employment.')
    if end_status not in TERMINAL_EMPLOYEE_STATUSES:
        raise ValueError('End employment status must be resigned, retired, or terminated.')
    if not date_of_exit:
        raise ValueError('Date of exit is required.')

    employee.status = end_status
    employee.date_of_exit = date_of_exit
    employee.save(update_fields=['status', 'date_of_exit', 'updated_at'])
    log_audit_event(
        actor,
        'employee.employment_ended',
        organisation=employee.organisation,
        target=employee,
        payload={'status': end_status, 'date_of_exit': date_of_exit.isoformat()},
    )
    return employee


def delete_employee(employee, actor=None):
    if employee.status not in [EmployeeStatus.INVITED, EmployeeStatus.PENDING]:
        raise ValueError('Only invited or pending employees can be deleted.')

    organisation = employee.organisation
    user = employee.user
    payload = {
        'user_email': user.email,
        'status': employee.status,
        'employee_id': str(employee.id),
    }

    from apps.invitations.models import Invitation

    with transaction.atomic():
        Invitation.objects.filter(
            organisation=organisation,
            user=user,
            role=InvitationRole.EMPLOYEE,
            status=InvitationStatus.PENDING,
        ).update(status=InvitationStatus.REVOKED, revoked_at=timezone.now())
        now = timezone.now()
        employee.education_records.update(is_deleted=True, deleted_at=now)
        employee.bank_accounts.update(is_deleted=True, deleted_at=now)
        employee.emergency_contacts.update(is_deleted=True, deleted_at=now)
        employee.family_members.update(is_deleted=True, deleted_at=now)
        employee.is_deleted = True
        employee.deleted_at = now
        employee.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        sync_user_role(user)

    log_audit_event(actor, 'employee.deleted', organisation=organisation, target=employee, payload=payload)


def update_employee_profile(employee, actor=None, **fields):
    profile, _ = EmployeeProfile.objects.get_or_create(employee=employee)
    for attr, value in fields.items():
        setattr(profile, attr, value)
    profile.save()
    log_audit_event(actor, 'employee.profile.updated', organisation=employee.organisation, target=employee, payload=fields)
    return profile


def update_onboarding_basics(employee, actor=None, profile_fields=None, pan_identifier='', aadhaar_identifier=''):
    profile = update_employee_profile(employee, actor=actor, **(profile_fields or {}))
    if pan_identifier:
        upsert_government_id(employee, GovernmentIdType.PAN, pan_identifier, actor=actor)
    if aadhaar_identifier:
        upsert_government_id(employee, GovernmentIdType.AADHAAR, aadhaar_identifier, actor=actor)
    refresh_employee_onboarding_status(employee, actor=actor)
    return profile


def create_or_update_emergency_contact(employee, actor=None, contact_id=None, **fields):
    if fields.get('is_primary'):
        employee.emergency_contacts.update(is_primary=False)
    if contact_id:
        contact = employee.emergency_contacts.get(id=contact_id)
        for attr, value in fields.items():
            setattr(contact, attr, value)
        contact.save()
        event = 'employee.emergency_contact.updated'
    else:
        contact = EmployeeEmergencyContact.objects.create(employee=employee, **fields)
        event = 'employee.emergency_contact.created'
    profile, _ = EmployeeProfile.objects.get_or_create(employee=employee)
    if contact.is_primary:
        profile.phone_emergency = contact.phone_number
        profile.emergency_contact_name = contact.full_name
        profile.emergency_contact_relation = contact.relation
        profile.save(update_fields=['phone_emergency', 'emergency_contact_name', 'emergency_contact_relation', 'updated_at'])
    refresh_employee_onboarding_status(employee, actor=actor)
    log_audit_event(actor, event, organisation=employee.organisation, target=contact)
    return contact


def delete_emergency_contact(contact, actor=None):
    organisation = contact.employee.organisation
    payload = {'contact_id': str(contact.id), 'full_name': contact.full_name}
    contact.is_deleted = True
    contact.deleted_at = timezone.now()
    contact.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    refresh_employee_onboarding_status(contact.employee, actor=actor)
    log_audit_event(actor, 'employee.emergency_contact.deleted', organisation=organisation, payload=payload)


def create_or_update_family_member(employee, actor=None, member_id=None, **fields):
    if member_id:
        member = employee.family_members.get(id=member_id)
        for attr, value in fields.items():
            setattr(member, attr, value)
        member.save()
        event = 'employee.family_member.updated'
    else:
        member = EmployeeFamilyMember.objects.create(employee=employee, **fields)
        event = 'employee.family_member.created'
    refresh_employee_onboarding_status(employee, actor=actor)
    log_audit_event(actor, event, organisation=employee.organisation, target=member)
    return member


def delete_family_member(member, actor=None):
    organisation = member.employee.organisation
    employee = member.employee
    payload = {'member_id': str(member.id), 'full_name': member.full_name}
    member.is_deleted = True
    member.deleted_at = timezone.now()
    member.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    refresh_employee_onboarding_status(employee, actor=actor)
    log_audit_event(actor, 'employee.family_member.deleted', organisation=organisation, payload=payload)


def create_education_record(employee, actor=None, **fields):
    record = EducationRecord.objects.create(employee=employee, **fields)
    log_audit_event(actor, 'employee.education.created', organisation=employee.organisation, target=record, payload=fields)
    return record


def update_education_record(record, actor=None, **fields):
    for attr, value in fields.items():
        setattr(record, attr, value)
    record.save()
    log_audit_event(actor, 'employee.education.updated', organisation=record.employee.organisation, target=record, payload=fields)
    return record


def delete_education_record(record, actor=None):
    organisation = record.employee.organisation
    payload = {'degree': record.degree, 'institution': record.institution}
    record.is_deleted = True
    record.deleted_at = timezone.now()
    record.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    log_audit_event(actor, 'employee.education.deleted', organisation=organisation, payload=payload)


def upsert_government_id(employee, id_type, identifier, actor=None, name_on_id='', metadata=None):
    normalized = identifier.replace(' ', '').upper()
    if id_type == GovernmentIdType.PAN and not PAN_PATTERN.match(normalized):
        raise ValueError('PAN must be in the format AAAAA9999A.')
    if id_type == GovernmentIdType.AADHAAR and not AADHAAR_PATTERN.match(normalized):
        raise ValueError('Aadhaar must be a 12-digit number.')

    record, _ = EmployeeGovernmentId.objects.get_or_create(employee=employee, id_type=id_type)
    record.identifier_encrypted = encrypt_value(normalized)
    record.masked_identifier = mask_value(normalized)
    record.name_on_id = name_on_id
    record.metadata = metadata or {}
    record.save()
    refresh_employee_onboarding_status(employee, actor=actor)
    log_audit_event(actor, 'employee.government_id.upserted', organisation=employee.organisation, target=record, payload={'id_type': id_type})
    return record


def create_bank_account(employee, actor=None, **fields):
    account_number = fields.pop('account_number').replace(' ', '')
    ifsc = fields.pop('ifsc').replace(' ', '').upper()
    if not IFSC_PATTERN.match(ifsc):
        raise ValueError('IFSC must be in the format AAAA0XXXXXX.')
    if fields.get('is_primary'):
        employee.bank_accounts.update(is_primary=False)
    account = EmployeeBankAccount.objects.create(
        employee=employee,
        account_number_encrypted=encrypt_value(account_number),
        masked_account_number=mask_value(account_number),
        ifsc_encrypted=encrypt_value(ifsc),
        masked_ifsc=mask_value(ifsc),
        **fields,
    )
    log_audit_event(actor, 'employee.bank_account.created', organisation=employee.organisation, target=account)
    return account


def update_bank_account(account, actor=None, **fields):
    if 'account_number' in fields:
        account_number = fields.pop('account_number').replace(' ', '')
        account.account_number_encrypted = encrypt_value(account_number)
        account.masked_account_number = mask_value(account_number)
    if 'ifsc' in fields:
        ifsc = fields.pop('ifsc').replace(' ', '').upper()
        if not IFSC_PATTERN.match(ifsc):
            raise ValueError('IFSC must be in the format AAAA0XXXXXX.')
        account.ifsc_encrypted = encrypt_value(ifsc)
        account.masked_ifsc = mask_value(ifsc)
    if fields.get('is_primary'):
        account.employee.bank_accounts.exclude(id=account.id).update(is_primary=False)
    for attr, value in fields.items():
        setattr(account, attr, value)
    account.save()
    log_audit_event(actor, 'employee.bank_account.updated', organisation=account.employee.organisation, target=account)
    return account


def delete_bank_account(account, actor=None):
    organisation = account.employee.organisation
    payload = {'account_id': str(account.id), 'account_holder_name': account.account_holder_name}
    account.is_deleted = True
    account.deleted_at = timezone.now()
    account.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    log_audit_event(actor, 'employee.bank_account.deleted', organisation=organisation, payload=payload)


def get_employee_dashboard(employee, calendar_month=None):
    refresh_employee_onboarding_status(employee)
    completion = get_profile_completion(employee)
    pending_document_requests = employee.document_requests.filter(
        status__in=[
            EmployeeDocumentRequestStatus.REQUESTED,
            EmployeeDocumentRequestStatus.REJECTED,
        ]
    )

    approvals_summary = {'count': 0, 'items': []}
    notices = []
    events = []
    leave_balances = []
    calendar = {'month': None, 'days': []}
    try:
        from apps.approvals.services import get_pending_approval_actions_for_user
        from apps.communications.services import get_employee_events, get_visible_notices
        from apps.timeoff.services import get_employee_calendar_month, get_employee_leave_balances

        approvals = get_pending_approval_actions_for_user(employee.user, organisation=employee.organisation)
        approvals_summary = {
            'count': approvals.count(),
            'items': [
                {
                    'action_id': str(action.id),
                    'label': action.approval_run.subject_label,
                    'request_kind': action.approval_run.request_kind,
                    'stage_name': action.stage.name,
                }
                for action in approvals[:5]
            ],
        }
        notices = get_visible_notices(employee)[:5]
        events = get_employee_events(employee)[:8]
        leave_balances = get_employee_leave_balances(employee)
        calendar = get_employee_calendar_month(employee, calendar_month=calendar_month)
    except Exception:  # noqa: BLE001
        pass

    serialized_notices = [
        {
            'id': str(notice.id),
            'title': notice.title,
            'body': notice.body,
            'status': notice.status,
            'published_at': notice.published_at.isoformat() if notice.published_at else None,
        }
        for notice in notices
    ]

    documents = employee.documents.all()
    return {
        'profile_completion': completion,
        'pending_documents': documents.filter(status='PENDING').count(),
        'verified_documents': documents.filter(status='VERIFIED').count(),
        'rejected_documents': documents.filter(status='REJECTED').count(),
        'pending_document_requests': pending_document_requests.count(),
        'employee_code': employee.employee_code,
        'onboarding_status': employee.onboarding_status,
        'approvals': approvals_summary,
        'notices': serialized_notices,
        'events': events,
        'leave_balances': leave_balances,
        'calendar': calendar,
    }
