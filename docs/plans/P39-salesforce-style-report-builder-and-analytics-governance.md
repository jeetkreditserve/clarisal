# P39 - Salesforce-Style Report Builder and Analytics Governance

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fixed report endpoints with a governed report-builder platform where authorised org admins can create, save, share, schedule, export, and reuse reporting templates across HR, payroll, attendance, leave, expense, assets, recruitment, and performance data.

**Architecture:** Add report metadata models and a safe query engine to the existing `reports` app. Do not allow arbitrary SQL. Reports are built from approved datasets, approved joins, approved fields, validated filters, validated formula expressions, and P38 access scopes. Existing fixed reports stay available and are migrated into seeded templates for backward compatibility.

**Tech Stack:** Django 4.2 | DRF | PostgreSQL | Celery | Redis | OpenPyXL | React 19 | TypeScript | TanStack Query | pytest | Vitest | Docker Compose

---

## Current Capability Answer

Org admins cannot create Salesforce-like reporting templates today.

- The backend exposes six hardcoded report types through `REPORT_REGISTRY` in `backend/apps/reports/views.py:18-25`: payroll register, headcount, attrition, leave utilization, attendance summary, and tax summary.
- `OrgReportView` accepts a `report_type` path argument and a few hardcoded query params in `backend/apps/reports/views.py:28-61`; there is no saved report template, field catalog, join model, sharing model, scheduling model, dashboard model, or builder API.
- `BaseReport` requires static `title`, static `columns`, and `generate_rows()` in `backend/apps/reports/base.py:13-64`; it is not a metadata-driven report engine.
- Report permission is only `IsOrgAdmin` plus active org membership in `backend/apps/reports/views.py:28-29`; there is no report-level permission, field-level masking, row-level scoping, folder sharing, or export permission.

This plan implements the missing platform while preserving current fixed-report endpoints.

## Benchmark Requirements

