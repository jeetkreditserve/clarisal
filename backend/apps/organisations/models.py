from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import AuditedBaseModel


class OrganisationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Payment'
    PAID = 'PAID', 'Paid'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class OrganisationBillingStatus(models.TextChoices):
    PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
    PAID = 'PAID', 'Paid'


class OrganisationAccessState(models.TextChoices):
    PROVISIONING = 'PROVISIONING', 'Provisioning'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class OrganisationOnboardingStage(models.TextChoices):
    ORG_CREATED = 'ORG_CREATED', 'Organisation Created'
    LICENCES_ASSIGNED = 'LICENCES_ASSIGNED', 'Licences Assigned'
    PAYMENT_CONFIRMED = 'PAYMENT_CONFIRMED', 'Payment Confirmed'
    ADMIN_INVITED = 'ADMIN_INVITED', 'Admin Invited'
    ADMIN_ACTIVATED = 'ADMIN_ACTIVATED', 'Admin Activated'
    MASTER_DATA_CONFIGURED = 'MASTER_DATA_CONFIGURED', 'Master Data Configured'
    EMPLOYEES_INVITED = 'EMPLOYEES_INVITED', 'Employees Invited'


class LicenceLedgerReason(models.TextChoices):
    OPENING_BALANCE = 'OPENING_BALANCE', 'Opening Balance'
    PURCHASE = 'PURCHASE', 'Purchase'
    ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
    CORRECTION = 'CORRECTION', 'Correction'


class LicenceBatchPaymentStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PAID = 'PAID', 'Paid'


