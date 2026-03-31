import os
from datetime import date

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import AccountType, User, UserRole
from apps.accounts.workspaces import sync_user_role
from apps.departments.models import Department
from apps.employees.models import (
    EducationRecord,
    Employee,
    EmployeeProfile,
    EmployeeStatus,
    EmploymentType,
    GovernmentIdType,
)
from apps.employees.services import (
    create_bank_account,
    update_bank_account,
    update_education_record,
    upsert_government_id,
)
from apps.locations.models import OfficeLocation
from apps.organisations.models import (
    Organisation,
    OrganisationMembershipStatus,
    OrganisationOnboardingStage,
    OrganisationStatus,
)
from apps.organisations.services import (
    create_organisation,
    ensure_org_admin_membership,
    mark_employee_invited,
    mark_master_data_configured,
    set_primary_admin,
    transition_organisation_state,
    update_licence_count,
)


DEFAULT_ORGANISATION = {
    'name': 'Acme Workforce Pvt Ltd',
    'licence_count': 10,
    'email': 'hello@acmeworkforce.com',
    'phone': '+91 9876543210',
    'address': '42 Residency Road, Bengaluru, Karnataka 560025',
    'country_code': 'IN',
    'currency': 'INR',
}

DEFAULT_ORG_ADMIN = {
    'email': 'admin@acmeworkforce.com',
    'password': 'Admin@12345',
    'first_name': 'Aditi',
    'last_name': 'Rao',
}

DEFAULT_EMPLOYEE_PASSWORD = 'Employee@12345'

DEMO_LOCATIONS = [
    {
        'name': 'Bengaluru HQ',
        'address': '42 Residency Road',
        'city': 'Bengaluru',
        'state': 'Karnataka',
        'country': 'India',
        'pincode': '560025',
    },
    {
        'name': 'Mumbai Branch',
        'address': '18 Nariman Point',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'country': 'India',
        'pincode': '400021',
    },
]

DEMO_DEPARTMENTS = [
    {
        'name': 'People Operations',
        'description': 'Owns HR operations, onboarding, and compliance.',
    },
    {
        'name': 'Finance',
        'description': 'Manages payroll readiness, reimbursements, and vendor controls.',
    },
    {
        'name': 'Engineering',
        'description': 'Builds internal systems and product operations tooling.',
    },
]