- Salesforce custom reports can be created from scratch or customized from standard reports; report creation, scheduling, builder access, custom report type management, and folders are permissioned. Source: https://help.salesforce.com/s/articleView?id=analytics.reports_custom.htm&language=en_US&type=5
- Salesforce custom report types define the records and fields available to a report based on a primary object and related objects. Source: https://help.salesforce.com/s/articleView?id=sf.reports_report_type_setup.htm&language=en_US&type=5
- Salesforce enhanced custom report type builder supports primary object selection, related-object relationships, report type categories, deployment status, and field layout control. Source: https://help.salesforce.com/s/articleView?id=xcloud.reports_enhanced_defining_report_types.htm&language=en_US&type=5
- Salesforce report builder supports summaries such as sum, average, min, max, and formula columns. Source: https://help.salesforce.com/s/articleView?id=analytics.reports_builder_fields_formulas.htm&language=en_US&type=5
- Darwinbox Atlas includes a report builder for attributes, transactions, transaction summaries, forms data, and custom fields, and applies role-based/contextual security for dataset creation, sharing, and publishing. Source: https://darwinbox.com/blog/darwinbox-atlas-all-in-one-reporting-analytics-engine
- Zoho custom reporting patterns allow users to create a report from a parent module and optional child modules, then save the custom configuration. Source: https://www.zoho.com/us/books/help/reports/custom-reports.html

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/reports/models.py` | Create | Report datasets, fields, joins, folders, templates, filters, formulas, subscriptions, runs, exports |
| `backend/apps/reports/migrations/__init__.py` | Create | Enable reports migrations |
| `backend/apps/reports/migrations/0001_report_builder.py` | Create | Report-builder schema |
| `backend/apps/reports/catalog.py` | Create | Seeded dataset and field catalog |
| `backend/apps/reports/query_engine.py` | Create | Safe ORM query compilation, filter validation, grouping, summaries |
| `backend/apps/reports/formulas.py` | Create | Safe formula parser and evaluator |
| `backend/apps/reports/exporters.py` | Create | JSON, CSV, XLSX export helpers for metadata-driven reports |
| `backend/apps/reports/services.py` | Create | Template creation, preview, run, schedule, sharing, fixed-report migration services |
| `backend/apps/reports/tasks.py` | Create | Async report run, export generation, subscription delivery |
| `backend/apps/reports/serializers.py` | Create | Dataset, template, filter, formula, run, export serializers |
| `backend/apps/reports/views.py` | Modify | Keep fixed endpoint; add report-builder endpoints and permission checks |
| `backend/apps/reports/urls.py` | Modify | Register builder, folders, templates, preview, run, export, subscription endpoints |
| `backend/apps/reports/tests/test_query_engine.py` | Create | Safe query generation and filter tests |
| `backend/apps/reports/tests/test_report_builder_views.py` | Create | API tests for templates, sharing, preview, exports |
| `backend/apps/reports/tests/test_fixed_report_migration.py` | Create | Fixed report compatibility and seeded template tests |
| `backend/apps/access_control/catalog.py` | Modify | Confirm report permissions from P38 are seeded |
| `frontend/src/types/reports.ts` | Modify | Add dataset/template/filter/formula/folder/run/export types |
| `frontend/src/lib/api/reports.ts` | Modify | Add report builder API clients |
| `frontend/src/pages/org/ReportsPage.tsx` | Modify | Preserve fixed report access; link to builder and saved templates |
| `frontend/src/pages/org/ReportBuilderPage.tsx` | Create | Salesforce-style builder UI |
| `frontend/src/pages/org/ReportTemplateListPage.tsx` | Create | Saved templates, folders, sharing, schedule controls |
| `frontend/src/pages/org/ReportRunDetailPage.tsx` | Create | Async run status and export download page |
| `frontend/src/pages/org/__tests__/ReportBuilderPage.test.tsx` | Create | Builder UI tests |
| `frontend/src/pages/org/__tests__/ReportTemplateListPage.test.tsx` | Create | Template list and sharing tests |

---

## Report Builder Concepts

Dataset examples:

- `employees`: employee master data with department, location, manager, employment status
- `payroll_runs`: payroll run headers, employee payroll lines, components, payslips
- `attendance_days`: daily attendance, shift, regularization, biometric source
- `leave_requests`: leave requests, leave types, balances
- `expense_claims`: expense claim headers, claim lines, categories, reimbursement status
- `approval_runs`: approval run status, stages, approvers, turnaround time
- `assets`: asset inventory and assignments
- `recruitment`: jobs, candidates, interviews, offers
- `performance`: cycles, reviews, ratings, goals

Template anatomy:

```json
{
  "dataset": "employees",
  "columns": ["employee.employee_number", "employee.full_name", "department.name"],
  "filters": [{"field": "employee.status", "operator": "eq", "value": "ACTIVE"}],
  "filter_logic": "1",
  "groupings": [{"field": "department.name", "position": 1}],
  "summaries": [{"field": "employee.id", "function": "count"}],
  "formula_fields": [{"label": "Tenure Months", "expression": "months_between(today(), date_of_joining)"}],
  "chart": {"type": "bar", "x": "department.name", "y": "count(employee.id)"}
}
```

## Task 1: Add Report Metadata Models

- [ ] Create `backend/apps/reports/models.py`:

```python
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
        db_table = "report_datasets"
        ordering = ["label"]


class ReportField(AuditedBaseModel):
    dataset = models.ForeignKey(ReportDataset, on_delete=models.CASCADE, related_name="fields")
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
        db_table = "report_fields"
        ordering = ["dataset__code", "label"]
        constraints = [
            models.UniqueConstraint(fields=["dataset", "code"], name="unique_report_field_code_per_dataset"),
        ]


class ReportJoin(AuditedBaseModel):
    dataset = models.ForeignKey(ReportDataset, on_delete=models.CASCADE, related_name="joins")
    code = models.CharField(max_length=120)
    label = models.CharField(max_length=255)
    relation_path = models.CharField(max_length=240)
    join_type = models.CharField(max_length=20, default="LEFT")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "report_joins"
        constraints = [
            models.UniqueConstraint(fields=["dataset", "code"], name="unique_report_join_code_per_dataset"),
        ]


class ReportFolder(AuditedBaseModel):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE, related_name="report_folders")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "report_folders"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organisation", "name"], name="unique_report_folder_name_per_org"),
        ]


class ReportTemplate(AuditedBaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        DEPLOYED = "DEPLOYED", "Deployed"
        ARCHIVED = "ARCHIVED", "Archived"

    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE, related_name="report_templates")
    folder = models.ForeignKey(ReportFolder, null=True, blank=True, on_delete=models.SET_NULL, related_name="templates")
    dataset = models.ForeignKey(ReportDataset, on_delete=models.PROTECT, related_name="templates")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_report_templates")
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
        db_table = "report_templates"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organisation", "name"], name="unique_report_template_name_per_org"),
        ]