class LicenceBatchLifecycleState(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PAID_PENDING_START = 'PAID_PENDING_START', 'Paid Pending Start'
    ACTIVE = 'ACTIVE', 'Active'
    EXPIRED = 'EXPIRED', 'Expired'


class OrganisationBillingProvider(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual'
    RAZORPAY = 'RAZORPAY', 'Razorpay'
    STRIPE = 'STRIPE', 'Stripe'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    REFUNDED = 'REFUNDED', 'Refunded'


class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ISSUED = 'ISSUED', 'Issued'
    PAID = 'PAID', 'Paid'
    VOID = 'VOID', 'Void'


class OrganisationBillingEventStatus(models.TextChoices):
    RECEIVED = 'RECEIVED', 'Received'
    PROCESSED = 'PROCESSED', 'Processed'
    IGNORED = 'IGNORED', 'Ignored'
    FAILED = 'FAILED', 'Failed'


class LifecycleEventType(models.TextChoices):
    ORGANISATION_CREATED = 'ORGANISATION_CREATED', 'Organisation Created'
    LICENCES_UPDATED = 'LICENCES_UPDATED', 'Licences Updated'
    PAYMENT_MARKED = 'PAYMENT_MARKED', 'Payment Marked'
    ADMIN_INVITED = 'ADMIN_INVITED', 'Admin Invited'
    ADMIN_ACTIVATED = 'ADMIN_ACTIVATED', 'Admin Activated'
    ACCESS_SUSPENDED = 'ACCESS_SUSPENDED', 'Access Suspended'
    ACCESS_RESTORED = 'ACCESS_RESTORED', 'Access Restored'
    MASTER_DATA_CONFIGURED = 'MASTER_DATA_CONFIGURED', 'Master Data Configured'
    EMPLOYEE_INVITED = 'EMPLOYEE_INVITED', 'Employee Invited'
    ACT_AS_STARTED = 'ACT_AS_STARTED', 'Act As Started'
    ACT_AS_REFRESHED = 'ACT_AS_REFRESHED', 'Act As Refreshed'
    ACT_AS_STOPPED = 'ACT_AS_STOPPED', 'Act As Stopped'


class OrganisationMembershipStatus(models.TextChoices):
    INVITED = 'INVITED', 'Invited'
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    REVOKED = 'REVOKED', 'Revoked'


class OrganisationAddressType(models.TextChoices):
    REGISTERED = 'REGISTERED', 'Registered'
    BILLING = 'BILLING', 'Billing'
    HEADQUARTERS = 'HEADQUARTERS', 'Headquarters'
    WAREHOUSE = 'WAREHOUSE', 'Warehouse'
    CUSTOM = 'CUSTOM', 'Custom'


class OrganisationEntityType(models.TextChoices):
    PRIVATE_LIMITED = 'PRIVATE_LIMITED', 'Private Limited Company'
    PUBLIC_LIMITED = 'PUBLIC_LIMITED', 'Public Limited Company'
    LIMITED_LIABILITY_PARTNERSHIP = 'LIMITED_LIABILITY_PARTNERSHIP', 'Limited Liability Partnership'
    PARTNERSHIP_FIRM = 'PARTNERSHIP_FIRM', 'Partnership Firm'
    SOLE_PROPRIETORSHIP = 'SOLE_PROPRIETORSHIP', 'Sole Proprietorship'
    ONE_PERSON_COMPANY = 'ONE_PERSON_COMPANY', 'One Person Company'
    SECTION_8_COMPANY = 'SECTION_8_COMPANY', 'Section 8 Company'
    TRUST = 'TRUST', 'Trust'
    SOCIETY = 'SOCIETY', 'Society'
    GOVERNMENT_BODY = 'GOVERNMENT_BODY', 'Government Body'
    OTHER = 'OTHER', 'Other'


class BootstrapAdminStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    INVITE_PENDING = 'INVITE_PENDING', 'Invite Pending'
    INVITE_ACCEPTED = 'INVITE_ACCEPTED', 'Invite Accepted'


class OrgAdminSetupStep(models.TextChoices):
    PROFILE = 'PROFILE', 'Organisation Profile'
    ADDRESSES = 'ADDRESSES', 'Addresses'
    LOCATIONS = 'LOCATIONS', 'Locations'
    DEPARTMENTS = 'DEPARTMENTS', 'Departments'
    HOLIDAYS = 'HOLIDAYS', 'Holiday Calendar'
    POLICIES = 'POLICIES', 'Policies And Approvals'
    EMPLOYEES = 'EMPLOYEES', 'Employees'


class OrganisationLegalIdentifierType(models.TextChoices):
    PAN = 'PAN', 'PAN'
    EIN = 'EIN', 'EIN'
    ABN = 'ABN', 'ABN'
    UEN = 'UEN', 'UEN'
    OTHER = 'OTHER', 'Other'


class OrganisationTaxRegistrationType(models.TextChoices):
    GSTIN = 'GSTIN', 'GSTIN'
    VAT = 'VAT', 'VAT'
    TRN = 'TRN', 'TRN'
    GST_HST = 'GST_HST', 'GST/HST'
    OTHER = 'OTHER', 'Other'


class OrganisationFeatureCode(models.TextChoices):
    ATTENDANCE = 'ATTENDANCE', 'Attendance'
    APPROVALS = 'APPROVALS', 'Approvals'
    BIOMETRICS = 'BIOMETRICS', 'Biometric Devices'
    NOTICES = 'NOTICES', 'Notices'
    PAYROLL = 'PAYROLL', 'Payroll'
    PERFORMANCE = 'PERFORMANCE', 'Performance'
    RECRUITMENT = 'RECRUITMENT', 'Recruitment'
    REPORTS = 'REPORTS', 'Reports'
    TIMEOFF = 'TIMEOFF', 'Leave and On-duty'


class TenantDataExportType(models.TextChoices):
    EMPLOYEES = 'EMPLOYEES', 'Employees'
    PAYSLIPS = 'PAYSLIPS', 'Payslips'
    LEAVE_HISTORY = 'LEAVE_HISTORY', 'Leave History'
    AUDIT_LOG = 'AUDIT_LOG', 'Audit Log'


class TenantDataExportStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class Organisation(AuditedBaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OrganisationStatus.choices,
        default=OrganisationStatus.PENDING,
    )
    billing_status = models.CharField(
        max_length=24,
        choices=OrganisationBillingStatus.choices,
        default=OrganisationBillingStatus.PENDING_PAYMENT,
    )
    access_state = models.CharField(
        max_length=20,
        choices=OrganisationAccessState.choices,
        default=OrganisationAccessState.PROVISIONING,
    )
    onboarding_stage = models.CharField(
        max_length=32,
        choices=OrganisationOnboardingStage.choices,
        default=OrganisationOnboardingStage.ORG_CREATED,
    )
    licence_count = models.PositiveIntegerField(default=0)
    country_code = models.CharField(max_length=2, default='IN')
    currency = models.CharField(max_length=3, default='INR')
    entity_type = models.CharField(
        max_length=40,
        choices=OrganisationEntityType.choices,
        default=OrganisationEntityType.PRIVATE_LIMITED,
    )
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    tan_number = models.CharField(max_length=10, null=True, blank=True)
    esi_branch_code = models.CharField(max_length=20, blank=True)
    billing_gateway = models.CharField(
        max_length=20,
        choices=OrganisationBillingProvider.choices,
        blank=True,
    )
    # P28 ADR hook: future org settings can add lwp_deduction_basis
    # (GROSS/BASIC). Current accepted default remains gross-pay basis.
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_organisations',
    )
    primary_admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='primary_admin_organisations',
    )
    paid_marked_at = models.DateTimeField(null=True, blank=True)
    paid_marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='paid_organisations',
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    admin_setup_started_at = models.DateTimeField(null=True, blank=True)
    admin_setup_current_step = models.CharField(
        max_length=24,
        choices=OrgAdminSetupStep.choices,
        default=OrgAdminSetupStep.PROFILE,
    )
    admin_setup_completed_at = models.DateTimeField(null=True, blank=True)
    admin_setup_completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='completed_org_admin_setups',
    )

    class Meta:
        db_table = 'organisations'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Organisation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.status})'


