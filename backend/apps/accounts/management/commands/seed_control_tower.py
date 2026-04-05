import os
from datetime import date, timedelta

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import AccountType, User, UserRole
from apps.accounts.workspaces import sync_user_role
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalFallbackType,
    ApprovalRequestKind,
    ApprovalRun,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalStageMode,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.approvals.services import approve_action, reject_action
from apps.common.security import hash_token
from apps.communications.models import Notice, NoticeAudienceType, NoticeStatus
from apps.communications.services import create_notice, publish_notice, update_notice
from apps.departments.models import Department
from apps.documents.models import (
    Document,
    DocumentStatus,
    EmployeeDocumentRequest,
    EmployeeDocumentRequestStatus,
    OnboardingDocumentType,
)
from apps.documents.services import assign_document_requests, ensure_default_document_types
from apps.employees.models import (
    EducationRecord,
    Employee,
    EmployeeEmergencyContact,
    EmployeeFamilyMember,
    EmployeeOnboardingStatus,
    EmployeeProfile,
    EmployeeStatus,
    EmploymentType,
    FamilyRelationChoice,
    GovernmentIdType,
)
from apps.employees.services import (
    create_bank_account,
    refresh_employee_onboarding_status,
    update_bank_account,
    update_education_record,
    upsert_government_id,
)
from apps.invitations.models import Invitation, InvitationRole, InvitationStatus
from apps.locations.models import OfficeLocation
from apps.locations.services import create_location, update_location
from apps.organisations.models import (
    LicenceBatchPaymentStatus,
    Organisation,
    OrganisationAddressType,
    OrganisationEntityType,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import (
    create_licence_batch,
    create_organisation,
    create_organisation_address,
    ensure_org_admin_membership,
    mark_bootstrap_admin_accepted,
    mark_employee_invited,
    mark_licence_batch_paid,
    mark_master_data_configured,
    set_primary_admin,
    transition_organisation_state,
    update_licence_count,
    update_organisation_address,
    update_organisation_profile,
    upsert_bootstrap_admin,
)
from apps.timeoff.models import (
    CarryForwardMode,
    DaySession,
    HolidayCalendar,
    HolidayCalendarStatus,
    HolidayClassification,
    LeaveCycle,
    LeaveCycleType,
    LeavePlan,
    LeavePlanEmployeeAssignment,
    LeaveRequest,
    OnDutyDurationType,
    OnDutyPolicy,
    OnDutyRequest,
)
from apps.timeoff.services import (
    create_holiday_calendar,
    create_leave_plan,
    create_leave_request,
    create_on_duty_request,
    publish_holiday_calendar,
    update_holiday_calendar,
    update_leave_plan,
    upsert_leave_cycle,
    upsert_on_duty_policy,
    withdraw_leave_request,
    withdraw_on_duty_request,
)

DEFAULT_ORGANISATION = {
    'name': 'Acme Workforce Pvt Ltd',
    'licence_count': 10,
    'pan_number': 'AACCA1234F',
    'email': 'hello@acmeworkforce.com',
    'phone': '+91 9876543210',
    'country_code': 'IN',
    'currency': 'INR',
    'entity_type': OrganisationEntityType.PRIVATE_LIMITED,
    'addresses': [
        {
            'address_type': OrganisationAddressType.REGISTERED,
            'line1': '42 Residency Road',
            'line2': '',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'country': 'India',
            'pincode': '560025',
            'gstin': '29AACCA1234F1Z5',
        },
        {
            'address_type': OrganisationAddressType.BILLING,
            'line1': '18 Nariman Point',
            'line2': '',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'country': 'India',
            'pincode': '400021',
            'gstin': '27AACCA1234F1Z7',
        },
        {
            'address_type': OrganisationAddressType.HEADQUARTERS,
            'label': 'Bengaluru HQ',
            'line1': '7th Floor, Embassy Tech Village',
            'line2': 'Outer Ring Road',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'country': 'India',
            'pincode': '560103',
            'gstin': '29AACCA1234F2Z4',
        },
        {
            'address_type': OrganisationAddressType.WAREHOUSE,
            'label': 'East Fulfilment Hub',
            'line1': '14 Logistics Park',
            'line2': 'Old Madras Road',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'country': 'India',
            'pincode': '560049',
            'gstin': '',
        },
        {
            'address_type': OrganisationAddressType.CUSTOM,
            'label': 'Pune Satellite Office',
            'line1': '3 Senapati Bapat Road',
            'line2': 'Shivajinagar',
            'city': 'Pune',
            'state': 'Maharashtra',
            'country': 'India',
            'pincode': '411016',
            'gstin': '',
        },
    ],
}

DEFAULT_ORG_ADMIN = {
    'email': 'admin@acmeworkforce.com',
    'first_name': 'Aditi',
    'last_name': 'Rao',
}
PRIMARY_CONSUMING_EMPLOYEE_COUNT = 7

SECONDARY_ORGANISATIONS = [
    {
        'name': 'Orbit Freight Pvt Ltd',
        'slug': 'orbit-freight-pvt-ltd',
        'pan_number': 'AAACO1234K',
        'email': 'ops@orbitfreight.com',
        'phone': '+91 9311111111',
        'country_code': 'IN',
        'currency': 'INR',
        'entity_type': OrganisationEntityType.PRIVATE_LIMITED,
        'licence_count': 12,
        'state_kind': 'PENDING_PAYMENT',
        'addresses': [
            {
                'address_type': OrganisationAddressType.REGISTERED,
                'line1': '11 Port Road',
                'line2': 'Whitefield',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'country': 'India',
                'pincode': '560066',
                'gstin': '29AAACO1234K1Z9',
            },
            {
                'address_type': OrganisationAddressType.BILLING,
                'line1': '90 Maker Chambers',
                'line2': 'Cuffe Parade',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '400005',
                'gstin': '27AAACO1234K1Z1',
            },
        ],
    },
    {
        'name': 'Redwood Retail Pvt Ltd',
        'slug': 'redwood-retail-pvt-ltd',
        'pan_number': 'AACCR1234L',
        'email': 'hello@redwoodretail.com',
        'phone': '+91 9322222222',
        'country_code': 'IN',
        'currency': 'INR',
        'entity_type': OrganisationEntityType.PRIVATE_LIMITED,
        'licence_count': 8,
        'state_kind': 'SUSPENDED',
        'addresses': [
            {
                'address_type': OrganisationAddressType.REGISTERED,
                'line1': '202 Residency Towers',
                'line2': 'MG Road',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'country': 'India',
                'pincode': '560001',
                'gstin': '29AACCR1234L1Z6',
            },
            {
                'address_type': OrganisationAddressType.BILLING,
                'line1': '44 BKC',
                'line2': 'Bandra East',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '400051',
                'gstin': '27AACCR1234L1Z8',
            },
        ],
    },
    {
        'name': 'Zenith Field Services Pvt Ltd',
        'slug': 'zenith-field-services-pvt-ltd',
        'pan_number': 'AACCF1234M',
        'email': 'contact@zenithfield.com',
        'phone': '+91 9333333333',
        'country_code': 'IN',
        'currency': 'INR',
        'entity_type': OrganisationEntityType.PRIVATE_LIMITED,
        'licence_count': 6,
        'state_kind': 'LICENCE_EXPIRED',
        'addresses': [
            {
                'address_type': OrganisationAddressType.REGISTERED,
                'line1': '88 Infantry Road',
                'line2': '',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'country': 'India',
                'pincode': '560001',
                'gstin': '29AACCF1234M1Z3',
            },
            {
                'address_type': OrganisationAddressType.BILLING,
                'line1': '22 Corporate Park',
                'line2': 'Viman Nagar',
                'city': 'Pune',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '411014',
                'gstin': '27AACCF1234M1Z5',
            },
        ],
    },
]

PRIMARY_DEPARTMENTS = [
    {
        'name': 'People Operations',
        'description': 'Owns hiring, onboarding, and compliance operations.',
        'parent': None,
    },
    {
        'name': 'Finance',
        'description': 'Manages payroll readiness, reimbursements, and controls.',
        'parent': None,
    },
    {
        'name': 'Engineering',
        'description': 'Builds internal systems and workforce tooling.',
        'parent': None,
    },
    {
        'name': 'Platform Engineering',
        'description': 'Owns platform reliability, integrations, and infrastructure.',
        'parent': 'Engineering',
    },
    {
        'name': 'Product Engineering',
        'description': 'Owns application delivery and UX implementation.',
        'parent': 'Engineering',
    },
]


class Command(BaseCommand):
    help = 'Creates an exhaustive local Control Tower seed covering organisations, roles, onboarding, approvals, time-off, and document scenarios.'

    def handle(self, *args, **options):
        control_tower_password = self._require_env(
            'CONTROL_TOWER_PASSWORD',
            'CONTROL_TOWER_PASSWORD environment variable is not set. Set it before running this command.',
        )
        org_admin_password = self._require_env(
            'SEED_ORG_ADMIN_PASSWORD',
            'SEED_ORG_ADMIN_PASSWORD environment variable is not set. Set it before running this command.',
        )
        employee_password = self._require_env(
            'SEED_EMPLOYEE_PASSWORD',
            'SEED_EMPLOYEE_PASSWORD environment variable is not set. Set it before running this command.',
        )

        licence_count = self._get_int_env('SEED_ORGANISATION_LICENCE_COUNT', DEFAULT_ORGANISATION['licence_count'])
        if licence_count < PRIMARY_CONSUMING_EMPLOYEE_COUNT:
            raise CommandError(
                f'SEED_ORGANISATION_LICENCE_COUNT must be at least {PRIMARY_CONSUMING_EMPLOYEE_COUNT} '
                'to cover the exhaustive seeded employee scenarios.'
            )

        with transaction.atomic():
            groups = self._ensure_groups()
            ensure_default_document_types()
            control_tower = self._ensure_control_tower_user(control_tower_password, groups['control_tower'])
            primary_org = self._ensure_primary_organisation(control_tower, licence_count)
            primary_admin = self._ensure_primary_org_admin(primary_org, control_tower, groups['org_admin'], org_admin_password)
            primary_org = self._ensure_primary_admin(primary_org, primary_admin, control_tower)
            primary_org = self._ensure_active(primary_org, control_tower)
            shared_admin = self._ensure_same_email_workforce_admin(
                control_tower,
                primary_org,
                control_tower_password,
                groups,
            )
            primary_context = self._seed_primary_org(
                primary_org,
                control_tower,
                primary_admin,
                shared_admin,
                groups,
                employee_password,
            )
            secondary_context = self._seed_secondary_organisations(control_tower, shared_admin, groups)
            self._print_seed_summary(control_tower, primary_admin, shared_admin, primary_context, secondary_context)

        self.stdout.write(self.style.SUCCESS('Exhaustive Control Tower seed completed.'))

    def _get_int_env(self, key, default):
        raw_value = os.environ.get(key, str(default))
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise CommandError(f'{key} must be an integer.') from exc
        if value < 1:
            raise CommandError(f'{key} must be at least 1.')
        return value

    def _require_env(self, key, message):
        value = os.environ.get(key)
        if not value:
            raise CommandError(message)
        return value

    def _primary_domain(self):
        return os.environ.get('SEED_ORG_ADMIN_EMAIL', DEFAULT_ORG_ADMIN['email']).split('@', 1)[-1]

    def _email_for_primary_org(self, local_part):
        return f'{local_part}@{self._primary_domain()}'

    def _names_from_email(self, email):
        local_part = email.split('@', 1)[0].replace('.', ' ').replace('_', ' ').replace('-', ' ')
        parts = [segment for segment in local_part.split() if segment]
        first_name = parts[0].title() if parts else 'Organisation'
        last_name = ' '.join(part.title() for part in parts[1:]) if len(parts) > 1 else 'Admin'
        return first_name, last_name

    def _bootstrap_admin_for_primary_org(self):
        return {
            'first_name': os.environ.get('SEED_ORG_ADMIN_FIRST_NAME', DEFAULT_ORG_ADMIN['first_name']),
            'last_name': os.environ.get('SEED_ORG_ADMIN_LAST_NAME', DEFAULT_ORG_ADMIN['last_name']),
            'email': os.environ.get('SEED_ORG_ADMIN_EMAIL', DEFAULT_ORG_ADMIN['email']),
            'phone': os.environ.get(
                'SEED_ORG_ADMIN_PHONE',
                os.environ.get('SEED_ORGANISATION_PHONE', DEFAULT_ORGANISATION['phone']),
            ),
        }

    def _bootstrap_admin_for_config(self, config):
        first_name, last_name = self._names_from_email(config['email'])
        return {
            'first_name': first_name,
            'last_name': last_name,
            'email': config['email'],
            'phone': config['phone'],
        }

    def _ensure_groups(self):
        groups = {}
        for group_name in ['control_tower', 'org_admin', 'employee']:
            group, created = Group.objects.get_or_create(name=group_name)
            groups[group_name] = group
            if created:
                self.stdout.write(f'  Created group: {group_name}')
        return groups

    def _ensure_control_tower_user(self, password, group):
        email = os.environ.get('CONTROL_TOWER_EMAIL', 'admin@clarisal.com')
        user, created = User.objects.get_or_create(
            email=email,
            account_type=AccountType.CONTROL_TOWER,
            defaults={
                'first_name': 'Control',
                'last_name': 'Tower',
                'role': UserRole.CONTROL_TOWER,
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
            },
        )
        user.first_name = 'Control'
        user.last_name = 'Tower'
        user.account_type = AccountType.CONTROL_TOWER
        user.role = UserRole.CONTROL_TOWER
        user.organisation = None
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.set_password(password)
        user.save()
        user.groups.add(group)

        if created:
            self.stdout.write(self.style.SUCCESS(f'Control Tower user created: {email}'))
        else:
            self.stdout.write(self.style.WARNING(f'Control Tower user {email} already exists, updated seed state.'))
        return user

    def _organisation_defaults(self):
        organisation_defaults = {
            'name': os.environ.get('SEED_ORGANISATION_NAME', DEFAULT_ORGANISATION['name']),
            'pan_number': os.environ.get('SEED_ORGANISATION_PAN', DEFAULT_ORGANISATION['pan_number']),
            'country_code': os.environ.get('SEED_ORGANISATION_COUNTRY_CODE', DEFAULT_ORGANISATION['country_code']),
            'currency': os.environ.get('SEED_ORGANISATION_CURRENCY', DEFAULT_ORGANISATION['currency']),
            'entity_type': os.environ.get('SEED_ORGANISATION_ENTITY_TYPE', DEFAULT_ORGANISATION['entity_type']),
        }
        registered_line1 = os.environ.get(
            'SEED_ORGANISATION_ADDRESS',
            DEFAULT_ORGANISATION['addresses'][0]['line1'],
        )
        return organisation_defaults, [
            {
                **DEFAULT_ORGANISATION['addresses'][0],
                'line1': registered_line1,
                'gstin': f"29{organisation_defaults['pan_number']}1Z5",
            },
            {
                **DEFAULT_ORGANISATION['addresses'][1],
                'gstin': f"27{organisation_defaults['pan_number']}1Z7",
            },
            {
                **DEFAULT_ORGANISATION['addresses'][2],
                'gstin': f"29{organisation_defaults['pan_number']}2Z4",
            },
            DEFAULT_ORGANISATION['addresses'][3],
            DEFAULT_ORGANISATION['addresses'][4],
        ]

    def _ensure_primary_organisation(self, control_tower, licence_count):
        organisation_defaults, addresses = self._organisation_defaults()
        seed_slug = slugify(organisation_defaults['name'])
        organisation = (
            Organisation.objects.filter(slug=seed_slug).first()
            or Organisation.objects.filter(name=organisation_defaults['name']).first()
        )

        if organisation is None:
            organisation = create_organisation(
                name=organisation_defaults['name'],
                licence_count=licence_count,
                created_by=control_tower,
                pan_number=organisation_defaults['pan_number'],
                addresses=addresses,
                primary_admin=self._bootstrap_admin_for_primary_org(),
                country_code=organisation_defaults['country_code'],
                currency=organisation_defaults['currency'],
                entity_type=organisation_defaults['entity_type'],
            )
            self.stdout.write(self.style.SUCCESS(f"Primary demo organisation created: {organisation_defaults['name']}"))
        else:
            changed = False
            for field, value in organisation_defaults.items():
                if getattr(organisation, field) != value:
                    setattr(organisation, field, value)
                    changed = True
            if organisation.created_by_id is None:
                organisation.created_by = control_tower
                changed = True
            if changed:
                organisation = update_organisation_profile(organisation, actor=control_tower, **organisation_defaults)
                self.stdout.write(
                    self.style.WARNING(f"Primary demo organisation {organisation.name} already exists, updated seed state.")
                )
        upsert_bootstrap_admin(organisation, actor=control_tower, **self._bootstrap_admin_for_primary_org())

        self._ensure_addresses(organisation, control_tower, addresses, auto_create_location=True)
        if organisation.licence_count != licence_count:
            try:
                organisation = update_licence_count(
                    organisation,
                    licence_count,
                    changed_by=control_tower,
                    note='Seed sync licence allocation',
                )
            except ValueError as exc:
                raise CommandError(str(exc)) from exc

        batch = self._ensure_named_licence_batch(
            organisation,
            control_tower,
            quantity=licence_count,
            start_date=date.today(),
            end_date=self._next_year(date.today()),
            note='Seed opening licence batch',
            paid=True,
        )
        if batch.payment_status != LicenceBatchPaymentStatus.PAID:
            mark_licence_batch_paid(batch, paid_by=control_tower, paid_at=date.today())
        if organisation.status == OrganisationStatus.PENDING:
            organisation = transition_organisation_state(
                organisation,
                OrganisationStatus.PAID,
                control_tower,
                note='Seed payment marked as received',
            )
        return organisation

    def _ensure_primary_org_admin(self, organisation, actor, group, password):
        email = os.environ.get('SEED_ORG_ADMIN_EMAIL', DEFAULT_ORG_ADMIN['email'])
        first_name = os.environ.get('SEED_ORG_ADMIN_FIRST_NAME', DEFAULT_ORG_ADMIN['first_name'])
        last_name = os.environ.get('SEED_ORG_ADMIN_LAST_NAME', DEFAULT_ORG_ADMIN['last_name'])
        user = self._ensure_workforce_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            groups=[group],
        )
        ensure_org_admin_membership(
            organisation,
            user,
            invited_by=actor,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        sync_user_role(user)
        return user

    def _ensure_same_email_workforce_admin(self, control_tower, organisation, password, groups):
        workforce_email = control_tower.email
        primary_admin_email = os.environ.get('SEED_ORG_ADMIN_EMAIL', DEFAULT_ORG_ADMIN['email'])
        if workforce_email == primary_admin_email:
            ensure_org_admin_membership(
                organisation,
                User.objects.get(email=workforce_email, account_type=AccountType.WORKFORCE),
                invited_by=control_tower,
                status=OrganisationMembershipStatus.ACTIVE,
            )
            existing = User.objects.get(email=workforce_email, account_type=AccountType.WORKFORCE)
            existing.groups.add(groups['org_admin'])
            sync_user_role(existing)
            return existing

        user = self._ensure_workforce_user(
            email=workforce_email,
            password=password,
            first_name='Control',
            last_name='Tower',
            is_active=True,
            groups=[groups['org_admin'], groups['employee']],
        )
        ensure_org_admin_membership(
            organisation,
            user,
            invited_by=control_tower,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        sync_user_role(user)
        return user

    def _ensure_primary_admin(self, organisation, org_admin, control_tower):
        if organisation.primary_admin_user_id != org_admin.id:
            organisation = set_primary_admin(organisation, org_admin, control_tower)
        mark_bootstrap_admin_accepted(organisation, org_admin)
        return organisation

    def _ensure_active(self, organisation, control_tower):
        if organisation.status in [OrganisationStatus.PAID, OrganisationStatus.SUSPENDED]:
            organisation = transition_organisation_state(
                organisation,
                OrganisationStatus.ACTIVE,
                control_tower,
                note='Seed organisation activated for local access',
            )
        return organisation

    def _ensure_addresses(self, organisation, actor, addresses, auto_create_location):
        existing = {(address.address_type, address.label): address for address in organisation.addresses.all()}
        for payload in addresses:
            label = payload.get('label') or self._default_label(payload['address_type'])
            key = (payload['address_type'], label)
            current = existing.get(key)
            address_payload = {**payload, 'label': label}
            if current is None:
                create_organisation_address(
                    organisation,
                    actor=actor,
                    auto_create_location=auto_create_location,
                    **address_payload,
                )
                continue
            update_organisation_address(current, actor=actor, **address_payload)

    def _default_label(self, address_type):
        return {
            OrganisationAddressType.REGISTERED: 'Registered Office',
            OrganisationAddressType.BILLING: 'Billing Address',
            OrganisationAddressType.HEADQUARTERS: 'Headquarters',
            OrganisationAddressType.WAREHOUSE: 'Warehouse',
            OrganisationAddressType.CUSTOM: 'Custom Address',
        }[address_type]

    def _next_year(self, value):
        try:
            return value.replace(year=value.year + 1)
        except ValueError:
            return value.replace(month=2, day=28, year=value.year + 1)

    def _ensure_named_licence_batch(self, organisation, actor, *, quantity, start_date, end_date, note, paid):
        batch = organisation.licence_batches.filter(note=note).order_by('created_at').first()
        if batch is None:
            batch = create_licence_batch(
                organisation,
                quantity=quantity,
                price_per_licence_per_month='0.00',
                start_date=start_date,
                end_date=end_date,
                created_by=actor,
                note=note,
            )
        if paid and batch.payment_status != LicenceBatchPaymentStatus.PAID:
            batch = mark_licence_batch_paid(batch, paid_by=actor, paid_at=start_date)
        return batch

    def _seed_primary_org(self, organisation, control_tower, primary_admin, shared_admin, groups, employee_password):
        locations = self._ensure_primary_locations(organisation, primary_admin)
        departments = self._ensure_primary_departments(organisation)

        shared_admin_employee = self._ensure_employee_record(
            organisation=organisation,
            user=shared_admin,
            employee_code='EMP001',
            department=departments['People Operations'],
            office_location=locations['Bengaluru HQ'],
            designation='People & Platform Director',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=date(2023, 4, 7),
            status=EmployeeStatus.ACTIVE,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
            groups=[groups['employee']],
        )
        shared_admin_employee.reporting_to = shared_admin_employee
        shared_admin_employee.save(update_fields=['reporting_to', 'modified_at'])
        self._seed_employee_details(
            shared_admin_employee,
            profile={
                'date_of_birth': date(1990, 4, 20),
                'gender': 'MALE',
                'marital_status': 'MARRIED',
                'nationality': 'Indian',
                'blood_type': 'O_POSITIVE',
                'phone_personal': '+91 9000000001',
                'phone_emergency': '+91 9000000099',
                'emergency_contact_name': 'Asha Tower',
                'emergency_contact_relation': 'Spouse',
                'address_line1': '12 Palm Meadows',
                'address_line2': 'Whitefield',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'country': 'India',
                'pincode': '560066',
            },
            government_ids=[
                {'id_type': GovernmentIdType.PAN, 'identifier': 'ABCDE2345F', 'name_on_id': 'Control Tower'},
                {'id_type': GovernmentIdType.AADHAAR, 'identifier': '234523452345', 'name_on_id': 'Control Tower'},
            ],
            family_members=[
                {
                    'full_name': 'Asha Tower',
                    'relation': FamilyRelationChoice.SPOUSE,
                    'date_of_birth': date(1991, 11, 2),
                    'contact_number': '+91 9000000002',
                    'is_dependent': True,
                }
            ],
            emergency_contacts=[
                {
                    'full_name': 'Asha Tower',
                    'relation': 'Spouse',
                    'phone_number': '+91 9000000002',
                    'alternate_phone_number': '+91 9000000003',
                    'address': '12 Palm Meadows, Whitefield, Bengaluru',
                    'is_primary': True,
                }
            ],
            bank_account={
                'account_holder_name': 'Control Tower',
                'bank_name': 'ICICI Bank',
                'account_number': '123450001234',
                'ifsc': 'ICIC0001234',
                'account_type': 'SALARY',
                'branch_name': 'Whitefield',
                'is_primary': True,
            },
        )

        priya_user = self._ensure_workforce_user(
            email=self._email_for_primary_org('priya.sharma'),
            password=employee_password,
            first_name='Priya',
            last_name='Sharma',
            is_active=True,
            groups=[groups['employee']],
        )
        priya = self._ensure_employee_record(
            organisation=organisation,
            user=priya_user,
            employee_code='EMP002',
            department=departments['People Operations'],
            office_location=locations['Registered Office'],
            designation='HR Operations Manager',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=date(2024, 4, 15),
            status=EmployeeStatus.ACTIVE,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
        )
        priya.reporting_to = shared_admin_employee
        priya.save(update_fields=['reporting_to', 'modified_at'])
        self._seed_employee_details(
            priya,
            profile={
                'date_of_birth': date(1994, 4, 10),
                'gender': 'FEMALE',
                'marital_status': 'MARRIED',
                'nationality': 'Indian',
                'blood_type': 'A_POSITIVE',
                'phone_personal': '+91 9988776655',
                'phone_emergency': '+91 9988776611',
                'emergency_contact_name': 'Rahul Sharma',
                'emergency_contact_relation': 'Spouse',
                'address_line1': '12 Lakeside Residency',
                'address_line2': 'HSR Layout',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'country': 'India',
                'pincode': '560102',
            },
            education={
                'degree': 'MBA',
                'institution': 'Christ University',
                'field_of_study': 'Human Resources',
                'start_year': 2014,
                'end_year': 2016,
                'grade': 'A',
                'is_current': False,
            },
            government_ids=[
                {'id_type': GovernmentIdType.PAN, 'identifier': 'ABCDE1234F', 'name_on_id': 'Priya Sharma'},
                {'id_type': GovernmentIdType.AADHAAR, 'identifier': '123412341234', 'name_on_id': 'Priya Sharma'},
            ],
            family_members=[
                {
                    'full_name': 'Rahul Sharma',
                    'relation': FamilyRelationChoice.SPOUSE,
                    'date_of_birth': date(1992, 5, 18),
                    'contact_number': '+91 9988776600',
                    'is_dependent': True,
                }
            ],
            emergency_contacts=[
                {
                    'full_name': 'Rahul Sharma',
                    'relation': 'Spouse',
                    'phone_number': '+91 9988776600',
                    'alternate_phone_number': '+91 9988776601',
                    'address': '12 Lakeside Residency, HSR Layout, Bengaluru',
                    'is_primary': True,
                }
            ],
            bank_account={
                'account_holder_name': 'Priya Sharma',
                'bank_name': 'HDFC Bank',
                'account_number': '123456789012',
                'ifsc': 'HDFC0001234',
                'account_type': 'SALARY',
                'branch_name': 'HSR Layout',
                'is_primary': True,
            },
        )

        rohan_user = self._ensure_workforce_user(
            email=self._email_for_primary_org('rohan.mehta'),
            password=employee_password,
            first_name='Rohan',
            last_name='Mehta',
            is_active=True,
            groups=[groups['employee']],
        )
        rohan = self._ensure_employee_record(
            organisation=organisation,
            user=rohan_user,
            employee_code='EMP003',
            department=departments['Finance'],
            office_location=locations['Billing Address'],
            designation='Finance Analyst',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=date(2024, 9, 16),
            status=EmployeeStatus.ACTIVE,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
        )
        rohan.reporting_to = shared_admin_employee
        rohan.save(update_fields=['reporting_to', 'modified_at'])
        self._seed_employee_details(
            rohan,
            profile={
                'date_of_birth': date(1995, 8, 11),
                'gender': 'MALE',
                'marital_status': 'SINGLE',
                'nationality': 'Indian',
                'blood_type': 'B_POSITIVE',
                'phone_personal': '+91 9000100010',
                'phone_emergency': '+91 9000100011',
                'emergency_contact_name': 'Neha Mehta',
                'emergency_contact_relation': 'Sister',
                'address_line1': '17 Riverstone Residency',
                'address_line2': 'Powai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '400076',
            },
            government_ids=[
                {'id_type': GovernmentIdType.PAN, 'identifier': 'BCDEA2345G', 'name_on_id': 'Rohan Mehta'},
                {'id_type': GovernmentIdType.AADHAAR, 'identifier': '222233334444', 'name_on_id': 'Rohan Mehta'},
            ],
            family_members=[
                {
                    'full_name': 'Sanjay Mehta',
                    'relation': FamilyRelationChoice.FATHER,
                    'date_of_birth': date(1966, 6, 14),
                    'contact_number': '+91 9000100012',
                    'is_dependent': False,
                }
            ],
            emergency_contacts=[
                {
                    'full_name': 'Neha Mehta',
                    'relation': 'Sister',
                    'phone_number': '+91 9000100013',
                    'alternate_phone_number': '',
                    'address': '17 Riverstone Residency, Powai, Mumbai',
                    'is_primary': True,
                }
            ],
            bank_account={
                'account_holder_name': 'Rohan Mehta',
                'bank_name': 'Axis Bank',
                'account_number': '789456123012',
                'ifsc': 'UTIB0001234',
                'account_type': 'SALARY',
                'branch_name': 'Powai',
                'is_primary': True,
            },
        )

        ananya_user = self._ensure_workforce_user(
            email=self._email_for_primary_org('ananya.iyer'),
            password=employee_password,
            first_name='Ananya',
            last_name='Iyer',
            is_active=True,
            groups=[groups['employee']],
        )
        ananya = self._ensure_employee_record(
            organisation=organisation,
            user=ananya_user,
            employee_code='EMP004',
            department=departments['Platform Engineering'],
            office_location=locations['Distributed Workforce'],
            designation='Senior Software Engineer',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=date(2025, 1, 6),
            status=EmployeeStatus.ACTIVE,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
        )
        ananya.reporting_to = shared_admin_employee
        ananya.save(update_fields=['reporting_to', 'modified_at'])
        self._seed_employee_details(
            ananya,
            profile={
                'date_of_birth': date(1997, 7, 9),
                'gender': 'FEMALE',
                'marital_status': 'SINGLE',
                'nationality': 'Indian',
                'blood_type': 'AB_POSITIVE',
                'phone_personal': '+91 9000200020',
                'phone_emergency': '+91 9000200021',
                'emergency_contact_name': 'Raghav Iyer',
                'emergency_contact_relation': 'Brother',
                'address_line1': '22 Orchid Towers',
                'address_line2': 'Koregaon Park',
                'city': 'Pune',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '411001',
            },
            government_ids=[
                {'id_type': GovernmentIdType.PAN, 'identifier': 'CDEAB3456H', 'name_on_id': 'Ananya Iyer'},
                {'id_type': GovernmentIdType.AADHAAR, 'identifier': '333344445555', 'name_on_id': 'Ananya Iyer'},
            ],
            family_members=[
                {
                    'full_name': 'Raghav Iyer',
                    'relation': FamilyRelationChoice.BROTHER,
                    'date_of_birth': date(1993, 3, 27),
                    'contact_number': '+91 9000200022',
                    'is_dependent': False,
                }
            ],
            emergency_contacts=[
                {
                    'full_name': 'Raghav Iyer',
                    'relation': 'Brother',
                    'phone_number': '+91 9000200022',
                    'alternate_phone_number': '',
                    'address': '22 Orchid Towers, Koregaon Park, Pune',
                    'is_primary': True,
                }
            ],
            bank_account={
                'account_holder_name': 'Ananya Iyer',
                'bank_name': 'SBI',
                'account_number': '456789123012',
                'ifsc': 'SBIN0001234',
                'account_type': 'SALARY',
                'branch_name': 'Koregaon Park',
                'is_primary': True,
            },
        )

        resigned = self._ensure_employee_record(
            organisation=organisation,
            user=self._ensure_workforce_user(
                email=self._email_for_primary_org('raj.nair'),
                password=employee_password,
                first_name='Raj',
                last_name='Nair',
                is_active=True,
                groups=[groups['employee']],
            ),
            employee_code='EMP005',
            department=departments['Finance'],
            office_location=locations['Billing Address'],
            designation='Payroll Specialist',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=date(2022, 2, 7),
            date_of_exit=date(2026, 2, 28),
            status=EmployeeStatus.RESIGNED,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
        )
        resigned.reporting_to = shared_admin_employee
        resigned.save(update_fields=['reporting_to', 'modified_at'])

        retired = self._ensure_employee_record(
            organisation=organisation,
            user=self._ensure_workforce_user(
                email=self._email_for_primary_org('leena.kulkarni'),
                password=employee_password,
                first_name='Leena',
                last_name='Kulkarni',
                is_active=True,
                groups=[groups['employee']],
            ),
            employee_code='EMP006',
            department=departments['People Operations'],
            office_location=locations['Registered Office'],
            designation='Compliance Lead',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=date(2001, 7, 9),
            date_of_exit=date(2026, 3, 31),
            status=EmployeeStatus.RETIRED,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
        )
        retired.reporting_to = shared_admin_employee
        retired.save(update_fields=['reporting_to', 'modified_at'])

        terminated = self._ensure_employee_record(
            organisation=organisation,
            user=self._ensure_workforce_user(
                email=self._email_for_primary_org('kabir.khan'),
                password=employee_password,
                first_name='Kabir',
                last_name='Khan',
                is_active=True,
                groups=[groups['employee']],
            ),
            employee_code='EMP007',
            department=departments['Product Engineering'],
            office_location=locations['Pune Satellite Office'],
            designation='Support Engineer',
            employment_type=EmploymentType.CONTRACT,
            date_of_joining=date(2025, 6, 2),
            date_of_exit=date(2026, 3, 18),
            status=EmployeeStatus.TERMINATED,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
        )
        terminated.reporting_to = shared_admin_employee
        terminated.save(update_fields=['reporting_to', 'modified_at'])

        onboarding_employee = self._ensure_invited_employee(
            organisation=organisation,
            email=self._email_for_primary_org('meera.singh'),
            password=employee_password,
            first_name='Meera',
            last_name='Singh',
            designation='Implementation Analyst',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=None,
            department=departments['People Operations'],
            office_location=locations['Registered Office'],
            required_document_codes=['AADHAAR_CARD', 'PAN_CARD', 'CANCELLED_CHEQUE', 'DEGREE_CERTIFICATE'],
            invited_by=primary_admin,
            accept_invite=True,
            completed_basic_details=False,
            desired_status=EmployeeStatus.INVITED,
            groups=[groups['employee']],
        )

        pending_employee = self._ensure_invited_employee(
            organisation=organisation,
            email=self._email_for_primary_org('karthik.verma'),
            password=employee_password,
            first_name='Karthik',
            last_name='Verma',
            designation='Finance Associate',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=None,
            department=departments['Finance'],
            office_location=locations['Billing Address'],
            required_document_codes=['AADHAAR_CARD', 'PAN_CARD', 'CANCELLED_CHEQUE', 'BACKGROUND_CHECK_CONSENT'],
            invited_by=primary_admin,
            accept_invite=True,
            completed_basic_details=True,
            desired_status=EmployeeStatus.PENDING,
            groups=[groups['employee']],
        )

        pending_invite_employee = self._ensure_invited_employee(
            organisation=organisation,
            email=self._email_for_primary_org('isha.kapoor'),
            password=employee_password,
            first_name='Isha',
            last_name='Kapoor',
            designation='People Ops Coordinator',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=None,
            department=departments['People Operations'],
            office_location=locations['Registered Office'],
            required_document_codes=['AADHAAR_CARD', 'PAN_CARD', 'PASSPORT_PHOTO'],
            invited_by=primary_admin,
            accept_invite=False,
            completed_basic_details=False,
            desired_status=EmployeeStatus.INVITED,
            groups=[groups['employee']],
        )

        self._ensure_supplemental_invitation(
            organisation=organisation,
            email=self._email_for_primary_org('former.candidate'),
            role=InvitationRole.EMPLOYEE,
            invited_by=primary_admin,
            status=InvitationStatus.REVOKED,
            expires_in_hours=48,
        )
        self._ensure_supplemental_invitation(
            organisation=organisation,
            email=self._email_for_primary_org('expired.candidate'),
            role=InvitationRole.EMPLOYEE,
            invited_by=primary_admin,
            status=InvitationStatus.EXPIRED,
            expires_in_hours=-24,
        )

        workflow_context = self._ensure_approval_workflows(
            organisation,
            primary_admin,
            departments=departments,
            locations=locations,
            employees={
                'shared_admin': shared_admin_employee,
                'priya': priya,
                'rohan': rohan,
                'ananya': ananya,
            },
        )
        leave_context = self._ensure_leave_setup(
            organisation,
            primary_admin,
            departments=departments,
            locations=locations,
            employees={
                'priya': priya,
                'rohan': rohan,
                'ananya': ananya,
                'shared_admin': shared_admin_employee,
            },
        )
        self._ensure_document_stage(primary_admin, employees={
            'priya': priya,
            'onboarding': onboarding_employee,
            'pending': pending_employee,
        })
        self._ensure_holiday_calendars(organisation, primary_admin, locations)
        self._ensure_notices(
            organisation,
            primary_admin,
            departments=departments,
            locations=locations,
            employees={
                'priya': priya,
                'rohan': rohan,
                'ananya': ananya,
                'pending': pending_employee,
            },
        )
        self._ensure_timeoff_activity(
            organisation,
            primary_admin,
            employees={
                'priya': priya,
                'rohan': rohan,
                'ananya': ananya,
            },
            leave_context=leave_context,
            workflow_context=workflow_context,
        )
        mark_master_data_configured(organisation, primary_admin)
        mark_employee_invited(organisation, primary_admin, onboarding_employee)

        return {
            'locations': locations,
            'departments': departments,
            'employees': {
                'shared_admin': shared_admin_employee,
                'priya': priya,
                'rohan': rohan,
                'ananya': ananya,
                'onboarding': onboarding_employee,
                'pending': pending_employee,
                'pending_invite': pending_invite_employee,
                'resigned': resigned,
                'retired': retired,
                'terminated': terminated,
            },
        }

    def _ensure_primary_locations(self, organisation, actor):
        locations = {}
        for address in organisation.addresses.filter(is_active=True).order_by('created_at'):
            location, _ = OfficeLocation.objects.get_or_create(
                organisation=organisation,
                name=address.label,
                defaults={'organisation_address': address, 'is_remote': False},
            )
            payload = {
                'organisation_address_id': address.id,
                'name': address.label,
                'is_remote': False,
                'is_active': True,
            }
            if location.organisation_address_id != address.id or location.is_remote:
                location = update_location(location, actor=actor, **payload)
            else:
                location.organisation_address = address
                location.address = address.line1
                location.city = address.city
                location.state = address.state
                location.country = address.country
                location.pincode = address.pincode
                location.is_active = True
                location.save()
            locations[location.name] = location

        hq_address = organisation.addresses.filter(label='Bengaluru HQ', is_active=True).first()
        if hq_address:
            remote_location = organisation.locations.filter(name='Distributed Workforce').first()
            payload = {
                'name': 'Distributed Workforce',
                'organisation_address_id': hq_address.id,
                'is_remote': True,
                'is_active': True,
            }
            if remote_location is None:
                remote_location = create_location(organisation, actor=actor, **payload)
            else:
                remote_location = update_location(remote_location, actor=actor, **payload)
            locations[remote_location.name] = remote_location
        return locations

    def _ensure_primary_departments(self, organisation):
        departments = {}
        for payload in PRIMARY_DEPARTMENTS:
            department, _ = Department.objects.get_or_create(
                organisation=organisation,
                name=payload['name'],
                defaults={
                    'description': payload['description'],
                },
            )
            department.description = payload['description']
            department.is_active = True
            department.save(update_fields=['description', 'is_active', 'modified_at'])
            departments[department.name] = department
        for payload in PRIMARY_DEPARTMENTS:
            parent_name = payload['parent']
            if not parent_name:
                continue
            department = departments[payload['name']]
            parent = departments[parent_name]
            if department.parent_department_id != parent.id:
                department.parent_department = parent
                department.save(update_fields=['parent_department', 'modified_at'])
        return departments

    def _ensure_workforce_user(self, *, email, password, first_name, last_name, is_active, groups):
        user, _ = User.objects.get_or_create(
            email=email,
            account_type=AccountType.WORKFORCE,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': UserRole.EMPLOYEE,
                'is_active': is_active,
            },
        )
        user.first_name = first_name
        user.last_name = last_name
        user.account_type = AccountType.WORKFORCE
        user.organisation = None
        user.is_active = is_active
        user.set_password(password)
        user.save()
        for group in groups:
            user.groups.add(group)
        sync_user_role(user)
        return user

    def _ensure_employee_record(
        self,
        *,
        organisation,
        user,
        employee_code,
        department,
        office_location,
        designation,
        employment_type,
        status,
        onboarding_status,
        date_of_joining=None,
        date_of_exit=None,
        groups=None,
    ):
        if groups:
            for group in groups:
                user.groups.add(group)
        employee = Employee.all_objects.filter(organisation=organisation, user=user).first()
        if employee is None:
            employee = Employee(organisation=organisation, user=user)
        employee.is_deleted = False
        employee.deleted_at = None
        employee.employee_code = employee_code
        employee.department = department
        employee.office_location = office_location
        employee.designation = designation
        employee.employment_type = employment_type
        employee.date_of_joining = date_of_joining
        employee.date_of_exit = date_of_exit
        employee.status = status
        employee.onboarding_status = onboarding_status
        if onboarding_status == EmployeeOnboardingStatus.COMPLETE and employee.onboarding_completed_at is None:
            employee.onboarding_completed_at = timezone.now()
        employee.save()
        EmployeeProfile.objects.get_or_create(employee=employee)
        sync_user_role(user)
        return employee

    def _seed_employee_details(
        self,
        employee,
        *,
        profile=None,
        education=None,
        government_ids=None,
        family_members=None,
        emergency_contacts=None,
        bank_account=None,
    ):
        if profile:
            profile_obj, _ = EmployeeProfile.objects.get_or_create(employee=employee)
            for field, value in profile.items():
                setattr(profile_obj, field, value)
            profile_obj.save()

        if education:
            education_record = employee.education_records.filter(
                degree=education['degree'],
                institution=education['institution'],
            ).first()
            if education_record is None:
                EducationRecord.objects.create(employee=employee, **education)
            else:
                update_education_record(education_record, actor=employee.user, **education)

        for government_id in government_ids or []:
            upsert_government_id(
                employee,
                government_id['id_type'],
                government_id['identifier'],
                actor=employee.user,
                name_on_id=government_id['name_on_id'],
            )

        for payload in family_members or []:
            member = EmployeeFamilyMember.all_objects.filter(
                employee=employee,
                full_name=payload['full_name'],
                relation=payload['relation'],
            ).first()
            if member is None:
                member = EmployeeFamilyMember(employee=employee)
            member.is_deleted = False
            member.deleted_at = None
            for field, value in payload.items():
                setattr(member, field, value)
            member.save()

        for payload in emergency_contacts or []:
            contact = EmployeeEmergencyContact.all_objects.filter(
                employee=employee,
                full_name=payload['full_name'],
                relation=payload['relation'],
                phone_number=payload['phone_number'],
            ).first()
            if contact is None:
                contact = EmployeeEmergencyContact(employee=employee)
            contact.is_deleted = False
            contact.deleted_at = None
            for field, value in payload.items():
                setattr(contact, field, value)
            contact.save()

        if bank_account:
            account = employee.bank_accounts.filter(is_primary=True).first()
            if account is None:
                create_bank_account(employee, actor=employee.user, **bank_account)
            else:
                update_bank_account(account, actor=employee.user, **bank_account)

    def _ensure_invited_employee(
        self,
        *,
        organisation,
        email,
        password,
        first_name,
        last_name,
        designation,
        employment_type,
        date_of_joining,
        department,
        office_location,
        required_document_codes,
        invited_by,
        accept_invite,
        completed_basic_details,
        desired_status,
        groups,
    ):
        user = self._ensure_workforce_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=accept_invite,
            groups=groups,
        )
        employee = self._ensure_employee_record(
            organisation=organisation,
            user=user,
            employee_code=None,
            department=department,
            office_location=office_location,
            designation=designation,
            employment_type=employment_type,
            date_of_joining=date_of_joining,
            status=EmployeeStatus.INVITED,
            onboarding_status=EmployeeOnboardingStatus.NOT_STARTED,
        )
        document_type_ids = list(
            OnboardingDocumentType.objects.filter(code__in=required_document_codes).values_list('id', flat=True)
        )
        assign_document_requests(employee, document_type_ids, actor=invited_by)
        self._ensure_invitation(
            organisation=organisation,
            user=user,
            role=InvitationRole.EMPLOYEE,
            invited_by=invited_by,
            status=InvitationStatus.ACCEPTED if accept_invite else InvitationStatus.PENDING,
            expires_in_hours=48 if accept_invite else 72,
        )

        if accept_invite:
            profile_payload = {
                'date_of_birth': date(1998, 6, 15),
                'gender': 'MALE',
                'marital_status': 'SINGLE',
                'nationality': 'Indian',
                'blood_type': 'O_POSITIVE',
                'phone_personal': '+91 9111111111',
                'phone_emergency': '+91 9222222222',
                'emergency_contact_name': 'Parent Contact',
                'emergency_contact_relation': 'Parent',
                'address_line1': '44 Seaside Apartments',
                'address_line2': 'Baner',
                'city': 'Pune',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '411045',
            }
            if completed_basic_details:
                self._seed_employee_details(
                    employee,
                    profile=profile_payload,
                    government_ids=[
                        {'id_type': GovernmentIdType.PAN, 'identifier': 'PQRST1234L', 'name_on_id': f'{first_name} {last_name}'},
                        {'id_type': GovernmentIdType.AADHAAR, 'identifier': '888899990000', 'name_on_id': f'{first_name} {last_name}'},
                    ],
                    family_members=[
                        {
                            'full_name': f'{first_name} Senior',
                            'relation': FamilyRelationChoice.FATHER,
                            'date_of_birth': date(1965, 1, 1),
                            'contact_number': '+91 9333333333',
                            'is_dependent': False,
                        }
                    ],
                    emergency_contacts=[
                        {
                            'full_name': f'{first_name} Emergency',
                            'relation': 'Parent',
                            'phone_number': '+91 9444444444',
                            'alternate_phone_number': '',
                            'address': '44 Seaside Apartments, Baner, Pune',
                            'is_primary': True,
                        }
                    ],
                )
                self._ensure_document_request_state(employee, 'AADHAAR_CARD', EmployeeDocumentRequestStatus.VERIFIED, invited_by)
                self._ensure_document_request_state(employee, 'PAN_CARD', EmployeeDocumentRequestStatus.SUBMITTED, invited_by)
                if 'CANCELLED_CHEQUE' in required_document_codes:
                    self._ensure_document_request_state(employee, 'CANCELLED_CHEQUE', EmployeeDocumentRequestStatus.WAIVED, invited_by)
                if 'BACKGROUND_CHECK_CONSENT' in required_document_codes:
                    self._ensure_document_request_state(employee, 'BACKGROUND_CHECK_CONSENT', EmployeeDocumentRequestStatus.VERIFIED, invited_by)
                refresh_employee_onboarding_status(employee, actor=invited_by)
            else:
                employee.onboarding_status = EmployeeOnboardingStatus.BASIC_DETAILS_PENDING
                employee.save(update_fields=['onboarding_status', 'modified_at'])
        else:
            employee.onboarding_status = EmployeeOnboardingStatus.NOT_STARTED
            employee.save(update_fields=['onboarding_status', 'modified_at'])

        if desired_status != employee.status:
            employee.status = desired_status
            employee.save(update_fields=['status', 'modified_at'])
        sync_user_role(user)
        return employee

    def _ensure_invitation(self, *, organisation, user, role, invited_by, status, expires_in_hours):
        invitation, _ = Invitation.objects.update_or_create(
            email=user.email,
            organisation=organisation,
            role=role,
            user=user,
            defaults={
                'invited_by': invited_by,
                'token_hash': hash_token(f'seed:{organisation.slug}:{role}:{user.email}'),
                'status': status,
                'email_sent': True,
                'expires_at': timezone.now() + timedelta(hours=expires_in_hours),
                'accepted_at': timezone.now() if status == InvitationStatus.ACCEPTED else None,
                'revoked_at': timezone.now() if status == InvitationStatus.REVOKED else None,
            },
        )
        if status == InvitationStatus.EXPIRED:
            invitation.accepted_at = None
            invitation.revoked_at = None
            invitation.save(update_fields=['accepted_at', 'revoked_at'])
        return invitation

    def _ensure_supplemental_invitation(self, *, organisation, email, role, invited_by, status, expires_in_hours):
        user = User.objects.filter(email=email, account_type=AccountType.WORKFORCE).first()
        Invitation.objects.update_or_create(
            email=email,
            organisation=organisation,
            role=role,
            defaults={
                'invited_by': invited_by,
                'user': user,
                'token_hash': hash_token(f'seed:{organisation.slug}:{role}:{email}:{status}'),
                'status': status,
                'email_sent': True,
                'expires_at': timezone.now() + timedelta(hours=expires_in_hours),
                'accepted_at': None,
                'revoked_at': timezone.now() if status == InvitationStatus.REVOKED else None,
            },
        )

    def _ensure_approval_workflows(self, organisation, actor, *, departments, locations, employees):
        leave_default = self._upsert_workflow(
            organisation=organisation,
            actor=actor,
            name='Default Leave Workflow',
            description='Default manager-led workflow for leave approvals.',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            rules=[
                {
                    'name': 'Default leave workflow',
                    'request_kind': ApprovalRequestKind.LEAVE,
                    'priority': 100,
                },
            ],
            stages=[
                {
                    'name': 'Manager review',
                    'sequence': 1,
                    'mode': ApprovalStageMode.ALL,
                    'fallback_type': ApprovalFallbackType.PRIMARY_ORG_ADMIN,
                    'fallback_employee': None,
                    'approvers': [
                        {
                            'approver_type': ApprovalApproverType.REPORTING_MANAGER,
                            'approver_employee': None,
                        }
                    ],
                },
            ],
        )

        on_duty_default = self._upsert_workflow(
            organisation=organisation,
            actor=actor,
            name='Default On-Duty Workflow',
            description='Default manager-led workflow for on-duty approvals.',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ON_DUTY,
            rules=[
                {
                    'name': 'Default on-duty workflow',
                    'request_kind': ApprovalRequestKind.ON_DUTY,
                    'priority': 100,
                },
            ],
            stages=[
                {
                    'name': 'Manager review',
                    'sequence': 1,
                    'mode': ApprovalStageMode.ALL,
                    'fallback_type': ApprovalFallbackType.PRIMARY_ORG_ADMIN,
                    'fallback_employee': None,
                    'approvers': [
                        {
                            'approver_type': ApprovalApproverType.REPORTING_MANAGER,
                            'approver_employee': None,
                        }
                    ],
                },
            ],
        )

        regularization_default = self._upsert_workflow(
            organisation=organisation,
            actor=actor,
            name='Default Attendance Regularization Workflow',
            description='Default manager-led workflow for attendance regularization approvals.',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
            rules=[
                {
                    'name': 'Default attendance regularization workflow',
                    'request_kind': ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
                    'priority': 100,
                },
            ],
            stages=[
                {
                    'name': 'Manager review',
                    'sequence': 1,
                    'mode': ApprovalStageMode.ALL,
                    'fallback_type': ApprovalFallbackType.PRIMARY_ORG_ADMIN,
                    'fallback_employee': None,
                    'approvers': [
                        {
                            'approver_type': ApprovalApproverType.REPORTING_MANAGER,
                            'approver_employee': None,
                        }
                    ],
                },
            ],
        )

        payroll_processing_default = self._upsert_workflow(
            organisation=organisation,
            actor=actor,
            name='Default Payroll Processing Workflow',
            description='Default primary-admin workflow for payroll processing approvals.',
            is_default=True,
            default_request_kind=ApprovalRequestKind.PAYROLL_PROCESSING,
            rules=[
                {
                    'name': 'Default payroll processing workflow',
                    'request_kind': ApprovalRequestKind.PAYROLL_PROCESSING,
                    'priority': 100,
                },
            ],
            stages=[
                {
                    'name': 'Primary org admin review',
                    'sequence': 1,
                    'mode': ApprovalStageMode.ALL,
                    'fallback_type': ApprovalFallbackType.NONE,
                    'fallback_employee': None,
                    'approvers': [
                        {
                            'approver_type': ApprovalApproverType.PRIMARY_ORG_ADMIN,
                            'approver_employee': None,
                        }
                    ],
                },
            ],
        )

        salary_revision_default = self._upsert_workflow(
            organisation=organisation,
            actor=actor,
            name='Default Salary Revision Workflow',
            description='Default primary-admin workflow for salary revision approvals.',
            is_default=True,
            default_request_kind=ApprovalRequestKind.SALARY_REVISION,
            rules=[
                {
                    'name': 'Default salary revision workflow',
                    'request_kind': ApprovalRequestKind.SALARY_REVISION,
                    'priority': 100,
                },
            ],
            stages=[
                {
                    'name': 'Primary org admin review',
                    'sequence': 1,
                    'mode': ApprovalStageMode.ALL,
                    'fallback_type': ApprovalFallbackType.NONE,
                    'fallback_employee': None,
                    'approvers': [
                        {
                            'approver_type': ApprovalApproverType.PRIMARY_ORG_ADMIN,
                            'approver_employee': None,
                        }
                    ],
                },
            ],
        )

        template_change_default = self._upsert_workflow(
            organisation=organisation,
            actor=actor,
            name='Default Compensation Template Workflow',
            description='Default primary-admin workflow for compensation template approvals.',
            is_default=True,
            default_request_kind=ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
            rules=[
                {
                    'name': 'Default compensation template workflow',
                    'request_kind': ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
                    'priority': 100,
                },
            ],
            stages=[
                {
                    'name': 'Primary org admin review',
                    'sequence': 1,
                    'mode': ApprovalStageMode.ALL,
                    'fallback_type': ApprovalFallbackType.NONE,
                    'fallback_employee': None,
                    'approvers': [
                        {
                            'approver_type': ApprovalApproverType.PRIMARY_ORG_ADMIN,
                            'approver_employee': None,
                        }
                    ],
                },
            ],
        )

        finance = self._upsert_workflow(
            organisation=organisation,
            actor=actor,
            name='Finance Escalation Workflow',
            description='Finance requests can be escalated directly to the primary org admin.',
            is_default=False,
            default_request_kind=None,
            rules=[
                {
                    'name': 'Controller level approvals',
                    'request_kind': ApprovalRequestKind.LEAVE,
                    'priority': 10,
                    'designation': 'Finance Controller',
                    'department': departments['Finance'],
                }
            ],
            stages=[
                {
                    'name': 'Primary org admin',
                    'sequence': 1,
                    'mode': ApprovalStageMode.ALL,
                    'fallback_type': ApprovalFallbackType.NONE,
                    'fallback_employee': None,
                    'approvers': [
                        {
                            'approver_type': ApprovalApproverType.PRIMARY_ORG_ADMIN,
                            'approver_employee': None,
                        }
                    ],
                },
            ],
        )
        return {
            'leave_default': leave_default,
            'on_duty_default': on_duty_default,
            'regularization_default': regularization_default,
            'payroll_processing_default': payroll_processing_default,
            'salary_revision_default': salary_revision_default,
            'template_change_default': template_change_default,
            'finance': finance,
        }

    def _upsert_workflow(self, *, organisation, actor, name, description, is_default, default_request_kind, rules, stages):
        workflow, _ = ApprovalWorkflow.objects.get_or_create(
            organisation=organisation,
            name=name,
            defaults={
                'description': description,
                'is_default': is_default,
                'default_request_kind': default_request_kind,
                'created_by': actor,
                'is_active': True,
            },
        )
        workflow.description = description
        workflow.is_default = is_default
        workflow.default_request_kind = default_request_kind if is_default else None
        workflow.is_active = True
        if workflow.created_by_id is None:
            workflow.created_by = actor
        workflow.save()
        if workflow.is_default and workflow.default_request_kind:
            ApprovalWorkflow.objects.filter(
                organisation=organisation,
                is_default=True,
                default_request_kind=workflow.default_request_kind,
            ).exclude(id=workflow.id).update(is_default=False, default_request_kind=None)

        keep_rule_ids = []
        for payload in rules:
            rule, _ = ApprovalWorkflowRule.objects.get_or_create(
                workflow=workflow,
                name=payload['name'],
                request_kind=payload['request_kind'],
                defaults={'priority': payload.get('priority', 100)},
            )
            rule.priority = payload.get('priority', 100)
            rule.is_active = True
            rule.department = payload.get('department')
            rule.office_location = payload.get('office_location')
            rule.specific_employee = payload.get('specific_employee')
            rule.employment_type = payload.get('employment_type', '')
            rule.designation = payload.get('designation', '')
            rule.leave_type = payload.get('leave_type')
            rule.save()
            keep_rule_ids.append(rule.id)
        workflow.rules.exclude(id__in=keep_rule_ids).delete()

        keep_stage_ids = []
        for stage_payload in stages:
            stage, _ = ApprovalStage.objects.get_or_create(
                workflow=workflow,
                sequence=stage_payload['sequence'],
                defaults={'name': stage_payload['name']},
            )
            stage.name = stage_payload['name']
            stage.mode = stage_payload['mode']
            stage.fallback_type = stage_payload['fallback_type']
            stage.fallback_employee = stage_payload['fallback_employee']
            stage.save()
            keep_stage_ids.append(stage.id)

            keep_approver_ids = []
            for approver_payload in stage_payload['approvers']:
                approver, _ = ApprovalStageApprover.objects.get_or_create(
                    stage=stage,
                    approver_type=approver_payload['approver_type'],
                    approver_employee=approver_payload.get('approver_employee'),
                )
                approver.approver_type = approver_payload['approver_type']
                approver.approver_employee = approver_payload.get('approver_employee')
                approver.save()
                keep_approver_ids.append(approver.id)
            stage.approvers.exclude(id__in=keep_approver_ids).delete()

        workflow.stages.exclude(id__in=keep_stage_ids).delete()
        return workflow

    def _ensure_leave_setup(self, organisation, actor, *, departments, locations, employees):
        financial_cycle = LeaveCycle.objects.filter(organisation=organisation, name='FY Leave Cycle').first()
        financial_cycle = upsert_leave_cycle(
            organisation,
            actor=actor,
            cycle=financial_cycle,
            name='FY Leave Cycle',
            cycle_type=LeaveCycleType.FINANCIAL_YEAR,
            start_month=4,
            start_day=1,
            is_default=True,
            is_active=True,
        )
        calendar_cycle = LeaveCycle.objects.filter(organisation=organisation, name='Calendar Leave Cycle').first()
        upsert_leave_cycle(
            organisation,
            actor=actor,
            cycle=calendar_cycle,
            name='Calendar Leave Cycle',
            cycle_type=LeaveCycleType.CALENDAR_YEAR,
            start_month=1,
            start_day=1,
            is_default=False,
            is_active=True,
        )

        general_plan = LeavePlan.objects.filter(organisation=organisation, name='General Staff Leave Plan').first()
        general_fields = {
            'leave_cycle': financial_cycle,
            'name': 'General Staff Leave Plan',
            'description': 'Default leave plan for most teams.',
            'is_default': True,
            'is_active': True,
            'priority': 100,
        }
        general_leave_types = [
            {
                'code': 'CL',
                'name': 'Casual Leave',
                'description': 'General planned leave',
                'color': '#2563eb',
                'is_paid': True,
                'is_loss_of_pay': False,
                'annual_entitlement': '12.00',
                'credit_frequency': 'MONTHLY',
                'prorate_on_join': True,
                'carry_forward_mode': CarryForwardMode.CAPPED,
                'carry_forward_cap': '4.00',
                'max_balance': '12.00',
                'allows_half_day': True,
                'requires_attachment': False,
                'min_notice_days': 1,
                'allow_past_request': False,
                'allow_future_request': True,
                'is_active': True,
            },
            {
                'code': 'SL',
                'name': 'Sick Leave',
                'description': 'Sickness and medical leave',
                'color': '#dc2626',
                'is_paid': True,
                'is_loss_of_pay': False,
                'annual_entitlement': '8.00',
                'credit_frequency': 'YEARLY',
                'prorate_on_join': True,
                'carry_forward_mode': CarryForwardMode.NONE,
                'max_balance': '8.00',
                'allows_half_day': True,
                'requires_attachment': False,
                'min_notice_days': 0,
                'allow_past_request': True,
                'allow_future_request': True,
                'is_active': True,
            },
            {
                'code': 'LOP',
                'name': 'Loss of Pay',
                'description': 'Unpaid leave when balance is insufficient.',
                'color': '#7c3aed',
                'is_paid': False,
                'is_loss_of_pay': True,
                'annual_entitlement': '0.00',
                'credit_frequency': 'MANUAL',
                'prorate_on_join': False,
                'carry_forward_mode': CarryForwardMode.NONE,
                'allows_half_day': True,
                'requires_attachment': False,
                'min_notice_days': 0,
                'allow_past_request': True,
                'allow_future_request': True,
                'is_active': True,
            },
        ]
        general_rules = [
            {
                'name': 'Default workforce rule',
                'priority': 100,
                'is_active': True,
            }
        ]
        if general_plan is None:
            general_plan = create_leave_plan(
                organisation,
                actor=actor,
                leave_types=general_leave_types,
                rules=general_rules,
                **general_fields,
            )
        else:
            general_leave_types = self._attach_leave_type_ids(general_plan, general_leave_types)
            general_rules = self._attach_leave_rule_ids(general_plan, general_rules)
            general_plan = update_leave_plan(
                general_plan,
                actor=actor,
                leave_types=general_leave_types,
                rules=general_rules,
                **general_fields,
            )

        engineering_plan = LeavePlan.objects.filter(organisation=organisation, name='Engineering Flex Leave Plan').first()
        engineering_fields = {
            'leave_cycle': financial_cycle,
            'name': 'Engineering Flex Leave Plan',
            'description': 'Higher earned leave entitlement for engineering teams.',
            'is_default': False,
            'is_active': True,
            'priority': 50,
        }
        engineering_leave_types = [
            {
                'code': 'EL',
                'name': 'Earned Leave',
                'description': 'Engineering earned leave',
                'color': '#0f766e',
                'is_paid': True,
                'is_loss_of_pay': False,
                'annual_entitlement': '18.00',
                'credit_frequency': 'MONTHLY',
                'prorate_on_join': True,
                'carry_forward_mode': CarryForwardMode.CAPPED,
                'carry_forward_cap': '10.00',
                'max_balance': '24.00',
                'allows_half_day': True,
                'requires_attachment': False,
                'min_notice_days': 2,
                'allow_past_request': False,
                'allow_future_request': True,
                'is_active': True,
            }
        ]
        engineering_rules = [
            {
                'name': 'Engineering teams',
                'priority': 10,
                'is_active': True,
                'department': departments['Platform Engineering'],
            }
        ]
        if engineering_plan is None:
            engineering_plan = create_leave_plan(
                organisation,
                actor=actor,
                leave_types=engineering_leave_types,
                rules=engineering_rules,
                **engineering_fields,
            )
        else:
            engineering_leave_types = self._attach_leave_type_ids(engineering_plan, engineering_leave_types)
            engineering_rules = self._attach_leave_rule_ids(engineering_plan, engineering_rules)
            engineering_plan = update_leave_plan(
                engineering_plan,
                actor=actor,
                leave_types=engineering_leave_types,
                rules=engineering_rules,
                **engineering_fields,
            )

        assignment, _ = LeavePlanEmployeeAssignment.objects.get_or_create(
            employee=employees['ananya'],
            defaults={'leave_plan': engineering_plan},
        )
        if assignment.leave_plan_id != engineering_plan.id:
            assignment.leave_plan = engineering_plan
            assignment.save(update_fields=['leave_plan', 'modified_at'])

        default_policy = OnDutyPolicy.objects.filter(organisation=organisation, name='Field Visit / Client Meeting').first()
        default_policy = upsert_on_duty_policy(
            organisation,
            actor=actor,
            policy=default_policy,
            name='Field Visit / Client Meeting',
            description='Default on-duty policy for client meetings and field travel.',
            is_default=True,
            is_active=True,
            allow_half_day=True,
            allow_time_range=True,
            requires_attachment=False,
            min_notice_days=0,
            allow_past_request=True,
            allow_future_request=True,
        )
        warehouse_policy = OnDutyPolicy.objects.filter(organisation=organisation, name='Warehouse Dispatch Support').first()
        upsert_on_duty_policy(
            organisation,
            actor=actor,
            policy=warehouse_policy,
            name='Warehouse Dispatch Support',
            description='Used for warehouse and dispatch support assignments.',
            is_default=False,
            is_active=True,
            allow_half_day=True,
            allow_time_range=False,
            requires_attachment=False,
            min_notice_days=0,
            allow_past_request=True,
            allow_future_request=True,
        )
        return {
            'general_plan': general_plan,
            'engineering_plan': engineering_plan,
            'default_policy': default_policy,
        }

    def _attach_leave_type_ids(self, leave_plan, leave_types):
        existing = {leave_type.code: leave_type for leave_type in leave_plan.leave_types.all()}
        payloads = []
        for payload in leave_types:
            item = {**payload}
            current = existing.get(item['code'])
            if current:
                item['id'] = current.id
            payloads.append(item)
        return payloads

    def _attach_leave_rule_ids(self, leave_plan, rules):
        existing = {rule.name: rule for rule in leave_plan.rules.all()}
        payloads = []
        for payload in rules:
            item = {**payload}
            current = existing.get(item['name'])
            if current:
                item['id'] = current.id
            payloads.append(item)
        return payloads

    def _ensure_document_stage(self, actor, *, employees):
        self._ensure_document_request_state(employees['onboarding'], 'AADHAAR_CARD', EmployeeDocumentRequestStatus.REQUESTED, actor)
        self._ensure_document_request_state(employees['onboarding'], 'PAN_CARD', EmployeeDocumentRequestStatus.REQUESTED, actor)
        self._ensure_document_request_state(employees['pending'], 'AADHAAR_CARD', EmployeeDocumentRequestStatus.VERIFIED, actor)
        self._ensure_document_request_state(employees['pending'], 'PAN_CARD', EmployeeDocumentRequestStatus.SUBMITTED, actor)
        self._ensure_document_request_state(employees['pending'], 'CANCELLED_CHEQUE', EmployeeDocumentRequestStatus.WAIVED, actor)
        self._ensure_document_request_state(employees['pending'], 'BACKGROUND_CHECK_CONSENT', EmployeeDocumentRequestStatus.VERIFIED, actor)

        document_type_ids = list(OnboardingDocumentType.objects.filter(code__in=['ADDRESS_PROOF', 'PASSPORT_PHOTO']).values_list('id', flat=True))
        assign_document_requests(employees['priya'], document_type_ids, actor=actor)
        self._ensure_document_request_state(employees['priya'], 'ADDRESS_PROOF', EmployeeDocumentRequestStatus.SUBMITTED, actor)
        self._ensure_document_request_state(
            employees['priya'],
            'PASSPORT_PHOTO',
            EmployeeDocumentRequestStatus.REJECTED,
            actor,
            rejection_note='Seeded rejection for the review queue.',
        )

    def _ensure_document_request_state(self, employee, document_code, status, actor, rejection_note=''):
        document_type = OnboardingDocumentType.objects.get(code=document_code)
        request, _ = EmployeeDocumentRequest.objects.get_or_create(
            employee=employee,
            document_type_ref=document_type,
            defaults={
                'requested_by': actor,
                'is_required': True,
                'status': EmployeeDocumentRequestStatus.REQUESTED,
            },
        )
        request.requested_by = actor
        request.is_required = True
        request.status = status
        request.rejection_note = rejection_note if status == EmployeeDocumentRequestStatus.REJECTED else ''
        request.latest_uploaded_at = timezone.now() if status in [
            EmployeeDocumentRequestStatus.SUBMITTED,
            EmployeeDocumentRequestStatus.VERIFIED,
            EmployeeDocumentRequestStatus.REJECTED,
        ] else None
        request.verified_by = actor if status == EmployeeDocumentRequestStatus.VERIFIED else None
        request.verified_at = timezone.now() if status == EmployeeDocumentRequestStatus.VERIFIED else None
        request.waived_by = actor if status == EmployeeDocumentRequestStatus.WAIVED else None
        request.save()

        if status in [
            EmployeeDocumentRequestStatus.SUBMITTED,
            EmployeeDocumentRequestStatus.VERIFIED,
            EmployeeDocumentRequestStatus.REJECTED,
        ]:
            document, _ = Document.objects.get_or_create(
                employee=employee,
                document_request=request,
                version=1,
                defaults={
                    'document_type': document_code,
                    'file_key': f'seed/{employee.organisation.slug}/{employee.user.email}/{document_code.lower()}.pdf',
                    'file_name': f'{document_code.lower()}.pdf',
                    'file_size': 1024,
                    'mime_type': 'application/pdf',
                    'uploaded_by': employee.user,
                },
            )
            document.document_type = document_code
            document.file_key = f'seed/{employee.organisation.slug}/{employee.user.email}/{document_code.lower()}.pdf'
            document.file_name = f'{document_code.lower()}.pdf'
            document.file_size = 1024
            document.mime_type = 'application/pdf'
            document.uploaded_by = employee.user
            document.file_hash = hash_token(f'{employee.id}:{document_code}:{status}')
            document.metadata = {'seeded': True, 'request_status': status}
            document.reviewed_by = actor if status in [EmployeeDocumentRequestStatus.VERIFIED, EmployeeDocumentRequestStatus.REJECTED] else None
            document.reviewed_at = timezone.now() if status in [EmployeeDocumentRequestStatus.VERIFIED, EmployeeDocumentRequestStatus.REJECTED] else None
            document.status = {
                EmployeeDocumentRequestStatus.SUBMITTED: DocumentStatus.PENDING,
                EmployeeDocumentRequestStatus.VERIFIED: DocumentStatus.VERIFIED,
                EmployeeDocumentRequestStatus.REJECTED: DocumentStatus.REJECTED,
            }[status]
            document.save()

    def _ensure_holiday_calendars(self, organisation, actor, locations):
        current_year = timezone.localdate().year
        published = HolidayCalendar.objects.filter(organisation=organisation, year=current_year, name='FY Operations Calendar').first()
        published_holidays = [
            {
                'name': 'Ugadi',
                'holiday_date': date(current_year, 4, 9),
                'classification': HolidayClassification.PUBLIC,
                'session': DaySession.FULL_DAY,
                'description': 'Regional new year holiday.',
            },
            {
                'name': 'Founders Day',
                'holiday_date': date(current_year, 4, 24),
                'classification': HolidayClassification.COMPANY,
                'session': DaySession.FULL_DAY,
                'description': 'Organisation-wide annual celebration.',
            },
            {
                'name': 'Labour Day',
                'holiday_date': date(current_year, 5, 1),
                'classification': HolidayClassification.PUBLIC,
                'session': DaySession.FULL_DAY,
                'description': 'National holiday.',
            },
        ]
        location_ids = [location.id for location in locations.values() if location.is_active]
        if published is None:
            published = create_holiday_calendar(
                organisation,
                actor=actor,
                holidays=published_holidays,
                location_ids=location_ids,
                name='FY Operations Calendar',
                year=current_year,
                description='Published holiday calendar for the current year.',
                is_default=True,
            )
        else:
            published_holidays = self._attach_holiday_ids(published, published_holidays)
            published = update_holiday_calendar(
                published,
                actor=actor,
                holidays=published_holidays,
                location_ids=location_ids,
                name='FY Operations Calendar',
                year=current_year,
                description='Published holiday calendar for the current year.',
                is_default=True,
                status=HolidayCalendarStatus.DRAFT,
            )
        if published.status != HolidayCalendarStatus.PUBLISHED:
            publish_holiday_calendar(published, actor=actor)

        next_year = current_year + 1
        draft = HolidayCalendar.objects.filter(organisation=organisation, year=next_year, name='Draft Holiday Calendar').first()
        draft_holidays = [
            {
                'name': 'New Year Day',
                'holiday_date': date(next_year, 1, 1),
                'classification': HolidayClassification.PUBLIC,
                'session': DaySession.FULL_DAY,
                'description': 'Seeded preview calendar.',
            }
        ]
        if draft is None:
            create_holiday_calendar(
                organisation,
                actor=actor,
                holidays=draft_holidays,
                location_ids=location_ids,
                name='Draft Holiday Calendar',
                year=next_year,
                description='Unpublished draft for the next year.',
                is_default=False,
            )
        else:
            draft_holidays = self._attach_holiday_ids(draft, draft_holidays)
            update_holiday_calendar(
                draft,
                actor=actor,
                holidays=draft_holidays,
                location_ids=location_ids,
                name='Draft Holiday Calendar',
                year=next_year,
                description='Unpublished draft for the next year.',
                is_default=False,
                status=HolidayCalendarStatus.DRAFT,
            )

    def _attach_holiday_ids(self, calendar_obj, holidays):
        existing = {
            (holiday.name, holiday.holiday_date): holiday
            for holiday in calendar_obj.holidays.all()
        }
        payloads = []
        for payload in holidays:
            item = {**payload}
            current = existing.get((item['name'], item['holiday_date']))
            if current:
                item['id'] = current.id
            payloads.append(item)
        return payloads

    def _ensure_notices(self, organisation, actor, *, departments, locations, employees):
        published = Notice.objects.filter(organisation=organisation, title='Performance calibration window opens Monday').first()
        if published is None:
            published = create_notice(
                organisation,
                actor=actor,
                title='Performance calibration window opens Monday',
                body='Managers should complete mid-year calibration by 15 April. Seeded notice for the employee dashboard.',
                audience_type=NoticeAudienceType.ALL_EMPLOYEES,
                status=NoticeStatus.DRAFT,
            )
        else:
            update_notice(
                published,
                actor=actor,
                title='Performance calibration window opens Monday',
                body='Managers should complete mid-year calibration by 15 April. Seeded notice for the employee dashboard.',
                audience_type=NoticeAudienceType.ALL_EMPLOYEES,
                status=NoticeStatus.DRAFT,
            )
        if published.status != NoticeStatus.PUBLISHED:
            publish_notice(published, actor=actor)

        scheduled = Notice.objects.filter(organisation=organisation, title='Bengaluru HQ access maintenance').first()
        if scheduled is None:
            create_notice(
                organisation,
                actor=actor,
                title='Bengaluru HQ access maintenance',
                body='Badge access will switch to the backup controller on Saturday evening.',
                audience_type=NoticeAudienceType.OFFICE_LOCATIONS,
                office_location_ids=[locations['Bengaluru HQ'].id],
                status=NoticeStatus.SCHEDULED,
                scheduled_for=timezone.now() + timedelta(days=2),
            )
        else:
            update_notice(
                scheduled,
                actor=actor,
                title='Bengaluru HQ access maintenance',
                body='Badge access will switch to the backup controller on Saturday evening.',
                audience_type=NoticeAudienceType.OFFICE_LOCATIONS,
                office_location_ids=[locations['Bengaluru HQ'].id],
                status=NoticeStatus.SCHEDULED,
                scheduled_for=timezone.now() + timedelta(days=2),
            )

        draft = Notice.objects.filter(organisation=organisation, title='Finance policy refresh draft').first()
        if draft is None:
            create_notice(
                organisation,
                actor=actor,
                title='Finance policy refresh draft',
                body='Draft notice reserved for targeted finance users.',
                audience_type=NoticeAudienceType.DEPARTMENTS,
                department_ids=[departments['Finance'].id],
                status=NoticeStatus.DRAFT,
            )
        else:
            update_notice(
                draft,
                actor=actor,
                title='Finance policy refresh draft',
                body='Draft notice reserved for targeted finance users.',
                audience_type=NoticeAudienceType.DEPARTMENTS,
                department_ids=[departments['Finance'].id],
                status=NoticeStatus.DRAFT,
            )

    def _ensure_timeoff_activity(self, organisation, actor, *, employees, leave_context, workflow_context):
        sick_leave = leave_context['general_plan'].leave_types.get(code='SL')
        earned_leave = leave_context['engineering_plan'].leave_types.get(code='EL')
        on_duty_policy = leave_context['default_policy']

        pending_manager = self._ensure_leave_request(
            employee=employees['ananya'],
            leave_type=earned_leave,
            start_date=date(2026, 4, 18),
            end_date=date(2026, 4, 18),
            start_session=DaySession.FIRST_HALF,
            end_session=DaySession.FIRST_HALF,
            reason='[seed] Pending manager approval leave request',
            state='PENDING_STAGE_ONE',
            actor=employees['ananya'].user,
        )
        pending_admin = self._ensure_leave_request(
            employee=employees['rohan'],
            leave_type=sick_leave,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 4, 22),
            start_session=DaySession.FULL_DAY,
            end_session=DaySession.FULL_DAY,
            reason='[seed] Pending org admin leave request',
            state='PENDING_STAGE_TWO',
            actor=employees['rohan'].user,
        )
        approved = self._ensure_leave_request(
            employee=employees['rohan'],
            leave_type=sick_leave,
            start_date=date(2026, 3, 12),
            end_date=date(2026, 3, 12),
            start_session=DaySession.FULL_DAY,
            end_session=DaySession.FULL_DAY,
            reason='[seed] Fully approved leave request',
            state='APPROVED',
            actor=employees['rohan'].user,
        )
        rejected = self._ensure_leave_request(
            employee=employees['ananya'],
            leave_type=sick_leave,
            start_date=date(2026, 5, 5),
            end_date=date(2026, 5, 6),
            start_session=DaySession.FULL_DAY,
            end_session=DaySession.FULL_DAY,
            reason='[seed] Rejected leave request',
            state='REJECTED',
            actor=employees['ananya'].user,
        )
        withdrawn = self._ensure_leave_request(
            employee=employees['rohan'],
            leave_type=sick_leave,
            start_date=date(2026, 5, 20),
            end_date=date(2026, 5, 20),
            start_session=DaySession.SECOND_HALF,
            end_session=DaySession.SECOND_HALF,
            reason='[seed] Withdrawn leave request',
            state='WITHDRAWN',
            actor=employees['rohan'].user,
        )

        self._ensure_on_duty_request(
            employee=employees['ananya'],
            policy=on_duty_policy,
            start_date=date(2026, 4, 14),
            end_date=date(2026, 4, 14),
            duration_type=OnDutyDurationType.TIME_RANGE,
            start_time=timezone.datetime(2026, 4, 14, 10, 0).time(),
            end_time=timezone.datetime(2026, 4, 14, 15, 30).time(),
            purpose='[seed] Pending on-duty approval',
            destination='Customer site',
            state='PENDING_STAGE_ONE',
            actor=employees['ananya'].user,
        )
        self._ensure_on_duty_request(
            employee=employees['rohan'],
            policy=on_duty_policy,
            start_date=date(2026, 3, 26),
            end_date=date(2026, 3, 26),
            duration_type=OnDutyDurationType.FULL_DAY,
            start_time=None,
            end_time=None,
            purpose='[seed] Approved on-duty request',
            destination='Bank visit',
            state='APPROVED',
            actor=employees['rohan'].user,
        )
        self._ensure_on_duty_request(
            employee=employees['ananya'],
            policy=on_duty_policy,
            start_date=date(2026, 5, 9),
            end_date=date(2026, 5, 9),
            duration_type=OnDutyDurationType.FIRST_HALF,
            start_time=None,
            end_time=None,
            purpose='[seed] Rejected on-duty request',
            destination='Vendor onboarding',
            state='REJECTED',
            actor=employees['ananya'].user,
        )
        self._ensure_on_duty_request(
            employee=employees['rohan'],
            policy=on_duty_policy,
            start_date=date(2026, 5, 13),
            end_date=date(2026, 5, 13),
            duration_type=OnDutyDurationType.SECOND_HALF,
            start_time=None,
            end_time=None,
            purpose='[seed] Withdrawn on-duty request',
            destination='Government office visit',
            state='WITHDRAWN',
            actor=employees['rohan'].user,
        )

        return {
            'pending_manager': pending_manager,
            'pending_admin': pending_admin,
            'approved': approved,
            'rejected': rejected,
            'withdrawn': withdrawn,
            'workflow': workflow_context['leave_default'],
        }

    def _ensure_leave_request(self, *, employee, leave_type, start_date, end_date, start_session, end_session, reason, state, actor):
        request = LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        ).first()
        if request is None:
            request = create_leave_request(
                employee,
                leave_type,
                start_date,
                end_date,
                start_session,
                end_session,
                reason=reason,
                actor=actor,
            )
        approval_run = self._ensure_approval_run(request, ApprovalRequestKind.LEAVE, employee, actor, leave_type=leave_type)
        self._stage_approval_run(approval_run, state, actor)
        if state == 'WITHDRAWN' and request.status not in ['WITHDRAWN', 'CANCELLED']:
            withdraw_leave_request(request, actor=actor)
        return request

    def _ensure_on_duty_request(
        self,
        *,
        employee,
        policy,
        start_date,
        end_date,
        duration_type,
        start_time,
        end_time,
        purpose,
        destination,
        state,
        actor,
    ):
        request = OnDutyRequest.objects.filter(
            employee=employee,
            policy=policy,
            start_date=start_date,
            end_date=end_date,
            purpose=purpose,
        ).first()
        if request is None:
            request = create_on_duty_request(
                employee,
                policy,
                start_date,
                end_date,
                duration_type,
                purpose,
                destination=destination,
                start_time=start_time,
                end_time=end_time,
                actor=actor,
            )
        approval_run = self._ensure_approval_run(request, ApprovalRequestKind.ON_DUTY, employee, actor)
        self._stage_approval_run(approval_run, state, actor)
        if state == 'WITHDRAWN' and request.status not in ['WITHDRAWN', 'CANCELLED']:
            withdraw_on_duty_request(request, actor=actor)
        return request

    def _ensure_approval_run(self, subject, request_kind, requester, actor, leave_type=None):
        content_type = ContentType.objects.get_for_model(subject.__class__)
        approval_run = ApprovalRun.objects.filter(
            content_type=content_type,
            object_id=subject.id,
        ).first()
        if approval_run is None:
            from apps.approvals.services import create_approval_run

            approval_run = create_approval_run(
                subject,
                request_kind,
                requester=requester,
                actor=actor,
                leave_type=leave_type,
                subject_label=f'Seed {request_kind} {requester.user.email}',
            )
        return approval_run

    def _stage_approval_run(self, approval_run, desired_state, actor):
        approval_run.refresh_from_db()
        pending_actions = approval_run.actions.filter(status='PENDING').select_related('approver_user').order_by('created_at')
        if desired_state == 'PENDING_STAGE_ONE':
            return approval_run
        if desired_state == 'PENDING_STAGE_TWO':
            if approval_run.current_stage_sequence == 1:
                first_action = pending_actions.first()
                if first_action:
                    approve_action(first_action, actor=first_action.approver_user, comment='Seeded manager approval')
            return approval_run
        if desired_state == 'APPROVED':
            while approval_run.status == 'PENDING':
                action = approval_run.actions.filter(status='PENDING').order_by('created_at').first()
                if action is None:
                    break
                approve_action(action, actor=action.approver_user, comment='Seeded approval')
                approval_run.refresh_from_db()
            return approval_run
        if desired_state == 'REJECTED':
            action = pending_actions.first()
            if action and action.status == 'PENDING':
                reject_action(action, actor=action.approver_user, comment='Seeded rejection')
            return approval_run
        if desired_state == 'WITHDRAWN':
            return approval_run
        return approval_run

    def _seed_secondary_organisations(self, control_tower, shared_admin, groups):
        contexts = {}
        for config in SECONDARY_ORGANISATIONS:
            organisation = self._ensure_secondary_organisation(config, control_tower)
            if config['state_kind'] != 'PENDING_PAYMENT':
                ensure_org_admin_membership(
                    organisation,
                    shared_admin,
                    invited_by=control_tower,
                    status=OrganisationMembershipStatus.ACTIVE,
                )
                shared_admin.groups.add(groups['org_admin'])
                if organisation.primary_admin_user_id != shared_admin.id:
                    set_primary_admin(organisation, shared_admin, control_tower)
            contexts[config['slug']] = organisation

        expired_org = contexts['zenith-field-services-pvt-ltd']
        expired_locations = {location.name: location for location in expired_org.locations.filter(is_active=True)}
        expired_departments = self._ensure_secondary_departments(expired_org)
        rohan_user = User.objects.get(email=self._email_for_primary_org('rohan.mehta'), account_type=AccountType.WORKFORCE)
        rohan_expired = self._ensure_employee_record(
            organisation=expired_org,
            user=rohan_user,
            employee_code='ZFS001',
            department=expired_departments['Finance'],
            office_location=expired_locations['Billing Address'],
            designation='Regional Finance Analyst',
            employment_type=EmploymentType.FULL_TIME,
            date_of_joining=date(2025, 8, 4),
            status=EmployeeStatus.ACTIVE,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
            groups=[groups['employee']],
        )
        rohan_expired.reporting_to = rohan_expired
        rohan_expired.save(update_fields=['reporting_to', 'modified_at'])
        return contexts

    def _ensure_secondary_organisation(self, config, control_tower):
        organisation = Organisation.objects.filter(slug=config['slug']).first() or Organisation.objects.filter(name=config['name']).first()
        if organisation is None:
            organisation = create_organisation(
                name=config['name'],
                licence_count=config['licence_count'],
                created_by=control_tower,
                pan_number=config['pan_number'],
                addresses=config['addresses'],
                primary_admin=self._bootstrap_admin_for_config(config),
                country_code=config['country_code'],
                currency=config['currency'],
                entity_type=config['entity_type'],
            )
        else:
            organisation = update_organisation_profile(
                organisation,
                actor=control_tower,
                name=config['name'],
                pan_number=config['pan_number'],
                country_code=config['country_code'],
                currency=config['currency'],
                entity_type=config['entity_type'],
            )
            if organisation.licence_count != config['licence_count']:
                organisation = update_licence_count(
                    organisation,
                    config['licence_count'],
                    changed_by=control_tower,
                    note=f"Seed sync licence allocation for {config['name']}",
                )
        upsert_bootstrap_admin(organisation, actor=control_tower, **self._bootstrap_admin_for_config(config))
        self._ensure_addresses(organisation, control_tower, config['addresses'], auto_create_location=True)
        if config['state_kind'] == 'PENDING_PAYMENT':
            self._ensure_named_licence_batch(
                organisation,
                control_tower,
                quantity=config['licence_count'],
                start_date=date.today(),
                end_date=self._next_year(date.today()),
                note='Seed pending payment batch',
                paid=False,
            )
            return organisation

        if organisation.status == OrganisationStatus.PENDING:
            organisation = transition_organisation_state(
                organisation,
                OrganisationStatus.PAID,
                control_tower,
                note=f'Seed payment confirmed for {config["name"]}',
            )
        batch_note = 'Seed expired org batch' if config['state_kind'] == 'LICENCE_EXPIRED' else 'Seed active org batch'
        if config['state_kind'] == 'LICENCE_EXPIRED':
            self._ensure_named_licence_batch(
                organisation,
                control_tower,
                quantity=config['licence_count'],
                start_date=date.today() - timedelta(days=540),
                end_date=date.today() - timedelta(days=30),
                note=batch_note,
                paid=True,
            )
        else:
            self._ensure_named_licence_batch(
                organisation,
                control_tower,
                quantity=config['licence_count'],
                start_date=date.today(),
                end_date=self._next_year(date.today()),
                note=batch_note,
                paid=True,
            )
        if organisation.status in [OrganisationStatus.PAID, OrganisationStatus.SUSPENDED]:
            organisation = transition_organisation_state(
                organisation,
                OrganisationStatus.ACTIVE,
                control_tower,
                note=f'Seed activation for {config["name"]}',
            )
        if config['state_kind'] == 'SUSPENDED' and organisation.status != OrganisationStatus.SUSPENDED:
            organisation = transition_organisation_state(
                organisation,
                OrganisationStatus.SUSPENDED,
                control_tower,
                note='Seed suspended organisation scenario',
            )
        return organisation

    def _ensure_secondary_departments(self, organisation):
        departments = {}
        for name, description in [
            ('Finance', 'Finance and operations'),
            ('Field Operations', 'Field execution teams'),
        ]:
            department, _ = Department.objects.get_or_create(
                organisation=organisation,
                name=name,
                defaults={'description': description},
            )
            department.description = description
            department.is_active = True
            department.save(update_fields=['description', 'is_active', 'modified_at'])
            departments[name] = department
        return departments

    def _print_seed_summary(self, control_tower, primary_admin, shared_admin, primary_context, secondary_context):
        primary_org = primary_admin.organisation_memberships.filter(is_org_admin=True).first().organisation
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seed Credentials'))
        self.stdout.write(f'  Control Tower login   : {control_tower.email}  -> /ct/login (password not shown)')
        self.stdout.write(f'  Org admin login       : {primary_admin.email}  -> /auth/login (password not shown)')
        self.stdout.write(f'  Shared CT workforce   : {shared_admin.email}  -> /auth/login (password not shown)')
        self.stdout.write(f'  Employee login        : {primary_context["employees"]["rohan"].user.email}  -> /auth/login (password not shown)')
        self.stdout.write(f'  Onboarding login      : {primary_context["employees"]["onboarding"].user.email}  -> /auth/login (password not shown)')
        self.stdout.write(f'  Pending join login    : {primary_context["employees"]["pending"].user.email}  -> /auth/login (password not shown)')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seed Scenarios'))
        self.stdout.write(f'  Primary organisation  : {primary_org.name} (active, fully configured)')
        self.stdout.write('  Workforce twin        : same email works in both /ct/login and /auth/login')
        self.stdout.write('  Multi-org admin       : shared CT workforce user can switch active/suspended/licence-expired orgs')
        self.stdout.write('  Multi-org employee    : Rohan Mehta has employee workspaces in the primary and licence-expired orgs')
        self.stdout.write('  Employee stages       : invited, onboarding invited, pending, active, resigned, retired, terminated')
        self.stdout.write('  Approval stages       : pending manager, pending org admin, approved, rejected, withdrawn')
        self.stdout.write('  Document stages       : requested, submitted, verified, rejected, waived')
        self.stdout.write(f'  Secondary organisations: {", ".join(org.name for org in secondary_context.values())}')