class ReportTemplateShare(AuditedBaseModel):
    class AccessLevel(models.TextChoices):
        VIEW = "VIEW", "View"
        EDIT = "EDIT", "Edit"
        MANAGE = "MANAGE", "Manage"

    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name="shares")
    role = models.ForeignKey("access_control.AccessRole", null=True, blank=True, on_delete=models.CASCADE, related_name="report_template_shares")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="report_template_shares")
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.VIEW)

    class Meta:
        db_table = "report_template_shares"


class ReportSubscription(AuditedBaseModel):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name="subscriptions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="report_subscriptions")
    cron_expression = models.CharField(max_length=120)
    file_format = models.CharField(max_length=20, default="xlsx")
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "report_subscriptions"


class ReportRun(AuditedBaseModel):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.CASCADE, related_name="report_runs")
    template = models.ForeignKey(ReportTemplate, on_delete=models.PROTECT, related_name="runs")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    parameters = models.JSONField(default=dict, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "report_runs"
        ordering = ["-created_at"]


class ReportExport(AuditedBaseModel):
    run = models.ForeignKey(ReportRun, on_delete=models.CASCADE, related_name="exports")
    file_format = models.CharField(max_length=20)
    storage_key = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    byte_size = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "report_exports"
```

- [ ] Create `backend/apps/reports/migrations/0001_report_builder.py`.
- [ ] Run `docker compose run --rm backend python manage.py makemigrations reports --check --dry-run`.
- [ ] Expected: no pending report model changes after migration exists.

## Task 2: Seed Dataset and Field Catalog

- [ ] Create `backend/apps/reports/catalog.py`:

```python
REPORT_DATASETS = {
    "employees": {
        "label": "Employees",
        "base_model": "employees.Employee",
        "default_date_field": "date_of_joining",
        "fields": [
            {"code": "employee.id", "label": "Employee ID", "path": "id", "data_type": "uuid", "is_filterable": True, "is_groupable": False},
            {"code": "employee.employee_number", "label": "Employee Number", "path": "employee_number", "data_type": "string"},
            {"code": "employee.full_name", "label": "Employee Name", "path": "user__email", "data_type": "string"},
            {"code": "employee.status", "label": "Status", "path": "status", "data_type": "choice"},
            {"code": "employee.date_of_joining", "label": "Date of Joining", "path": "date_of_joining", "data_type": "date"},
            {"code": "department.name", "label": "Department", "path": "department__name", "data_type": "string"},
            {"code": "office_location.name", "label": "Office Location", "path": "office_location__name", "data_type": "string"},
            {"code": "employee.designation", "label": "Designation", "path": "designation", "data_type": "string"},
            {"code": "employee.current_ctc", "label": "Current CTC", "path": "current_ctc", "data_type": "decimal", "is_sensitive": True, "permission_code": "org.employee_sensitive.read"},
        ],
    },
    "payroll_runs": {
        "label": "Payroll Runs",
        "base_model": "payroll.PayrollRunLine",
        "default_date_field": "pay_run__period_start",
        "fields": [
            {"code": "payroll.period_month", "label": "Payroll Month", "path": "pay_run__period_month", "data_type": "integer"},
            {"code": "payroll.period_year", "label": "Payroll Year", "path": "pay_run__period_year", "data_type": "integer"},
            {"code": "employee.employee_number", "label": "Employee Number", "path": "employee__employee_number", "data_type": "string"},
            {"code": "employee.full_name", "label": "Employee Name", "path": "employee__user__email", "data_type": "string"},
            {"code": "payroll.gross_pay", "label": "Gross Pay", "path": "gross_pay", "data_type": "decimal", "is_summarizable": True, "is_sensitive": True, "permission_code": "org.payroll.read"},
            {"code": "payroll.net_pay", "label": "Net Pay", "path": "net_pay", "data_type": "decimal", "is_summarizable": True, "is_sensitive": True, "permission_code": "org.payroll.read"},
        ],
    },
    "leave_requests": {
        "label": "Leave Requests",
        "base_model": "timeoff.LeaveRequest",
        "default_date_field": "start_date",
        "fields": [
            {"code": "leave.start_date", "label": "Start Date", "path": "start_date", "data_type": "date"},
            {"code": "leave.end_date", "label": "End Date", "path": "end_date", "data_type": "date"},
            {"code": "leave.status", "label": "Status", "path": "status", "data_type": "choice"},
            {"code": "leave.type", "label": "Leave Type", "path": "leave_type__name", "data_type": "string"},
            {"code": "employee.employee_number", "label": "Employee Number", "path": "employee__employee_number", "data_type": "string"},
            {"code": "department.name", "label": "Department", "path": "employee__department__name", "data_type": "string"},
        ],
    },
}
```

- [ ] In `backend/apps/reports/services.py`, add:

```python
from django.apps import apps

from .catalog import REPORT_DATASETS
from .models import ReportDataset, ReportField


def sync_report_catalog():
    for dataset_code, dataset_spec in REPORT_DATASETS.items():
        dataset, _ = ReportDataset.objects.update_or_create(
            code=dataset_code,
            defaults={
                "label": dataset_spec["label"],
                "base_model": dataset_spec["base_model"],
                "default_date_field": dataset_spec.get("default_date_field", ""),
                "is_active": True,
            },
        )
        for field_spec in dataset_spec["fields"]:
            ReportField.objects.update_or_create(
                dataset=dataset,
                code=field_spec["code"],
                defaults={
                    "label": field_spec["label"],
                    "path": field_spec["path"],
                    "data_type": field_spec["data_type"],
                    "is_filterable": field_spec.get("is_filterable", True),
                    "is_groupable": field_spec.get("is_groupable", True),
                    "is_summarizable": field_spec.get("is_summarizable", False),
                    "is_sensitive": field_spec.get("is_sensitive", False),
                    "permission_code": field_spec.get("permission_code", ""),
                },
            )
```

- [ ] Add command `backend/apps/reports/management/commands/sync_report_catalog.py` that calls `sync_report_catalog`.
- [ ] Run `docker compose run --rm backend python manage.py sync_report_catalog`.
- [ ] Expected: command completes and creates the three initial datasets.

## Task 3: Implement Safe Query Engine

**Why:** The report builder must never concatenate arbitrary field names or SQL fragments from user input.

- [ ] Create `backend/apps/reports/query_engine.py`:

```python
from django.apps import apps
from django.db.models import Avg, Count, Max, Min, Q, Sum

from apps.access_control.services import has_permission, scope_employee_queryset

SUMMARY_FUNCTIONS = {
    "count": Count,
    "sum": Sum,
    "avg": Avg,
    "min": Min,
    "max": Max,
}

FILTER_LOOKUPS = {
    "eq": "",
    "neq": "",
    "contains": "__icontains",
    "gte": "__gte",
    "lte": "__lte",
    "in": "__in",
    "isnull": "__isnull",
}


class ReportValidationError(ValueError):
    pass


def _model_for_dataset(dataset):
    app_label, model_name = dataset.base_model.split(".", 1)
    return apps.get_model(app_label, model_name)


def _field_map(dataset):
    return {field.code: field for field in dataset.fields.filter(is_active=True)}


def _validate_field(field_map, field_code):
    field = field_map.get(field_code)
    if field is None:
        raise ReportValidationError(f"Unknown report field: {field_code}")
    return field


def _filter_q(field_map, filter_payload):
    field = _validate_field(field_map, filter_payload["field"])
    if not field.is_filterable:
        raise ReportValidationError(f"Field is not filterable: {field.code}")
    operator = filter_payload["operator"]
    if operator not in FILTER_LOOKUPS:
        raise ReportValidationError(f"Unsupported filter operator: {operator}")
    lookup = f"{field.path}{FILTER_LOOKUPS[operator]}"
    value = filter_payload.get("value")
    if operator == "neq":
        return ~Q(**{field.path: value})
    return Q(**{lookup: value})


def build_report_queryset(template, user, organisation, parameters=None):
    parameters = parameters or {}
    dataset = template.dataset
    model = _model_for_dataset(dataset)
    queryset = model.objects.all()

    if dataset.code == "employees":
        queryset = scope_employee_queryset(queryset, user, organisation, "org.employees.read")
    elif hasattr(model, "employee"):
        scoped_employee_ids = scope_employee_queryset(
            apps.get_model("employees", "Employee").objects.all(),
            user,
            organisation,
            "org.employees.read",
        ).values_list("id", flat=True)
        queryset = queryset.filter(employee_id__in=scoped_employee_ids)
    else:
        queryset = queryset.filter(organisation=organisation)

    field_map = _field_map(dataset)
    for field_code in template.columns:
        field = _validate_field(field_map, field_code)
        if field.permission_code and not has_permission(user, field.permission_code, organisation):
            raise ReportValidationError(f"Missing permission for field: {field.code}")

    combined_q = Q()
    for filter_payload in template.filters:
        combined_q &= _filter_q(field_map, filter_payload)
    return queryset.filter(combined_q), field_map
```

- [ ] Add row generation:

```python
def preview_report(template, user, organisation, limit=100, parameters=None):
    queryset, field_map = build_report_queryset(template, user, organisation, parameters)
    selected_fields = [_validate_field(field_map, code) for code in template.columns]
    values = [field.path for field in selected_fields]
    rows = []
    for item in queryset.values(*values)[:limit]:
        row = {}
        for field in selected_fields:
            row[field.code] = item.get(field.path)
        rows.append(row)
    return {
        "columns": [{"code": field.code, "label": field.label, "data_type": field.data_type} for field in selected_fields],
        "rows": rows,
        "truncated": queryset.count() > limit,
    }
```

- [ ] Add tests:

```python
def test_query_engine_rejects_unknown_field(report_template, org_admin_user, organisation):
    report_template.columns = ["employee.employee_number", "employee.password_hash"]
    report_template.save(update_fields=["columns"])

    with pytest.raises(ReportValidationError, match="Unknown report field"):
        preview_report(report_template, org_admin_user, organisation)
```

- [ ] Run `docker compose run --rm backend pytest apps/reports/tests/test_query_engine.py -q`.
- [ ] Expected: tests pass.

## Task 4: Add Safe Formula Fields

**Why:** Salesforce-style reports need derived fields, but formulas must be constrained to safe expressions.

- [ ] Create `backend/apps/reports/formulas.py`:

```python
import ast
from datetime import date

ALLOWED_FUNCTIONS = {"today", "days_between", "months_between", "coalesce"}
ALLOWED_NODES = {
    ast.Expression,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.UnaryOp,
    ast.USub,
}


class FormulaValidationError(ValueError):
    pass


def validate_formula(expression):
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            raise FormulaValidationError(f"Unsupported formula syntax: {type(node).__name__}")
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") not in ALLOWED_FUNCTIONS:
            raise FormulaValidationError(f"Unsupported formula function: {getattr(node.func, 'id', '')}")
    return tree


def today():
    return date.today()


def days_between(a, b):
    return abs((a - b).days)


def months_between(a, b):
    return abs((a.year - b.year) * 12 + (a.month - b.month))


def coalesce(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None
```

- [ ] Formula expressions initially support date math and null coalescing only. Do not add arbitrary attribute access, imports, comprehensions, lambdas, or function definitions.
- [ ] Add tests for valid and invalid formulas:

```python
def test_formula_rejects_import_call():
    with pytest.raises(FormulaValidationError):
        validate_formula("__import__('os').system('whoami')")
```

## Task 5: Add Report Builder APIs

- [ ] Create serializers in `backend/apps/reports/serializers.py`:

```python
class ReportFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportField
        fields = ["id", "code", "label", "data_type", "is_filterable", "is_groupable", "is_summarizable", "is_sensitive"]


class ReportDatasetSerializer(serializers.ModelSerializer):
    fields = ReportFieldSerializer(many=True)

    class Meta:
        model = ReportDataset
        fields = ["id", "code", "label", "description", "default_date_field", "fields"]


class ReportTemplateWriteSerializer(serializers.Serializer):
    folder_id = serializers.UUIDField(required=False)
    dataset_code = serializers.CharField(max_length=120)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=ReportTemplate.Status.choices, default=ReportTemplate.Status.DRAFT)
    columns = serializers.ListField(child=serializers.CharField(max_length=180))
    filters = serializers.ListField(child=serializers.DictField(), required=False)
    filter_logic = serializers.CharField(required=False, allow_blank=True)
    groupings = serializers.ListField(child=serializers.DictField(), required=False)
    summaries = serializers.ListField(child=serializers.DictField(), required=False)
    formula_fields = serializers.ListField(child=serializers.DictField(), required=False)
    chart = serializers.DictField(required=False)
```

- [ ] Add views in `backend/apps/reports/views.py`:
  - `ReportDatasetListView`: requires `org.reports.read`
  - `ReportFolderListCreateView`: requires `org.reports.builder.manage`
  - `ReportTemplateListCreateView`: requires `org.reports.read` for GET and `org.reports.builder.manage` for POST
  - `ReportTemplateDetailView`: requires template share and permission code
  - `ReportTemplateDraftPreviewView`: requires `org.reports.read`
  - `ReportTemplatePreviewView`: requires `org.reports.read`
  - `ReportTemplateRunView`: requires `org.reports.read`
  - `ReportExportView`: requires `org.reports.export`
  - `ReportSubscriptionListCreateView`: requires `org.reports.builder.manage`
- [ ] Register routes:

```python
urlpatterns = [
    path("org/reports/datasets/", ReportDatasetListView.as_view()),
    path("org/reports/folders/", ReportFolderListCreateView.as_view()),
    path("org/reports/templates/", ReportTemplateListCreateView.as_view()),
    path("org/reports/templates/preview-draft/", ReportTemplateDraftPreviewView.as_view()),
    path("org/reports/templates/<uuid:pk>/", ReportTemplateDetailView.as_view()),
    path("org/reports/templates/<uuid:pk>/preview/", ReportTemplatePreviewView.as_view()),
    path("org/reports/templates/<uuid:pk>/run/", ReportTemplateRunView.as_view()),
    path("org/reports/runs/<uuid:pk>/exports/<uuid:export_id>/", ReportExportView.as_view()),
    path("org/reports/subscriptions/", ReportSubscriptionListCreateView.as_view()),
]
```

- [ ] Add API test:

```python
def test_report_builder_denies_template_creation_without_manage_permission(api_client, reports_reader_user):
    api_client.force_authenticate(reports_reader_user)
    response = api_client.post(
        "/api/org/reports/templates/",
        {"dataset_code": "employees", "name": "Active Employees", "columns": ["employee.employee_number"]},
        format="json",
    )

    assert response.status_code == 403
```

## Task 6: Implement Async Runs, Exports, and Subscriptions

- [ ] Create `backend/apps/reports/tasks.py`:

```python
from celery import shared_task
from django.utils import timezone

from .exporters import build_export
from .models import ReportExport, ReportRun
from .query_engine import preview_report


@shared_task
def run_report_task(run_id, file_format="xlsx"):
    run = ReportRun.objects.select_related("template", "organisation", "requested_by").get(id=run_id)
    run.status = ReportRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "modified_at"])
    try:
        result = preview_report(run.template, run.requested_by, run.organisation, limit=50000, parameters=run.parameters)
        export = build_export(run, result, file_format)
        run.status = ReportRun.Status.SUCCEEDED
        run.row_count = len(result["rows"])
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "row_count", "completed_at", "modified_at"])
        return {"run_id": str(run.id), "export_id": str(export.id)}
    except Exception as exc:
        run.status = ReportRun.Status.FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error_message", "completed_at", "modified_at"])
        raise