class OrganisationAddress(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='addresses',
    )
    address_type = models.CharField(
        max_length=24,
        choices=OrganisationAddressType.choices,
    )
    label = models.CharField(max_length=255, blank=True)
    line1 = models.TextField()
    line2 = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    state_code = models.CharField(max_length=16, blank=True, default='')
    country = models.CharField(max_length=100, default='India')
    country_code = models.CharField(max_length=2, default='IN')
    pincode = models.CharField(max_length=20)
    gstin = models.CharField(max_length=64, null=True, blank=True)
    tax_registration = models.ForeignKey(
        'OrganisationTaxRegistration',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='addresses',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'organisation_addresses'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'address_type'],
                condition=Q(address_type=OrganisationAddressType.REGISTERED, is_active=True),
                name='unique_active_registered_address_per_org',
            ),
            models.UniqueConstraint(
                fields=['organisation', 'address_type'],
                condition=Q(address_type=OrganisationAddressType.BILLING, is_active=True),
                name='unique_active_billing_address_per_org',
            ),
        ]

    def __str__(self):
        return f'{self.organisation.name} - {self.label or self.get_address_type_display()}'


class OrganisationBootstrapAdmin(AuditedBaseModel):
    organisation = models.OneToOneField(
        Organisation,
        on_delete=models.CASCADE,
        related_name='bootstrap_admin',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    person = models.ForeignKey(
        'accounts.Person',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bootstrap_admin_profiles',
    )
    email_address = models.ForeignKey(
        'accounts.EmailAddress',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bootstrap_admin_profiles',
    )
    phone_number = models.ForeignKey(
        'accounts.PhoneNumber',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bootstrap_admin_profiles',
    )
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20,
        choices=BootstrapAdminStatus.choices,
        default=BootstrapAdminStatus.DRAFT,
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bootstrap_admin_assignments',
    )
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'organisation_bootstrap_admins'

    def __str__(self):
        return f'{self.organisation.name} bootstrap admin <{self.email}>'


class OrganisationLegalIdentifier(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='legal_identifiers',
    )
    country_code = models.CharField(max_length=2, default='IN')
    identifier_type = models.CharField(
        max_length=20,
        choices=OrganisationLegalIdentifierType.choices,
    )
    identifier = models.CharField(max_length=64)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'organisation_legal_identifiers'
        constraints = [
            models.UniqueConstraint(
                fields=['country_code', 'identifier_type', 'identifier'],
                name='unique_legal_identifier_globally',
            ),
            models.UniqueConstraint(
                fields=['organisation', 'identifier_type'],
                condition=Q(is_primary=True),
                name='unique_primary_legal_identifier_per_org_type',
            ),
        ]

    def __str__(self):
        return f'{self.organisation.name} {self.identifier_type} {self.identifier}'


