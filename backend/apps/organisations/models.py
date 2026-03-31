import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify


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


class OrganisationMembershipStatus(models.TextChoices):
    INVITED = 'INVITED', 'Invited'
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    REVOKED = 'REVOKED', 'Revoked'


class Organisation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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


class OrganisationStateTransition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organisation_state_transitions'
        ordering = ['-created_at']


class OrganisationLicenceLedger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organisation_licence_ledger'
        ordering = ['-created_at']


class OrganisationLifecycleEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organisation_lifecycle_events'
        ordering = ['-created_at']


class OrganisationMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