```

- [ ] Create `backend/apps/reports/exporters.py`:

```python
import csv
import io

from openpyxl import Workbook

from .models import ReportExport


def build_export(run, result, file_format):
    if file_format == "csv":
        content_type = "text/csv"
        file_name = f"{run.template.name}.csv"
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=[column["code"] for column in result["columns"]])
        writer.writeheader()
        writer.writerows(result["rows"])
        payload = buffer.getvalue().encode("utf-8")
    else:
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_name = f"{run.template.name}.xlsx"
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Report"
        worksheet.append([column["label"] for column in result["columns"]])
        for row in result["rows"]:
            worksheet.append([row.get(column["code"], "") for column in result["columns"]])
        output = io.BytesIO()
        workbook.save(output)
        payload = output.getvalue()

    # Phase 1 stores content through the existing storage backend key. If no S3 backend is configured, use default file storage.
    storage_key = save_report_export(file_name, payload, content_type)
    return ReportExport.objects.create(
        run=run,
        file_format=file_format,
        storage_key=storage_key,
        file_name=file_name,
        content_type=content_type,
        byte_size=len(payload),
    )
```

- [ ] Implement `save_report_export` using Django `default_storage`.
- [ ] Add tests for queued -> running -> succeeded and export metadata creation.

## Task 7: Seed Existing Fixed Reports as System Templates

**Why:** Current report URLs must continue to work while the new builder becomes primary.

- [ ] In `backend/apps/reports/services.py`, add:

```python
FIXED_REPORT_TEMPLATE_SEEDS = [
    {
        "name": "Payroll Register",
        "dataset": "payroll_runs",
        "columns": ["employee.employee_number", "employee.full_name", "payroll.gross_pay", "payroll.net_pay"],
        "filters": [],
        "groupings": [{"field": "payroll.period_year", "position": 1}, {"field": "payroll.period_month", "position": 2}],
        "summaries": [{"field": "payroll.net_pay", "function": "sum"}],
    },
    {
        "name": "Headcount",
        "dataset": "employees",
        "columns": ["department.name", "office_location.name", "employee.status"],
        "filters": [{"field": "employee.status", "operator": "eq", "value": "ACTIVE"}],
        "groupings": [{"field": "department.name", "position": 1}],
        "summaries": [{"field": "employee.id", "function": "count"}],
    },
]


