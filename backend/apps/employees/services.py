import re
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountType, User
from apps.accounts.workspaces import sync_user_role
from apps.audit.services import log_audit_event
from apps.common.security import encrypt_value, mask_value
from apps.departments.models import Department
from apps.invitations.models import InvitationRole, InvitationStatus
from apps.invitations.services import create_employee_invitation
from apps.locations.models import OfficeLocation
from apps.organisations.services import get_org_licence_summary, mark_employee_invited

from .models import (
    EducationRecord,
    Employee,
    EmployeeBankAccount,
    EmployeeGovernmentId,
    EmployeeProfile,
    EmployeeStatus,
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


def _get_department(organisation, department_id):
    if not department_id:
        return None
    return Department.objects.get(organisation=organisation, id=department_id, is_active=True)


def _get_location(organisation, location_id):
    if not location_id:
        return None
    return OfficeLocation.objects.get(organisation=organisation, id=location_id, is_active=True)


def _next_employee_code(organisation):
    existing_codes = set(
        Employee.objects.filter(organisation=organisation).exclude(employee_code__isnull=True).exclude(employee_code='').values_list('employee_code', flat=True)
    )
    counter = 1
    while True:
        code = f'EMP{counter:03d}'
        if code not in existing_codes:
            return code
        counter += 1


def get_next_employee_code(organisation):
    return _next_employee_code(organisation)


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
        bool(profile and profile.date_of_birth and profile.phone_personal and profile.address_line1 and profile.city),
    )
    check('education', employee.education_records.exists())
    government_ids = {item.id_type for item in employee.government_ids.all()}
    check('government_ids', {'PAN', 'AADHAAR'}.issubset(government_ids))
    check('bank_account', employee.bank_accounts.filter(is_primary=True).exists())
    check('documents', employee.documents.exists())

    total_sections = len(completed_sections) + len(missing_sections)
    percent = int((len(completed_sections) / total_sections) * 100) if total_sections else 0
    return {
        'percent': percent,
        'completed_sections': completed_sections,
        'missing_sections': missing_sections,
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
    invited_by=None,
):
    licence_summary = get_org_licence_summary(organisation)
    if licence_summary['available'] <= 0:
        raise ValueError('No licences are available for this organisation.')

    department = _get_department(organisation, department_id)
    office_location = _get_location(organisation, office_location_id)

    with transaction.atomic():
        user, created = User.objects.get_or_create(
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
            )
        employee.designation = designation
        employee.employment_type = employment_type
        employee.date_of_joining = date_of_joining
        employee.department = department
        employee.office_location = office_location
        employee.status = EmployeeStatus.INVITED
        employee.save()

        EmployeeProfile.objects.get_or_create(employee=employee)
        invitation = create_employee_invitation(organisation, user, invited_by)
        mark_employee_invited(organisation, invited_by, employee)
        sync_user_role(user)
        log_audit_event(
            invited_by,
            'employee.invited',
            organisation=organisation,
            target=employee,
            payload={'email': company_email, 'status': employee.status},
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


def mark_employee_joined(employee, employee_code, date_of_joining, actor=None):
    if employee.status != EmployeeStatus.PENDING:
        raise ValueError('Only pending employees can be marked as joined.')

    normalized_code = (employee_code or '').strip().upper()
    if not normalized_code:
        raise ValueError('Employee code is required when marking an employee as joined.')
    if not date_of_joining:
        raise ValueError('Date of joining is required when marking an employee as joined.')
    if Employee.objects.filter(
        organisation=employee.organisation,
        employee_code=normalized_code,
    ).exclude(id=employee.id).exists():
        raise ValueError('Employee code already exists in this organisation.')

    employee.employee_code = normalized_code
    employee.date_of_joining = date_of_joining
    employee.status = EmployeeStatus.ACTIVE
    employee.save(update_fields=['employee_code', 'date_of_joining', 'status', 'updated_at'])
    log_audit_event(
        actor,
        'employee.joined',
        organisation=employee.organisation,
        target=employee,
        payload={'employee_code': normalized_code, 'date_of_joining': date_of_joining.isoformat()},
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
        employee.delete()
        sync_user_role(user)

    log_audit_event(actor, 'employee.deleted', organisation=organisation, payload=payload)


def update_employee_profile(employee, actor=None, **fields):
    profile, _ = EmployeeProfile.objects.get_or_create(employee=employee)
    for attr, value in fields.items():
        setattr(profile, attr, value)
    profile.save()
    log_audit_event(actor, 'employee.profile.updated', organisation=employee.organisation, target=employee, payload=fields)
    return profile


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
    record.delete()
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
    account.delete()
    log_audit_event(actor, 'employee.bank_account.deleted', organisation=organisation)


def get_employee_dashboard(employee):
    completion = get_profile_completion(employee)
    documents = employee.documents.all()
    return {
        'profile_completion': completion,
        'pending_documents': documents.filter(status='PENDING').count(),
        'verified_documents': documents.filter(status='VERIFIED').count(),
        'rejected_documents': documents.filter(status='REJECTED').count(),
        'employee_code': employee.employee_code,
    }
