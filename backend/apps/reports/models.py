from django.conf import settings
from django.db import models

from apps.common.models import AuditedBaseModel


class ReportDataset(AuditedBaseModel):
    code = models.CharField(max_length=120, unique=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    base_model = models.CharField(max_length=160)
    default_date_field = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'report_datasets'
        ordering = ['label']

    def __str__(self):
        return self.code


class ReportField(AuditedBaseModel):
    dataset = models.ForeignKey(ReportDataset, on_delete=models.CASCADE, related_name='fields')
    code = models.CharField(max_length=180)
    label = models.CharField(max_length=255)
    path = models.CharField(max_length=240)
    data_type = models.CharField(max_length=40)
    is_filterable = models.BooleanField(default=True)
    is_groupable = models.BooleanField(default=True)
    is_summarizable = models.BooleanField(default=False)
    is_sensitive = models.BooleanField(default=False)
    permission_code = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'report_fields'
        ordering = ['dataset__code', 'label']
        constraints = [
            models.UniqueConstraint(fields=['dataset', 'code'], name='unique_report_field_code_per_dataset'),
        ]

    def __str__(self):
        return f'{self.dataset.code}.{self.code}'


class ReportJoin(AuditedBaseModel):
    dataset = models.ForeignKey(ReportDataset, on_delete=models.CASCADE, related_name='joins')
    code = models.CharField(max_length=120)
    label = models.CharField(max_length=255)
    relation_path = models.CharField(max_length=240)
    join_type = models.CharField(max_length=20, default='LEFT')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'report_joins'
        constraints = [
            models.UniqueConstraint(fields=['dataset', 'code'], name='unique_report_join_code_per_dataset'),
        ]


class ReportFolder(AuditedBaseModel):
    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='report_folders')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'report_folders'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['organisation', 'name'], name='unique_report_folder_name_per_org'),
        ]

    def __str__(self):
        return self.name


class ReportTemplate(AuditedBaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        DEPLOYED = 'DEPLOYED', 'Deployed'
        ARCHIVED = 'ARCHIVED', 'Archived'

    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='report_templates')
    folder = models.ForeignKey(ReportFolder, null=True, blank=True, on_delete=models.SET_NULL, related_name='templates')
    dataset = models.ForeignKey(ReportDataset, on_delete=models.PROTECT, related_name='templates')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_report_templates')
    columns = models.JSONField(default=list, blank=True)
    filters = models.JSONField(default=list, blank=True)
    filter_logic = models.CharField(max_length=120, blank=True)
    groupings = models.JSONField(default=list, blank=True)
    summaries = models.JSONField(default=list, blank=True)
    formula_fields = models.JSONField(default=list, blank=True)
    chart = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_system = models.BooleanField(default=False)

    class Meta:
        db_table = 'report_templates'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['organisation', 'name'], name='unique_report_template_name_per_org'),
        ]

    def __str__(self):
        return self.name


class ReportTemplateShare(AuditedBaseModel):
    class AccessLevel(models.TextChoices):
        VIEW = 'VIEW', 'View'
        EDIT = 'EDIT', 'Edit'
        MANAGE = 'MANAGE', 'Manage'

    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='shares')
    role = models.ForeignKey('access_control.AccessRole', null=True, blank=True, on_delete=models.CASCADE, related_name='report_template_shares')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name='report_template_shares')
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.VIEW)

    class Meta:
        db_table = 'report_template_shares'


class ReportSubscription(AuditedBaseModel):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='subscriptions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='report_subscriptions')
    cron_expression = models.CharField(max_length=120)
    file_format = models.CharField(max_length=20, default='xlsx')
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'report_subscriptions'


class ReportRun(AuditedBaseModel):
    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        RUNNING = 'RUNNING', 'Running'
        SUCCEEDED = 'SUCCEEDED', 'Succeeded'
        FAILED = 'FAILED', 'Failed'

    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='report_runs')
    template = models.ForeignKey(ReportTemplate, on_delete=models.PROTECT, related_name='runs')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    parameters = models.JSONField(default=dict, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'report_runs'
        ordering = ['-created_at']


class ReportExport(AuditedBaseModel):
    run = models.ForeignKey(ReportRun, on_delete=models.CASCADE, related_name='exports')
    file_format = models.CharField(max_length=20)
    storage_key = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    byte_size = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'report_exports'
