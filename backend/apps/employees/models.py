from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import AuditedBaseModel


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


class BloodTypeChoice(models.TextChoices):
    A_POSITIVE = 'A_POSITIVE', 'A+'
    A_NEGATIVE = 'A_NEGATIVE', 'A-'
    B_POSITIVE = 'B_POSITIVE', 'B+'
    B_NEGATIVE = 'B_NEGATIVE', 'B-'
    AB_POSITIVE = 'AB_POSITIVE', 'AB+'
    AB_NEGATIVE = 'AB_NEGATIVE', 'AB-'
    O_POSITIVE = 'O_POSITIVE', 'O+'
    O_NEGATIVE = 'O_NEGATIVE', 'O-'
    UNKNOWN = 'UNKNOWN', 'Unknown'


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


class EmployeeOnboardingStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    BASIC_DETAILS_PENDING = 'BASIC_DETAILS_PENDING', 'Basic Details Pending'
    DOCUMENTS_PENDING = 'DOCUMENTS_PENDING', 'Documents Pending'
    COMPLETE = 'COMPLETE', 'Complete'


class OffboardingProcessStatus(models.TextChoices):
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class OffboardingTaskStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    WAIVED = 'WAIVED', 'Waived'


class OffboardingTaskOwner(models.TextChoices):
    ORG_ADMIN = 'ORG_ADMIN', 'Org Admin'
    MANAGER = 'MANAGER', 'Manager'
    EMPLOYEE = 'EMPLOYEE', 'Employee'
    PAYROLL = 'PAYROLL', 'Payroll'
    IT = 'IT', 'IT'


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def soft_delete(self):
        return self.update(is_deleted=True, deleted_at=timezone.now())


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore[misc]
    def get_queryset(self):
        return super().get_queryset().active()


class SoftDeleteModel(AuditedBaseModel):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def soft_delete(self, save=True):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if save:
            self.save(update_fields=['is_deleted', 'deleted_at'])


class Employee(SoftDeleteModel):
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
    designation_ref = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employees_with_designation',
        help_text='Reference to a Designation master entry',
    )
    reporting_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='direct_reports',
    )
    date_of_joining = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date on which the employee completes their probation period.',
    )
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
    onboarding_status = models.CharField(
        max_length=32,
        choices=EmployeeOnboardingStatus.choices,
        default=EmployeeOnboardingStatus.NOT_STARTED,
    )
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    leave_approval_workflow = models.ForeignKey(
        'approvals.ApprovalWorkflow',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_leave_employees',
    )
    on_duty_approval_workflow = models.ForeignKey(
        'approvals.ApprovalWorkflow',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_on_duty_employees',
    )
    attendance_regularization_approval_workflow = models.ForeignKey(
        'approvals.ApprovalWorkflow',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_attendance_regularization_employees',
    )
    expense_approval_workflow = models.ForeignKey(
        'approvals.ApprovalWorkflow',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_expense_employees',
    )

    class Meta:
        db_table = 'employees'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'employee_code'],
                condition=Q(employee_code__isnull=False) & ~Q(employee_code='') & Q(is_deleted=False),
                name='unique_employee_code_per_org_when_present',
            ),
        ]
        indexes = [
            models.Index(fields=['organisation', 'status', 'is_deleted']),
            models.Index(fields=['user', 'organisation', 'is_deleted']),
            models.Index(
                fields=['organisation', 'status', 'date_of_joining'],
                name='employee_org_status_doj_idx',
            ),
            models.Index(
                fields=['organisation', 'reporting_to', 'status'],
                name='emp_org_mgr_status_idx',
            ),
            models.Index(
                fields=['organisation', 'department', 'status'],
                name='emp_org_dept_status_idx',
            ),
        ]

    def __str__(self):
        return f'{self.employee_code or "UNASSIGNED"} - {self.user.full_name}'


class EmployeeOffboardingProcess(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='employee_offboarding_processes',
    )
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='offboarding_process',
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='initiated_offboarding_processes',
    )
    status = models.CharField(
        max_length=20,
        choices=OffboardingProcessStatus.choices,
        default=OffboardingProcessStatus.IN_PROGRESS,
    )
    exit_status = models.CharField(max_length=20, choices=EmployeeStatus.choices)
    date_of_exit = models.DateField()
    exit_reason = models.CharField(max_length=255, blank=True)
    exit_notes = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'employee_offboarding_processes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['employee', 'status']),
        ]