class OrganisationTaxRegistration(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='tax_registrations',
    )
    legal_identifier = models.ForeignKey(
        OrganisationLegalIdentifier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tax_registrations',
    )
    country_code = models.CharField(max_length=2, default='IN')
    registration_type = models.CharField(
        max_length=20,
        choices=OrganisationTaxRegistrationType.choices,
    )
    identifier = models.CharField(max_length=64)
    state_code = models.CharField(max_length=16, blank=True, default='')
    is_primary_billing = models.BooleanField(default=False)

    class Meta:
        db_table = 'organisation_tax_registrations'
        constraints = [
            models.UniqueConstraint(
                fields=['country_code', 'registration_type', 'identifier'],
                name='unique_tax_registration_globally',
            ),
            models.UniqueConstraint(
                fields=['organisation'],
                condition=Q(is_primary_billing=True),
                name='unique_primary_billing_tax_registration_per_org',
            ),
        ]

    def __str__(self):
        return f'{self.organisation.name} {self.registration_type} {self.identifier}'


class OrganisationStateTransition(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='state_transitions',
    )
    from_status = models.CharField(max_length=20, choices=OrganisationStatus.choices)
    to_status = models.CharField(max_length=20, choices=OrganisationStatus.choices)
    transitioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='org_transitions',
    )
    note = models.TextField(blank=True)

    class Meta:
        db_table = 'organisation_state_transitions'
        ordering = ['-created_at']


class OrganisationLicenceLedger(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='licence_ledger_entries',
    )
    delta = models.IntegerField()
    reason = models.CharField(max_length=24, choices=LicenceLedgerReason.choices)
    note = models.TextField(blank=True)
    effective_from = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='licence_ledger_entries',
    )
    class Meta:
        db_table = 'organisation_licence_ledger'
        ordering = ['-created_at']


class OrganisationLicenceBatch(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='licence_batches',
    )
    quantity = models.PositiveIntegerField()
    price_per_licence_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    billing_months = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_provider = models.CharField(
        max_length=20,
        choices=OrganisationBillingProvider.choices,
        default=OrganisationBillingProvider.MANUAL,
    )
    invoice_reference = models.CharField(max_length=255, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=LicenceBatchPaymentStatus.choices,
        default=LicenceBatchPaymentStatus.DRAFT,
    )
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_licence_batches',
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='paid_licence_batches',
    )
    paid_at = models.DateField(null=True, blank=True)
    gateway_subscription_id = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'organisation_licence_batches'
        ordering = ['-created_at']

    @property
    def lifecycle_state(self):
        today = timezone.localdate()
        if self.payment_status == LicenceBatchPaymentStatus.DRAFT:
            return LicenceBatchLifecycleState.DRAFT
        if today < self.start_date:
            return LicenceBatchLifecycleState.PAID_PENDING_START
        if self.start_date <= today <= self.end_date:
            return LicenceBatchLifecycleState.ACTIVE
        return LicenceBatchLifecycleState.EXPIRED


class Payment(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    licence_batch = models.ForeignKey(
        OrganisationLicenceBatch,
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    gateway = models.CharField(max_length=20, choices=OrganisationBillingProvider.choices)
    gateway_order_id = models.CharField(max_length=200, unique=True)
    gateway_payment_id = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    idempotency_key = models.CharField(max_length=160, unique=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    gateway_options = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'organisation_payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['licence_batch', 'status']),
        ]

    def __str__(self):
        return f'{self.gateway_order_id} ({self.status})'


class Invoice(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='invoices',
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name='invoice',
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED)
    storage_key = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'organisation_invoices'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
        ]

    def __str__(self):
        return self.invoice_number


class OrganisationBillingEvent(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='billing_events',
    )
    licence_batch = models.ForeignKey(
        OrganisationLicenceBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='billing_events',
    )
    provider = models.CharField(max_length=20, choices=OrganisationBillingProvider.choices)
    event_type = models.CharField(max_length=100)
    provider_event_id = models.CharField(max_length=255, unique=True)
    provider_payment_id = models.CharField(max_length=255, blank=True)
    invoice_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OrganisationBillingEventStatus.choices,
        default=OrganisationBillingEventStatus.RECEIVED,
    )
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'organisation_billing_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'provider', 'status']),
        ]


