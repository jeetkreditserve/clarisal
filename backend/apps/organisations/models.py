import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class OrganisationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Payment'
    PAID = 'PAID', 'Paid'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class Organisation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OrganisationStatus.choices,
        default=OrganisationStatus.PENDING,
    )
    licence_count = models.PositiveIntegerField(default=0)
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