class EmployeeOffboardingTask(AuditedBaseModel):
    process = models.ForeignKey(
        EmployeeOffboardingProcess,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    code = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.CharField(max_length=20, choices=OffboardingTaskOwner.choices, default=OffboardingTaskOwner.ORG_ADMIN)
    status = models.CharField(
        max_length=20,
        choices=OffboardingTaskStatus.choices,
        default=OffboardingTaskStatus.PENDING,
    )
    note = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_required = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='completed_offboarding_tasks',
    )

    class Meta:
        db_table = 'employee_offboarding_tasks'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['process', 'code'], name='unique_offboarding_task_code_per_process'),
        ]


class EmployeeProfile(AuditedBaseModel):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GenderChoice.choices, blank=True)
    marital_status = models.CharField(max_length=20, choices=MaritalStatus.choices, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    blood_type = models.CharField(max_length=20, choices=BloodTypeChoice.choices, blank=True)
    phone_personal = models.CharField(max_length=20, blank=True)
    phone_emergency = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_relation = models.CharField(max_length=100, blank=True)
    address_line1 = models.TextField(blank=True)
    address_line2 = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    state_code = models.CharField(max_length=16, blank=True, default='')
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=2, blank=True, default='')
    pincode = models.CharField(max_length=20, blank=True)
    uan_number = models.CharField(max_length=12, blank=True)
    esic_ip_number = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'employee_profiles'

    def __str__(self):
        return f'Profile({self.employee.employee_code or self.employee.user.email})'


class EducationRecord(SoftDeleteModel):
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

    class Meta:
        db_table = 'education_records'
        ordering = ['-end_year', '-start_year']
        indexes = [
            models.Index(fields=['employee', 'is_deleted']),
        ]

    def __str__(self):
        return f'{self.degree} at {self.institution}'


class EmployeeGovernmentId(AuditedBaseModel):
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

    class Meta:
        db_table = 'employee_government_ids'
        ordering = ['-modified_at']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'id_type'],
                name='unique_employee_government_id_type',
            ),
        ]


class EmployeeBankAccount(SoftDeleteModel):
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

    class Meta:
        db_table = 'employee_bank_accounts'
        ordering = ['-is_primary', '-modified_at']
        constraints = [
            models.UniqueConstraint(
                fields=['employee'],
                condition=Q(is_primary=True) & Q(is_deleted=False),
                name='unique_primary_bank_account_per_employee',
            ),
        ]
        indexes = [
            models.Index(fields=['employee', 'is_deleted']),
        ]


class FamilyRelationChoice(models.TextChoices):
    SPOUSE = 'SPOUSE', 'Spouse'
    FATHER = 'FATHER', 'Father'
    MOTHER = 'MOTHER', 'Mother'
    SON = 'SON', 'Son'
    DAUGHTER = 'DAUGHTER', 'Daughter'
    BROTHER = 'BROTHER', 'Brother'
    SISTER = 'SISTER', 'Sister'
    OTHER = 'OTHER', 'Other'


class EmployeeFamilyMember(SoftDeleteModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='family_members',
    )
    full_name = models.CharField(max_length=255)
    relation = models.CharField(max_length=20, choices=FamilyRelationChoice.choices, default=FamilyRelationChoice.OTHER)
    date_of_birth = models.DateField(null=True, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    is_dependent = models.BooleanField(default=False)

    class Meta:
        db_table = 'employee_family_members'
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['employee', 'is_deleted']),
        ]


class EmployeeEmergencyContact(SoftDeleteModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='emergency_contacts',
    )
    full_name = models.CharField(max_length=255)
    relation = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    alternate_phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'employee_emergency_contacts'
        ordering = ['-is_primary', 'full_name']
        constraints = [
            models.UniqueConstraint(
                fields=['employee'],
                condition=Q(is_primary=True) & Q(is_deleted=False),
                name='unique_primary_emergency_contact_per_employee',
            ),
        ]
        indexes = [
            models.Index(fields=['employee', 'is_deleted']),
        ]


