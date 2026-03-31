import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q


class EmploymentType(models.TextChoices):
    FULL_TIME = 'FULL_TIME', 'Full Time'
    PART_TIME = 'PART_TIME', 'Part Time'
    CONTRACT = 'CONTRACT', 'Contract'
    INTERN = 'INTERN', 'Intern'


class EmployeeStatus(models.TextChoices):
    INVITED = 'INVITED', 'Invited'
    PENDING = 'PENDING', 'Pending'
    ACTIVE = 'ACTIVE', 'Active'
    RESIGNED = 'RESIGNED', 'Resigned'
    RETIRED = 'RETIRED', 'Retired'
    TERMINATED = 'TERMINATED', 'Terminated'


class GenderChoice(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'
    OTHER = 'OTHER', 'Other'
    PREFER_NOT_TO_SAY = 'PREFER_NOT_TO_SAY', 'Prefer Not To Say'


class MaritalStatus(models.TextChoices):
    SINGLE = 'SINGLE', 'Single'
    MARRIED = 'MARRIED', 'Married'
    DIVORCED = 'DIVORCED', 'Divorced'
    WIDOWED = 'WIDOWED', 'Widowed'


class GovernmentIdType(models.TextChoices):
    PAN = 'PAN', 'PAN'
    AADHAAR = 'AADHAAR', 'Aadhaar'


class GovernmentIdStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    VERIFIED = 'VERIFIED', 'Verified'
    REJECTED = 'REJECTED', 'Rejected'


class BankAccountType(models.TextChoices):
    SAVINGS = 'SAVINGS', 'Savings'
    CURRENT = 'CURRENT', 'Current'
    SALARY = 'SALARY', 'Salary'


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='employees',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_records',
    )
    employee_code = models.CharField(max_length=20, null=True, blank=True)
    department = models.ForeignKey(
        'departments.Department',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employees',
    )
    office_location = models.ForeignKey(
        'locations.OfficeLocation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employees',
    )
    designation = models.CharField(max_length=255, blank=True)
    reporting_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='direct_reports',
    )
    date_of_joining = models.DateField(null=True, blank=True)
    date_of_exit = models.DateField(null=True, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    status = models.CharField(
        max_length=20,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.INVITED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employees'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'employee_code'],
                condition=Q(employee_code__isnull=False) & ~Q(employee_code=''),
                name='unique_employee_code_per_org_when_present',
            ),
        ]

    def __str__(self):
        return f'{self.employee_code or "UNASSIGNED"} - {self.user.full_name}'


class EmployeeProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GenderChoice.choices, blank=True)
    marital_status = models.CharField(max_length=20, choices=MaritalStatus.choices, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    phone_personal = models.CharField(max_length=20, blank=True)
    phone_emergency = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_relation = models.CharField(max_length=100, blank=True)
    address_line1 = models.TextField(blank=True)
    address_line2 = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employee_profiles'

    def __str__(self):
        return f'Profile({self.employee.employee_code or self.employee.user.email})'


class EducationRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='education_records',
    )
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True)
    start_year = models.PositiveIntegerField(null=True, blank=True)
    end_year = models.PositiveIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'education_records'
        ordering = ['-end_year', '-start_year']

    def __str__(self):
        return f'{self.degree} at {self.institution}'


class EmployeeGovernmentId(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='government_ids',
    )
    id_type = models.CharField(max_length=20, choices=GovernmentIdType.choices)
    identifier_encrypted = models.TextField(blank=True)
    masked_identifier = models.CharField(max_length=32, blank=True)
    name_on_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=GovernmentIdStatus.choices,
        default=GovernmentIdStatus.PENDING,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employee_government_ids'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'id_type'],
                name='unique_employee_government_id_type',
            ),
        ]


class EmployeeBankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='bank_accounts',
    )
    account_holder_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255, blank=True)
    account_number_encrypted = models.TextField(blank=True)
    masked_account_number = models.CharField(max_length=32, blank=True)
    ifsc_encrypted = models.TextField(blank=True)
    masked_ifsc = models.CharField(max_length=24, blank=True)
    account_type = models.CharField(
        max_length=20,
        choices=BankAccountType.choices,
        default=BankAccountType.SALARY,
    )
    branch_name = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employee_bank_accounts'
        ordering = ['-is_primary', '-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['employee'],
                condition=Q(is_primary=True),
                name='unique_primary_bank_account_per_employee',
            ),
        ]