DEMO_EMPLOYEES = [
    {
        'email': 'priya.sharma@acmeworkforce.com',
        'first_name': 'Priya',
        'last_name': 'Sharma',
        'employee_code': 'EMP001',
        'designation': 'HR Operations Manager',
        'employment_type': EmploymentType.FULL_TIME,
        'date_of_joining': date(2024, 6, 3),
        'department': 'People Operations',
        'location': 'Bengaluru HQ',
        'profile': {
            'date_of_birth': date(1994, 8, 21),
            'gender': 'FEMALE',
            'marital_status': 'MARRIED',
            'nationality': 'Indian',
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
        'education': {
            'degree': 'MBA',
            'institution': 'Christ University',
            'field_of_study': 'Human Resources',
            'start_year': 2014,
            'end_year': 2016,
            'grade': 'A',
            'is_current': False,
        },
        'government_ids': [
            {
                'id_type': GovernmentIdType.PAN,
                'identifier': 'ABCDE1234F',
                'name_on_id': 'Priya Sharma',
            },
            {
                'id_type': GovernmentIdType.AADHAAR,
                'identifier': '123412341234',
                'name_on_id': 'Priya Sharma',
            },
        ],
        'bank_account': {
            'account_holder_name': 'Priya Sharma',
            'bank_name': 'HDFC Bank',
            'account_number': '123456789012',
            'ifsc': 'HDFC0001234',
            'account_type': 'SALARY',
            'branch_name': 'HSR Layout',
            'is_primary': True,
        },
    },
    {
        'email': 'rohan.mehta@acmeworkforce.com',
        'first_name': 'Rohan',
        'last_name': 'Mehta',
        'employee_code': 'EMP002',
        'designation': 'Finance Analyst',
        'employment_type': EmploymentType.FULL_TIME,
        'date_of_joining': date(2024, 9, 16),
        'department': 'Finance',
        'location': 'Mumbai Branch',
    },
    {
        'email': 'ananya.iyer@acmeworkforce.com',
        'first_name': 'Ananya',
        'last_name': 'Iyer',
        'employee_code': 'EMP003',
        'designation': 'Software Engineer',
        'employment_type': EmploymentType.FULL_TIME,
        'date_of_joining': date(2025, 1, 6),
        'department': 'Engineering',
        'location': 'Bengaluru HQ',
    },
]


class Command(BaseCommand):
    help = 'Creates the initial Control Tower user and seeds a paid, active demo organisation.'

    def handle(self, *args, **options):
        control_tower_password = os.environ.get('CONTROL_TOWER_PASSWORD')
        if not control_tower_password:
            raise CommandError(
                'CONTROL_TOWER_PASSWORD environment variable is not set. '
                'Set it before running this command.'
            )

        licence_count = self._get_int_env('SEED_ORGANISATION_LICENCE_COUNT', DEFAULT_ORGANISATION['licence_count'])
        if licence_count < len(DEMO_EMPLOYEES):
            raise CommandError(
                f'SEED_ORGANISATION_LICENCE_COUNT must be at least {len(DEMO_EMPLOYEES)} '
                'to cover the seeded demo employees.'
            )

        with transaction.atomic():
            groups = self._ensure_groups()
            control_tower = self._ensure_control_tower_user(control_tower_password, groups['control_tower'])
            organisation = self._ensure_organisation(control_tower, licence_count)
            organisation = self._ensure_paid(organisation, control_tower)
            org_admin = self._ensure_org_admin(organisation, control_tower, groups['org_admin'])
            organisation = self._ensure_primary_admin(organisation, org_admin, control_tower)
            organisation = self._ensure_active(organisation, control_tower)
            locations = self._ensure_locations(organisation)
            departments = self._ensure_departments(organisation)
            organisation = self._ensure_master_data_stage(organisation, org_admin)
            employees = self._ensure_employees(organisation, departments, locations, groups['employee'])
            self._ensure_employee_stage(organisation, org_admin, employees)

        self.stdout.write(self.style.SUCCESS('Seeded Control Tower account and demo organisation data.'))

    def _get_int_env(self, key, default):
        raw_value = os.environ.get(key, str(default))
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise CommandError(f'{key} must be an integer.') from exc
        if value < 1:
            raise CommandError(f'{key} must be at least 1.')
        return value

    def _ensure_groups(self):
        groups = {}
        for group_name in ['control_tower', 'org_admin', 'employee']:
            group, created = Group.objects.get_or_create(name=group_name)
            groups[group_name] = group
            if created:
                self.stdout.write(f'  Created group: {group_name}')
        return groups

    def _ensure_control_tower_user(self, password, group):
        email = os.environ.get('CONTROL_TOWER_EMAIL', 'admin@calrisal.com')
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

    def _ensure_organisation(self, control_tower, licence_count):
        organisation_defaults = {
            'name': os.environ.get('SEED_ORGANISATION_NAME', DEFAULT_ORGANISATION['name']),
            'email': os.environ.get('SEED_ORGANISATION_EMAIL', DEFAULT_ORGANISATION['email']),
            'phone': os.environ.get('SEED_ORGANISATION_PHONE', DEFAULT_ORGANISATION['phone']),
            'address': os.environ.get('SEED_ORGANISATION_ADDRESS', DEFAULT_ORGANISATION['address']),
            'country_code': os.environ.get('SEED_ORGANISATION_COUNTRY_CODE', DEFAULT_ORGANISATION['country_code']),
            'currency': os.environ.get('SEED_ORGANISATION_CURRENCY', DEFAULT_ORGANISATION['currency']),
        }
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
                address=organisation_defaults['address'],
                phone=organisation_defaults['phone'],
                email=organisation_defaults['email'],
                country_code=organisation_defaults['country_code'],
                currency=organisation_defaults['currency'],
            )
            self.stdout.write(self.style.SUCCESS(f"Demo organisation created: {organisation_defaults['name']}"))
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
                organisation.save()
                self.stdout.write(self.style.WARNING(f"Demo organisation {organisation.name} already exists, updated seed state."))

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
        return organisation

    def _ensure_paid(self, organisation, control_tower):
        if organisation.status == OrganisationStatus.PENDING:
            organisation = transition_organisation_state(
                organisation,
                OrganisationStatus.PAID,
                control_tower,
                note='Seed payment marked as received',
            )
        return organisation

    def _ensure_org_admin(self, organisation, actor, group):
        password = os.environ.get('SEED_ORG_ADMIN_PASSWORD', DEFAULT_ORG_ADMIN['password'])
        email = os.environ.get('SEED_ORG_ADMIN_EMAIL', DEFAULT_ORG_ADMIN['email'])
        first_name = os.environ.get('SEED_ORG_ADMIN_FIRST_NAME', DEFAULT_ORG_ADMIN['first_name'])
        last_name = os.environ.get('SEED_ORG_ADMIN_LAST_NAME', DEFAULT_ORG_ADMIN['last_name'])

        user, created = User.objects.get_or_create(
            email=email,
            account_type=AccountType.WORKFORCE,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': UserRole.ORG_ADMIN,
                'is_active': True,
            },
        )

        user.first_name = first_name
        user.last_name = last_name
        user.account_type = AccountType.WORKFORCE
        user.organisation = None
        user.is_active = True
        user.set_password(password)
        user.save()
        user.groups.add(group)
        ensure_org_admin_membership(
            organisation,
            user,
            invited_by=actor,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        sync_user_role(user)

        if created:
            self.stdout.write(self.style.SUCCESS(f'Organisation admin created: {email}'))
        else:
            self.stdout.write(self.style.WARNING(f'Organisation admin {email} already exists, updated seed state.'))
        return user

    def _ensure_primary_admin(self, organisation, org_admin, control_tower):
        if organisation.primary_admin_user_id != org_admin.id:
            organisation = set_primary_admin(organisation, org_admin, control_tower)
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

    def _ensure_locations(self, organisation):
        locations = {}
        for payload in DEMO_LOCATIONS:
            location, created = OfficeLocation.objects.get_or_create(
                organisation=organisation,
                name=payload['name'],
                defaults=payload,
            )
            if not created:
                changed = False
                for field, value in payload.items():
                    if getattr(location, field) != value:
                        setattr(location, field, value)
                        changed = True
                if not location.is_active:
                    location.is_active = True
                    changed = True
                if changed:
                    location.save()
            locations[location.name] = location
        return locations

    def _ensure_departments(self, organisation):
        departments = {}
        for payload in DEMO_DEPARTMENTS:
            department, created = Department.objects.get_or_create(
                organisation=organisation,
                name=payload['name'],
                defaults=payload,
            )
            if not created:
                changed = False
                for field, value in payload.items():
                    if getattr(department, field) != value:
                        setattr(department, field, value)
                        changed = True
                if not department.is_active:
                    department.is_active = True
                    changed = True
                if changed:
                    department.save()
            departments[department.name] = department
        return departments

    def _ensure_master_data_stage(self, organisation, actor):
        organisation.refresh_from_db()
        if organisation.onboarding_stage != OrganisationOnboardingStage.EMPLOYEES_INVITED:
            organisation = mark_master_data_configured(organisation, actor)
        return organisation

    def _ensure_employees(self, organisation, departments, locations, group):
        password = os.environ.get('SEED_EMPLOYEE_PASSWORD', DEFAULT_EMPLOYEE_PASSWORD)
        employees = []

        for payload in DEMO_EMPLOYEES:
            user, created = User.objects.get_or_create(
                email=payload['email'],
                account_type=AccountType.WORKFORCE,
                defaults={
                    'first_name': payload['first_name'],
                    'last_name': payload['last_name'],
                    'role': UserRole.EMPLOYEE,
                    'is_active': True,
                },
            )

            user.first_name = payload['first_name']
            user.last_name = payload['last_name']
            user.account_type = AccountType.WORKFORCE
            user.organisation = None
            user.is_active = True
            if not user.organisation_memberships.filter(is_org_admin=True).exists():
                user.set_password(password)
            user.save()
            user.groups.add(group)

            conflicting_employee = (
                Employee.objects.filter(
                    organisation=organisation,
                    employee_code=payload['employee_code'],
                )
                .exclude(user=user)
                .first()
            )
            if conflicting_employee:
                raise CommandError(
                    f"Employee code {payload['employee_code']} is already used by {conflicting_employee.user.email}."
                )

            employee, _ = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'organisation': organisation,
                    'employee_code': payload['employee_code'],
                },
            )
            if employee.organisation_id != organisation.id:
                raise CommandError(f"Employee record for {payload['email']} belongs to another organisation.")

            employee.organisation = organisation
            employee.employee_code = payload['employee_code']
            employee.department = departments[payload['department']]
            employee.office_location = locations[payload['location']]
            employee.designation = payload['designation']
            employee.employment_type = payload['employment_type']
            employee.date_of_joining = payload['date_of_joining']
            employee.status = EmployeeStatus.ACTIVE
            employee.save()
            sync_user_role(user)

            EmployeeProfile.objects.get_or_create(employee=employee)
            self._seed_employee_details(employee, payload)
            employees.append(employee)

        if len(employees) >= 3:
            employees[1].reporting_to = employees[0]
            employees[1].save(update_fields=['reporting_to', 'updated_at'])
            employees[2].reporting_to = employees[0]
            employees[2].save(update_fields=['reporting_to', 'updated_at'])

        return employees

    def _seed_employee_details(self, employee, payload):
        profile_payload = payload.get('profile')
        if profile_payload:
            profile, _ = EmployeeProfile.objects.get_or_create(employee=employee)
            for field, value in profile_payload.items():
                setattr(profile, field, value)
            profile.save()

        education_payload = payload.get('education')
        if education_payload:
            education_record = employee.education_records.filter(
                degree=education_payload['degree'],
                institution=education_payload['institution'],
            ).first()
            if education_record is None:
                EducationRecord.objects.create(employee=employee, **education_payload)
            else:
                update_education_record(education_record, actor=employee.user, **education_payload)

        for government_id in payload.get('government_ids', []):
            upsert_government_id(
                employee,
                government_id['id_type'],
                government_id['identifier'],
                actor=employee.user,
                name_on_id=government_id['name_on_id'],
            )

        bank_payload = payload.get('bank_account')
        if bank_payload:
            account = employee.bank_accounts.filter(is_primary=True).first()
            if account is None:
                create_bank_account(employee, actor=employee.user, **bank_payload)
            else:
                update_bank_account(account, actor=employee.user, **bank_payload)

    def _ensure_employee_stage(self, organisation, actor, employees):
        organisation.refresh_from_db()
        if employees and organisation.onboarding_stage != OrganisationOnboardingStage.EMPLOYEES_INVITED:
            mark_employee_invited(organisation, actor, employees[0])