def seed_system_report_templates(organisation, owner=None):
    default_folder, _ = ReportFolder.objects.get_or_create(
        organisation=organisation,
        name="System Reports",
        defaults={"description": "Seeded reports equivalent to legacy fixed reports.", "created_by": owner},
    )
    for seed in FIXED_REPORT_TEMPLATE_SEEDS:
        dataset = ReportDataset.objects.get(code=seed["dataset"])
        ReportTemplate.objects.update_or_create(
            organisation=organisation,
            name=seed["name"],
            defaults={
                "folder": default_folder,
                "dataset": dataset,
                "owner": owner,
                "status": ReportTemplate.Status.DEPLOYED,
                "columns": seed["columns"],
                "filters": seed["filters"],
                "groupings": seed["groupings"],
                "summaries": seed["summaries"],
                "is_system": True,
            },
        )
```

- [ ] Add management command `seed_system_report_templates --organisation <id>` and bulk option `--all-active-organisations`.
- [ ] Keep `OrgReportView` legacy endpoint, but internally log a deprecation audit event and link to the equivalent template in the response when possible.
- [ ] Add compatibility test that `/api/org/reports/headcount/` still returns the legacy shape.

## Task 8: Build Frontend Report Builder

- [ ] Modify `frontend/src/types/reports.ts`:

```ts
export interface ReportDataset {
  id: string
  code: string
  label: string
  description: string
  fields: ReportField[]
}