class CustomFieldType(models.TextChoices):
    TEXT = 'TEXT', 'Text'
    NUMBER = 'NUMBER', 'Number'
    DATE = 'DATE', 'Date'
    DROPDOWN = 'DROPDOWN', 'Dropdown'
    CHECKBOX = 'CHECKBOX', 'Checkbox'
    EMAIL = 'EMAIL', 'Email'
    PHONE = 'PHONE', 'Phone'


class CustomFieldPlacement(models.TextChoices):
    PERSONAL = 'PERSONAL', 'Personal Info'
    WORK = 'WORK', 'Work Info'
    FAMILY = 'FAMILY', 'Family Info'
    DOCUMENTS = 'DOCUMENTS', 'Documents'
    BANK = 'BANK', 'Bank Info'
    CUSTOM = 'CUSTOM', 'Custom'


class CustomFieldDefinition(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='custom_field_definitions',
    )
    name = models.CharField(max_length=100)
    field_key = models.SlugField(
        max_length=50,
        help_text='API-safe key for this field (e.g., shirt_size, uniform_size)',
    )
    field_type = models.CharField(
        max_length=20,
        choices=CustomFieldType.choices,
        default=CustomFieldType.TEXT,
    )
    placement = models.CharField(
        max_length=20,
        choices=CustomFieldPlacement.choices,
        default=CustomFieldPlacement.CUSTOM,
    )
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    dropdown_options = models.JSONField(
        default=list,
        blank=True,
        help_text='List of options for DROPDOWN type fields',
    )
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'custom_field_definitions'
        ordering = ['placement', 'display_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'field_key'],
                name='unique_custom_field_key_per_org',
            ),
        ]
        indexes = [
            models.Index(fields=['organisation', 'is_active']),
            models.Index(fields=['organisation', 'placement']),
        ]

    def __str__(self):
        return f'{self.name} ({self.field_key})'


class CustomFieldValue(SoftDeleteModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='custom_field_values',
    )
    field_definition = models.ForeignKey(
        CustomFieldDefinition,
        on_delete=models.CASCADE,
        related_name='values',
    )
    value_text = models.TextField(blank=True)
    value_number = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )
    value_date = models.DateField(null=True, blank=True)
    value_boolean = models.BooleanField(default=False)

    class Meta:
        db_table = 'custom_field_values'
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'field_definition'],
                name='unique_custom_field_value_per_employee',
            ),
        ]
        indexes = [
            models.Index(fields=['employee', 'is_deleted']),
        ]

    def __str__(self):
        return f'{self.field_definition.name}: {self.get_display_value()}'

    def get_display_value(self):
        if self.field_definition.field_type == CustomFieldType.TEXT:
            return self.value_text
        elif self.field_definition.field_type == CustomFieldType.NUMBER:
            return str(self.value_number) if self.value_number else ''
        elif self.field_definition.field_type == CustomFieldType.DATE:
            return str(self.value_date) if self.value_date else ''
        elif self.field_definition.field_type == CustomFieldType.DROPDOWN:
            return self.value_text
        elif self.field_definition.field_type == CustomFieldType.CHECKBOX:
            return 'Yes' if self.value_boolean else 'No'
        elif self.field_definition.field_type == CustomFieldType.EMAIL:
            return self.value_text
        elif self.field_definition.field_type == CustomFieldType.PHONE:
            return self.value_text
        return self.value_text


class Designation(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='designations',
    )
    name = models.CharField(max_length=255)
    level = models.PositiveIntegerField(
        default=1,
        help_text='Hierarchy level (1 = highest, higher numbers = lower rank)',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'designations'
        ordering = ['level', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'name'],
                name='unique_designation_name_per_org',
            ),
        ]
        indexes = [
            models.Index(fields=['organisation', 'is_active']),
            models.Index(fields=['organisation', 'level']),
        ]

    def __str__(self):
        return self.name


class ExitInterviewQuestionType(models.TextChoices):
    RATING = 'RATING', 'Rating Scale'
    TEXT = 'TEXT', 'Free Text'
    MULTIPLE_CHOICE = 'MULTIPLE_CHOICE', 'Multiple Choice'
    YES_NO = 'YES_NO', 'Yes/No'