class OrgUsageStat(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='usage_stats',
    )
    snapshot_date = models.DateField()
    active_employees = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    attendance_days_count = models.PositiveIntegerField(default=0)
    leave_requests_count = models.PositiveIntegerField(default=0)
    payroll_runs_count = models.PositiveIntegerField(default=0)
    pending_approvals_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'organisation_usage_stats'
        ordering = ['-snapshot_date', 'organisation__name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'snapshot_date'],
                name='unique_usage_stat_per_org_date',
            ),
        ]


class OrganisationLifecycleEvent(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='lifecycle_events',
    )
    event_type = models.CharField(max_length=32, choices=LifecycleEventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='organisation_lifecycle_events',
    )
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'organisation_lifecycle_events'
        ordering = ['-created_at']


class OrganisationMembership(AuditedBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organisation_memberships',
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    is_org_admin = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=OrganisationMembershipStatus.choices,
        default=OrganisationMembershipStatus.INVITED,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_memberships',
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'organisation_memberships'
        ordering = ['organisation__name', 'user__email']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'organisation'],
                name='unique_user_membership_per_organisation',
            ),
        ]

    @property
    def is_active(self):
        return self.status == OrganisationMembershipStatus.ACTIVE

    def __str__(self):
        return f'{self.user.email} -> {self.organisation.name}'


class OrganisationNote(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    body = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organisation_notes',
    )

    class Meta:
        db_table = 'organisation_notes'
        ordering = ['-created_at']

    def __str__(self):
        return f'Note for {self.organisation.name} by {self.created_by.email}'


class ActAsSession(AuditedBaseModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='act_as_sessions',
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='act_as_sessions',
    )
    target_org_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='targeted_act_as_sessions',
    )
    reason = models.TextField()
    started_at = models.DateTimeField(default=timezone.now)
    refreshed_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ended_act_as_sessions',
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='revoked_act_as_sessions',
    )
    revoked_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'organisation_act_as_sessions'
        ordering = ['-started_at']
        constraints = [
            models.UniqueConstraint(
                fields=['actor'],
                condition=Q(ended_at__isnull=True, revoked_at__isnull=True),
                name='unique_active_act_as_session_per_actor',
            ),
        ]

    @property
    def is_active(self):
        return self.ended_at is None and self.revoked_at is None


class OrganisationFeatureFlag(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='feature_flags',
    )
    feature_code = models.CharField(
        max_length=32,
        choices=OrganisationFeatureCode.choices,
    )
    is_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'organisation_feature_flags'
        ordering = ['feature_code']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'feature_code'],
                name='unique_feature_flag_per_org',
            ),
        ]


class TenantDataExportBatch(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='tenant_data_exports',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='requested_tenant_data_exports',
    )
    export_type = models.CharField(max_length=20, choices=TenantDataExportType.choices)
    status = models.CharField(
        max_length=20,
        choices=TenantDataExportStatus.choices,
        default=TenantDataExportStatus.REQUESTED,
    )
    artifact_key = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tenant_data_export_batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['organisation', 'export_type']),
        ]


class OnboardingStepCode(models.TextChoices):
    ADMINS = "ADMINS", "Admin Users"
    DEPARTMENTS = "DEPARTMENTS", "Departments"
    LOCATIONS = "LOCATIONS", "Locations"
    LEAVE = "LEAVE", "Leave Configuration"
    PAYROLL = "PAYROLL", "Payroll Configuration"
    POLICIES = "POLICIES", "Attendance Policies"
    HOLIDAYS = "HOLIDAYS", "Holiday Calendar"
    FIRST_EMPLOYEE = "FIRST_EMPLOYEE", "First Employee Invite"


class OnboardingChecklist(AuditedBaseModel):
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="onboarding_checklist"
    )
    step = models.CharField(max_length=30, choices=OnboardingStepCode.choices)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "organisation_onboarding_checklist"
        unique_together = [("organisation", "step")]