export interface ReportField {
  id: string
  code: string
  label: string
  data_type: string
  is_filterable: boolean
  is_groupable: boolean
  is_summarizable: boolean
  is_sensitive: boolean
}

export interface ReportTemplatePayload {
  dataset_code: string
  name: string
  description: string
  status: 'DRAFT' | 'DEPLOYED' | 'ARCHIVED'
  columns: string[]
  filters: ReportFilter[]
  filter_logic: string
  groupings: ReportGrouping[]
  summaries: ReportSummary[]
  formula_fields: ReportFormulaField[]
  chart: ReportChart | null
}
```

- [ ] Add API clients in `frontend/src/lib/api/reports.ts`:

```ts
export async function fetchReportDatasets(): Promise<ReportDataset[]> {
  const { data } = await api.get('/org/reports/datasets/')
  return data
}

export async function previewReportTemplate(payload: ReportTemplatePayload): Promise<ReportPreviewResult> {
  const { data } = await api.post('/org/reports/templates/preview-draft/', payload)
  return data
}

export async function saveReportTemplate(payload: ReportTemplatePayload): Promise<ReportTemplate> {
  const { data } = await api.post('/org/reports/templates/', payload)
  return data
}
```

- [ ] Create `frontend/src/pages/org/ReportBuilderPage.tsx` with these panels:
  - Dataset selector.
  - Column picker grouped by field category.
  - Filter builder with operator choices based on field type.
  - Filter logic editor using numbers such as `1 AND (2 OR 3)`.
  - Grouping and summary builder.
  - Formula field builder with validation feedback.
  - Chart selector for bar, line, pie, and table-only.
  - Preview grid capped to 100 rows.
  - Save as draft, deploy, clone, and run buttons.
- [ ] Ensure the builder hides fields marked `is_sensitive` if the current user lacks the field's permission summary from P38.
- [ ] Add test:

```ts
it('builds an active employee report and previews rows', async () => {
  mockReportDatasets([employeesDataset])
  mockPreviewReport({ columns: [{ code: 'employee.employee_number', label: 'Employee Number' }], rows: [{ 'employee.employee_number': 'E-001' }] })

  render(<ReportBuilderPage />)

  await userEvent.selectOptions(await screen.findByLabelText(/Dataset/i), 'employees')
  await userEvent.click(screen.getByRole('checkbox', { name: /Employee Number/i }))
  await userEvent.click(screen.getByRole('button', { name: /Preview/i }))

  expect(await screen.findByText('E-001')).toBeInTheDocument()
})
```

## Task 9: Build Saved Templates, Folders, Sharing, and Runs UI

- [ ] Create `frontend/src/pages/org/ReportTemplateListPage.tsx` with:
  - Folder sidebar.
  - Template status tabs: Draft, Deployed, Archived.
  - Search by name/dataset.
  - Clone, edit, archive, run, export actions.
  - Share drawer with role/user picker and access level.
  - Schedule drawer with cron presets: daily, weekly, monthly.
- [ ] Create `frontend/src/pages/org/ReportRunDetailPage.tsx` with:
  - Run status.
  - Requested by.
  - Started/completed timestamps.
  - Row count.
  - Export download links.
  - Error message if failed.
- [ ] Modify `frontend/src/pages/org/ReportsPage.tsx`:
  - Keep legacy fixed reports.
  - Add "Saved Templates" and "Create Report" actions.
  - Show builder only when `hasPermission(user, 'org.reports.builder.manage')`.
  - Show export buttons only when `hasPermission(user, 'org.reports.export')`.

## Task 10: Enforce P38 Permissions and Scopes End-to-End

- [ ] Every builder endpoint must require one of:
  - `org.reports.read`
  - `org.reports.builder.manage`
  - `org.reports.export`
- [ ] Every dataset query must call P38 scoping helpers. Employee-based datasets must call `scope_employee_queryset`; payroll datasets must additionally require `org.payroll.read`.
- [ ] Sensitive fields must require `ReportField.permission_code`.
- [ ] Folder/template sharing cannot grant access to a user who lacks `org.reports.read`.
- [ ] Export cannot run if preview is allowed but `org.reports.export` is missing.
- [ ] Add tests:

```python
def test_payroll_field_requires_payroll_permission(report_template, reports_reader_user, organisation):
    report_template.columns = ["employee.employee_number", "payroll.net_pay"]
    report_template.save(update_fields=["columns"])

    with pytest.raises(ReportValidationError, match="Missing permission for field"):
        preview_report(report_template, reports_reader_user, organisation)