class ExitInterviewTemplate(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='exit_interview_templates',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'exit_interview_templates'
        unique_together = [['organisation', 'name']]
        ordering = ['name']

    def __str__(self):
        return f"{self.organisation.name} - {self.name}"


class ExitInterviewQuestion(AuditedBaseModel):
    template = models.ForeignKey(
        ExitInterviewTemplate,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=ExitInterviewQuestionType.choices,
        default=ExitInterviewQuestionType.TEXT,
    )
    options = models.JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = 'exit_interview_questions'
        ordering = ['template', 'order']

    def __str__(self):
        return f"{self.template.name} - Q{self.order}: {self.question_text[:50]}"


class ExitInterview(AuditedBaseModel):
    OFFBOARDING_STAGES = [
        ('NOTICE_PERIOD', 'Notice Period'),
        ('LAST_DAY', 'Last Day'),
        ('EXIT', 'Exit'),
        ('AFTER_EXIT', 'After Exit'),
    ]

    process = models.ForeignKey(
        EmployeeOffboardingProcess,
        on_delete=models.CASCADE,
        related_name='exit_interviews',
    )
    template = models.ForeignKey(
        ExitInterviewTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='exit_interviews',
    )
    stage = models.CharField(max_length=20, choices=OFFBOARDING_STAGES, default='EXIT')
    scheduled_date = models.DateTimeField(null=True, blank=True)
    conducted_date = models.DateTimeField(null=True, blank=True)
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conducted_exit_interviews',
    )
    notes = models.TextField(blank=True)
    overall_rating = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'exit_interviews'
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"Exit Interview - {self.process.employee.full_name}"


class ExitInterviewResponse(AuditedBaseModel):
    exit_interview = models.ForeignKey(
        ExitInterview,
        on_delete=models.CASCADE,
        related_name='responses',
    )
    question = models.ForeignKey(
        ExitInterviewQuestion,
        on_delete=models.CASCADE,
        related_name='responses',
    )
    rating_value = models.PositiveSmallIntegerField(null=True, blank=True)
    text_value = models.TextField(blank=True)
    choice_value = models.CharField(max_length=255, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'exit_interview_responses'
        unique_together = [['exit_interview', 'question']]

    def __str__(self):
        return f"Response to Q{self.question.order} for {self.exit_interview}"


class EmployeeTransferEvent(AuditedBaseModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EFFECTIVE', 'Effective'),
        ('CANCELLED', 'Cancelled'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='transfer_events',
    )
    from_department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_from',
    )
    to_department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_to',
    )
    from_location = models.ForeignKey(
        'locations.OfficeLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_from',
    )
    to_location = models.ForeignKey(
        'locations.OfficeLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_to',
    )
    from_designation = models.ForeignKey(
        'employees.Designation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_from',
    )
    to_designation = models.ForeignKey(
        'employees.Designation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_to',
    )
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_transfers',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_transfers',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'employee_transfer_events'
        ordering = ['-effective_date', '-created_at']

    def __str__(self):
        return f"Transfer: {self.employee} - {self.effective_date}"
    def handle_approval_status_change(self, new_status, rejection_reason=''):
        self.status = new_status
        if rejection_reason:
            self.notes = rejection_reason
        self.save(update_fields=['status', 'notes', 'modified_at'])


class EmployeePromotionEvent(AuditedBaseModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EFFECTIVE', 'Effective'),
        ('CANCELLED', 'Cancelled'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='promotion_events',
    )
    from_designation = models.ForeignKey(
        'employees.Designation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions_from',
        help_text='Previous designation before promotion'
    )
    to_designation = models.ForeignKey(
        'employees.Designation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions_to',
        help_text='New designation after promotion'
    )
    revised_compensation_assignment = models.ForeignKey(
        'payroll.CompensationAssignment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_promotions',
    )
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_promotions',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_promotions',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'employee_promotion_events'
        ordering = ['-effective_date', '-created_at']

    def __str__(self):
        return f"Promotion: {self.employee} - {self.effective_date}"

    def handle_approval_status_change(self, new_status, rejection_reason=''):
        self.status = new_status
        if rejection_reason:
            self.notes = rejection_reason
        self.save(update_fields=['status', 'notes', 'modified_at'])
