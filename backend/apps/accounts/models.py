from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import AuditedBaseModel


class AccountType(models.TextChoices):
    CONTROL_TOWER = 'CONTROL_TOWER', 'Control Tower'
    WORKFORCE = 'WORKFORCE', 'Workforce'


class UserRole(models.TextChoices):
    CONTROL_TOWER = 'CONTROL_TOWER', 'Control Tower'
    ORG_ADMIN = 'ORG_ADMIN', 'Organisation Admin'
    EMPLOYEE = 'EMPLOYEE', 'Employee'


class ContactKind(models.TextChoices):
    WORK = 'WORK', 'Work'
    PERSONAL = 'PERSONAL', 'Personal'
    LEGAL = 'LEGAL', 'Legal'
    EMERGENCY = 'EMERGENCY', 'Emergency'
    OTHER = 'OTHER', 'Other'


class Person(AuditedBaseModel):
    class Meta:
        db_table = 'people'
        ordering = ['-created_at']

    def __str__(self):
        primary_email = self.email_addresses.filter(is_primary=True).first()
        if primary_email:
            return primary_email.email
        return f'Person {self.id}'


class EmailAddress(AuditedBaseModel):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='email_addresses',
    )
    email = models.EmailField()
    normalized_email = models.CharField(max_length=254, unique=True)
    kind = models.CharField(
        max_length=20,
        choices=ContactKind.choices,
        default=ContactKind.WORK,
    )
    is_primary = models.BooleanField(default=False)
    is_login = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    class Meta:
        db_table = 'email_addresses'
        ordering = ['-is_primary', 'email']
        constraints = [
            models.UniqueConstraint(
                fields=['person'],
                condition=Q(is_primary=True),
                name='unique_primary_email_per_person',
            ),
        ]

    def __str__(self):
        return self.email


class PhoneNumber(AuditedBaseModel):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='phone_numbers',
    )
    e164_number = models.CharField(max_length=20, unique=True)
    display_number = models.CharField(max_length=32, blank=True)
    kind = models.CharField(
        max_length=20,
        choices=ContactKind.choices,
        default=ContactKind.WORK,
    )
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    class Meta:
        db_table = 'phone_numbers'
        ordering = ['-is_primary', 'e164_number']
        constraints = [
            models.UniqueConstraint(
                fields=['person'],
                condition=Q(is_primary=True),
                name='unique_primary_phone_per_person',
            ),
        ]

    def __str__(self):
        return self.e164_number


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = email.strip().lower()
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('account_type', AccountType.CONTROL_TOWER)
        extra_fields.setdefault('role', UserRole.CONTROL_TOWER)
        return self.create_user(email, password, **extra_fields)


class User(AuditedBaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField()
    person = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='accounts',
    )
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.WORKFORCE,
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.EMPLOYEE)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users',
    )
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_onboarding_email_sent = models.BooleanField(default=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'account_type'],
                name='unique_email_per_account_type',
            ),
        ]

    def __str__(self):
        return f'{self.email} ({self.account_type}/{self.role})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def save(self, *args, **kwargs):
        from .contact_services import ensure_user_contact_identity

        if self.email:
            self.email = self.email.strip().lower()
        ensure_user_contact_identity(self)
        super().save(*args, **kwargs)


class PasswordResetToken(AuditedBaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    requested_by_ip = models.GenericIPAddressField(null=True, blank=True)
    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.used_at and not self.is_expired