```

## Task 11: Docker Verification

- [ ] Rebuild backend and frontend images:

```bash
docker compose build backend frontend
```

- [ ] Recreate services:

```bash
docker compose up -d --force-recreate backend frontend
```

- [ ] Run migrations and catalog seed:

```bash
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py sync_access_control
docker compose run --rm backend python manage.py sync_report_catalog
```

- [ ] Run backend tests:

```bash
docker compose run --rm backend pytest apps/reports/tests apps/access_control/tests -q
```

- [ ] Run frontend tests:

```bash
docker compose run --rm frontend npm run test -- ReportBuilderPage ReportTemplateListPage rbac
```

- [ ] Run full frontend check:

```bash
docker compose run --rm frontend npm run check
```

- [ ] Expected: all commands exit 0.

## Implementation Order

1. Metadata schema and catalog.
2. Query engine and validation.
3. Permission and scope enforcement.
4. Builder APIs.
5. Async run/export/subscription pipeline.
6. Fixed report migration.
7. Frontend builder and saved-template UI.
8. Docker verification.

## Self-Review Checklist for Workers

- [ ] No endpoint accepts arbitrary model paths, field paths, SQL snippets, or unvalidated formula syntax.
- [ ] Every selected field exists in `ReportField` for the selected dataset.
- [ ] Payroll and sensitive fields fail closed without explicit permissions.
- [ ] Employee row visibility respects P38 scopes by department, location, selected employees, and reporting tree.
- [ ] Legacy fixed report endpoints still work.
- [ ] Report exports require `org.reports.export`.
- [ ] Report templates have folder/share behavior and cannot be read by users without report access.
- [ ] Report builder frontend hides actions the current user cannot perform.
