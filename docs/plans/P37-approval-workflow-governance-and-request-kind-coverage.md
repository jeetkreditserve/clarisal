# P37 - Approval Workflow Governance and Request Kind Coverage

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make organisation admins able to configure, preview, and enforce approval workflows for every supported business request type: leave, on duty, attendance regularization, expense claim, payroll processing, salary revision, compensation template change, promotion, and transfer.

**Architecture:** Keep the existing `approvals` domain model, but remove hardcoded coverage gaps. Add a canonical request-kind catalog, generic employee workflow assignments, richer routing conditions, richer approver targets, workflow presets, and a simulation endpoint. The current workflow engine already supports ordered stages and `ALL`/`ANY` stage modes, so this plan extends configurability instead of replacing the engine.

**Tech Stack:** Django 4.2 | DRF | PostgreSQL | React 19 | TypeScript | TanStack Query | pytest | Vitest | Docker Compose

---

## Current Capability Answer

Org admins cannot fully configure all requested workflow types from the product today.

- Backend enum coverage exists for all requested kinds in `backend/apps/approvals/models.py:10-22`: `LEAVE`, `ON_DUTY`, `ATTENDANCE_REGULARIZATION`, `EXPENSE_CLAIM`, `PAYROLL_PROCESSING`, `SALARY_REVISION`, `COMPENSATION_TEMPLATE_CHANGE`, `PROMOTION`, `TRANSFER`.
- Multi-level approval mechanics exist through `ApprovalStage.sequence`, `ApprovalStage.mode`, and `ApprovalStageApprover` in `backend/apps/approvals/models.py:151-240`; completion logic supports `ALL` and `ANY` at `backend/apps/approvals/services.py:493-546`.
- Workflow resolution is generic once a workflow exists, but default-readiness only requires leave, on duty, and attendance regularization at `backend/apps/approvals/services.py:27-46`.
- Employee-specific assignment is hardcoded only for leave, on duty, attendance regularization, and expense claim at `backend/apps/approvals/services.py:122-135`.
- The frontend workflow builder omits `PROMOTION` and `TRANSFER` from `ApprovalRequestKind` and `APPROVAL_REQUEST_KIND_OPTIONS` at `frontend/src/types/hr.ts:43-50` and `frontend/src/lib/constants.ts:27-35`.
- Approver targets are too narrow. Today they are only reporting manager, specific employee, and primary org admin at `backend/apps/approvals/models.py:30-33`.
- Routing conditions are too narrow. Today rules can match department, office location, specific employee, employment type, designation, and leave type at `backend/apps/approvals/models.py:102-141`.

This means API callers can create many workflows if they know the backend contract, but the product does not yet provide Zoho/Darwinbox/Keka-grade workflow administration.

## Benchmark Requirements

Primary benchmark: Zoho People and related Zoho approval/report patterns.

- Zoho-style custom approvals should allow module-specific approval flows with rule conditions and extra approver levels for exceptions such as high-value transactions. Source: https://www.zoho.com/procurement/help/settings/approvals/custom-approval/
- Zoho People roles separate general and specific roles and allow location and department applicability for data-admin access. Source: https://www.zoho.com/people/help/adminguide/RolesEnhancementUPDdoc.html

Secondary benchmarks:

- Darwinbox emphasizes configurable access by department, location, band, designation, business unit, and module; it also calls out maker-checker approval flows for employee data changes. Source: https://darwinbox.com/blog/advanced-hrms-features
- Keka separates explicit user roles from implicit roles such as reporting manager, department head, and business head, and notes those implicit roles can support leave, expense, asset, and finance approval chains. Source: https://help.keka.com/hc/en-us/articles/39946719445393-Overview-Roles-Permissions
- SAP SuccessFactors workflow administration includes reminders, escalation, and automatic approval for stalled workflows. Source: https://help.sap.com/docs/successfactors-employee-central/implementing-and-managing-workflows/configuring-workflow-features

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/approvals/catalog.py` | Create | Canonical request-kind metadata, module grouping, defaults, and preset stage definitions |
| `backend/apps/approvals/models.py` | Modify | Add generic assignment model, richer rule fields, richer approver and fallback types |
| `backend/apps/approvals/migrations/0009_workflow_catalog_assignments_and_rule_scope.py` | Create | Persist assignment/rule/approver schema changes |
| `backend/apps/approvals/role_resolver.py` | Create | Temporary role-to-employee resolver used until P38 installs full access control |
| `backend/apps/approvals/services.py` | Modify | Use generic assignments, request-kind catalog, richer rule matching, approver resolution, and simulation |
| `backend/apps/approvals/serializers.py` | Modify | Expose catalog, assignments, new rule fields, and simulation payloads |
| `backend/apps/approvals/views.py` | Modify | Add catalog, preset, assignment, readiness, and simulation endpoints |
| `backend/apps/approvals/urls.py` | Modify | Register new org admin workflow endpoints |
| `backend/apps/approvals/tests/test_workflow_catalog.py` | Create | Catalog completeness and readiness tests |
| `backend/apps/approvals/tests/test_workflow_resolution.py` | Modify | Assignment, rules, fallback, and every request-kind resolution tests |
| `backend/apps/approvals/tests/test_views.py` | Modify | API coverage for builder, simulation, assignments, presets |
| `frontend/src/types/hr.ts` | Modify | Add missing request kinds and new workflow types |
| `frontend/src/lib/constants.ts` | Modify | Replace hardcoded request-kind list with catalog-backed labels |
| `frontend/src/lib/api/approvals.ts` | Modify | Add catalog, presets, assignment, readiness, and simulation clients |
| `frontend/src/pages/org/ApprovalWorkflowBuilderPage.tsx` | Modify | Add all request kinds, templates, richer rule editor, preview/simulation |
| `frontend/src/pages/org/ApprovalWorkflowReadinessPage.tsx` | Create | Show missing defaults, inactive workflows, untested workflows, and request-kind coverage |
| `frontend/src/routes.tsx` | Modify | Register readiness page under org settings |
| `frontend/src/pages/org/__tests__/ApprovalWorkflowBuilderPage.test.tsx` | Modify | UI coverage for all request kinds and simulation |
| `frontend/src/pages/org/__tests__/ApprovalWorkflowReadinessPage.test.tsx` | Create | Readiness page coverage |

---

## Task 1: Add Canonical Request-Kind Catalog

**Why:** The backend enum and frontend constants drifted. The catalog becomes the single backend source for product behavior: labels, modules, subject model, whether default workflow is required, whether assignment is allowed, and recommended preset stages.

- [ ] Create `backend/apps/approvals/catalog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from .models import ApprovalFallbackType, ApprovalRequestKind, ApprovalStageMode


@dataclass(frozen=True)
class ApprovalStagePreset:
    name: str
    sequence: int
    mode: str
    approver_types: tuple[str, ...]
    fallback_type: str = ApprovalFallbackType.PRIMARY_ORG_ADMIN
    reminder_after_hours: int | None = 24
    escalate_after_hours: int | None = 48


@dataclass(frozen=True)
class ApprovalRequestKindMeta:
    kind: str
    label: str
    module: str
    subject_label: str
    requires_default_workflow: bool
    supports_employee_assignment: bool
    supports_amount_rules: bool
    supports_leave_type_rules: bool
    recommended_minimum_stages: int
    presets: tuple[ApprovalStagePreset, ...]


MANAGER_STAGE = ApprovalStagePreset(
    name="Manager review",
    sequence=1,
    mode=ApprovalStageMode.ALL,
    approver_types=("REPORTING_MANAGER",),
)

HR_STAGE = ApprovalStagePreset(
    name="HR review",
    sequence=2,
    mode=ApprovalStageMode.ALL,
    approver_types=("PRIMARY_ORG_ADMIN",),
)

FINANCE_STAGE = ApprovalStagePreset(
    name="Finance review",
    sequence=2,
    mode=ApprovalStageMode.ALL,
    approver_types=("FINANCE_APPROVER",),
)

PAYROLL_STAGE = ApprovalStagePreset(
    name="Payroll review",
    sequence=2,
    mode=ApprovalStageMode.ALL,
    approver_types=("PAYROLL_ADMIN",),
)

APPROVAL_REQUEST_KIND_CATALOG: dict[str, ApprovalRequestKindMeta] = {
    ApprovalRequestKind.LEAVE: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.LEAVE,
        label="Leave",
        module="Time Off",
        subject_label="Leave request",
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=False,
        supports_leave_type_rules=True,
        recommended_minimum_stages=1,
        presets=(MANAGER_STAGE, HR_STAGE),
    ),
    ApprovalRequestKind.ON_DUTY: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.ON_DUTY,
        label="On Duty",
        module="Attendance",
        subject_label="On-duty request",
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=False,
        supports_leave_type_rules=False,
        recommended_minimum_stages=1,
        presets=(MANAGER_STAGE, HR_STAGE),
    ),
    ApprovalRequestKind.ATTENDANCE_REGULARIZATION: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
        label="Attendance Regularization",
        module="Attendance",
        subject_label="Attendance regularization request",
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=False,
        supports_leave_type_rules=False,
        recommended_minimum_stages=1,
        presets=(MANAGER_STAGE, HR_STAGE),
    ),
    ApprovalRequestKind.EXPENSE_CLAIM: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.EXPENSE_CLAIM,
        label="Expense Claim",
        module="Expense",
        subject_label="Expense claim",
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(MANAGER_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.PAYROLL_PROCESSING: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.PAYROLL_PROCESSING,
        label="Payroll Processing",
        module="Payroll",
        subject_label="Payroll run",
        requires_default_workflow=True,
        supports_employee_assignment=False,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(PAYROLL_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.SALARY_REVISION: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.SALARY_REVISION,
        label="Salary Revision",
        module="Payroll",
        subject_label="Salary revision",
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(MANAGER_STAGE, PAYROLL_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
        label="Compensation Template Change",
        module="Payroll",
        subject_label="Compensation template change",
        requires_default_workflow=True,
        supports_employee_assignment=False,
        supports_amount_rules=False,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(PAYROLL_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.PROMOTION: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.PROMOTION,
        label="Promotion",
        module="Employee Lifecycle",
        subject_label="Promotion request",
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(MANAGER_STAGE, HR_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.TRANSFER: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.TRANSFER,
        label="Transfer",
        module="Employee Lifecycle",
        subject_label="Transfer request",
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=False,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(MANAGER_STAGE, HR_STAGE),
    ),
}


def get_workflow_enabled_request_kinds() -> list[str]:
    return list(APPROVAL_REQUEST_KIND_CATALOG.keys())


def get_required_default_request_kinds() -> list[str]:
    return [
        meta.kind
        for meta in APPROVAL_REQUEST_KIND_CATALOG.values()
        if meta.requires_default_workflow
    ]
```

- [ ] Run `docker compose run --rm backend python manage.py shell -c "from apps.approvals.catalog import get_required_default_request_kinds; print(len(get_required_default_request_kinds()))"`.
- [ ] Expected: prints `9`.

## Task 2: Add Approver and Fallback Types Needed by Real HR Workflows

**Why:** Real implementations use implicit roles and permission groups, not only one named employee or one primary admin. This mirrors Keka implicit roles, Darwinbox role/module permissions, and SAP-style role assignments while still resolving to concrete approval actions at runtime.

- [ ] In `backend/apps/approvals/models.py`, extend `ApprovalApproverType`:

```python
class ApprovalApproverType(models.TextChoices):
    REPORTING_MANAGER = "REPORTING_MANAGER", "Reporting Manager"
    NTH_LEVEL_MANAGER = "NTH_LEVEL_MANAGER", "Nth Level Manager"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD", "Department Head"
    LOCATION_ADMIN = "LOCATION_ADMIN", "Location Admin"
    HR_BUSINESS_PARTNER = "HR_BUSINESS_PARTNER", "HR Business Partner"
    PAYROLL_ADMIN = "PAYROLL_ADMIN", "Payroll Admin"
    FINANCE_APPROVER = "FINANCE_APPROVER", "Finance Approver"
    ROLE = "ROLE", "Role"
    SPECIFIC_EMPLOYEE = "SPECIFIC_EMPLOYEE", "Specific Employee"
    PRIMARY_ORG_ADMIN = "PRIMARY_ORG_ADMIN", "Primary Organisation Admin"
```

- [ ] In the same file, extend `ApprovalFallbackType`:

```python
class ApprovalFallbackType(models.TextChoices):
    NONE = "NONE", "None"
    REPORTING_MANAGER = "REPORTING_MANAGER", "Reporting Manager"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD", "Department Head"
    ROLE = "ROLE", "Role"
    SPECIFIC_EMPLOYEE = "SPECIFIC_EMPLOYEE", "Specific Employee"
    PRIMARY_ORG_ADMIN = "PRIMARY_ORG_ADMIN", "Primary Organisation Admin"
```

- [ ] Add fields to `ApprovalStageApprover`:

```python
    manager_level = models.PositiveSmallIntegerField(default=1)
    role_code = models.CharField(max_length=120, blank=True)
```

- [ ] Add fields to `ApprovalStage` and `ApprovalStageEscalationPolicy`:

```python
    fallback_role_code = models.CharField(max_length=120, blank=True)
```

```python
    escalation_role_code = models.CharField(max_length=120, blank=True)
```

- [ ] Create migration `backend/apps/approvals/migrations/0009_workflow_catalog_assignments_and_rule_scope.py`.
- [ ] Run `docker compose run --rm backend python manage.py makemigrations approvals --check --dry-run`.
- [ ] Expected: no pending model changes after the migration file is created.

## Task 3: Replace Hardcoded Employee Workflow Fields With Generic Assignments

**Why:** The current resolver only checks four employee FK fields, so promotion, transfer, payroll, and compensation workflows cannot be assigned per employee in a consistent way.

- [ ] In `backend/apps/approvals/models.py`, add:

```python
class ApprovalWorkflowAssignment(AuditedBaseModel):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="approval_workflow_assignments",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="approval_workflow_assignments",
    )
    request_kind = models.CharField(max_length=32, choices=ApprovalRequestKind.choices)
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="employee_assignments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "approval_workflow_assignments"
        ordering = ["request_kind", "employee__employee_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "employee", "request_kind"],
                condition=Q(is_active=True),
                name="unique_active_approval_workflow_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.employee_id} {self.request_kind} -> {self.workflow_id}"
```

- [ ] In the migration, copy existing employee FK assignments into the new model with a `RunPython` operation:

```python
def forwards(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    Assignment = apps.get_model("approvals", "ApprovalWorkflowAssignment")
    mapping = {
        "LEAVE": "leave_approval_workflow_id",
        "ON_DUTY": "on_duty_approval_workflow_id",
        "ATTENDANCE_REGULARIZATION": "attendance_regularization_approval_workflow_id",
        "EXPENSE_CLAIM": "expense_approval_workflow_id",
    }
    rows = []
    for employee in Employee.objects.all().only("id", "organisation_id", *mapping.values()):
        for request_kind, field_name in mapping.items():
            workflow_id = getattr(employee, field_name)
            if workflow_id:
                rows.append(
                    Assignment(
                        organisation_id=employee.organisation_id,
                        employee_id=employee.id,
                        request_kind=request_kind,
                        workflow_id=workflow_id,
                        is_active=True,
                    )
                )
    Assignment.objects.bulk_create(rows, ignore_conflicts=True)
```

- [ ] Keep the existing employee FK fields in this phase for backward compatibility. Do not remove them until all API serializers and UI screens are migrated.
- [ ] In `backend/apps/approvals/services.py`, replace `get_employee_assigned_workflow` with:

```python
def get_employee_assigned_workflow(employee, request_kind):
    from .catalog import APPROVAL_REQUEST_KIND_CATALOG
    from .models import ApprovalWorkflowAssignment

    meta = APPROVAL_REQUEST_KIND_CATALOG.get(str(request_kind))
    if meta is None or not meta.supports_employee_assignment:
        return None

    assignment = (
        ApprovalWorkflowAssignment.objects.select_related("workflow")
        .filter(
            organisation=employee.organisation,
            employee=employee,
            request_kind=request_kind,
            is_active=True,
            workflow__is_active=True,
            workflow__organisation=employee.organisation,
        )
        .first()
    )
    return assignment.workflow if assignment else None
```

- [ ] Add a regression test in `backend/apps/approvals/tests/test_workflow_resolution.py`:

```python
def test_employee_specific_assignment_supports_promotion(employee, promotion_workflow):
    ApprovalWorkflowAssignment.objects.create(
        organisation=employee.organisation,
        employee=employee,
        request_kind=ApprovalRequestKind.PROMOTION,
        workflow=promotion_workflow,
    )

    workflow, source = resolve_workflow_with_source(employee, ApprovalRequestKind.PROMOTION)

    assert workflow == promotion_workflow
    assert source == "ASSIGNMENT"
```

- [ ] Run `docker compose run --rm backend pytest apps/approvals/tests/test_workflow_resolution.py::test_employee_specific_assignment_supports_promotion -q`.
- [ ] Expected: test passes.

## Task 4: Add Rule Fields for Amount, Grade, Cost Centre, and Legal Entity

**Why:** Expense, salary revision, promotion, and payroll workflows need amount thresholds and organisational dimensions beyond department/location.

- [ ] In `backend/apps/approvals/models.py`, add fields to `ApprovalWorkflowRule`:

```python
    min_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=120, blank=True)
    band = models.CharField(max_length=120, blank=True)
    cost_centre = models.CharField(max_length=120, blank=True)
    legal_entity = models.CharField(max_length=120, blank=True)
```

- [ ] Change `_matches_rule` in `backend/apps/approvals/services.py` to accept `amount=None` and `context=None`:

```python
def _matches_rule(rule, employee, request_kind, leave_type=None, amount=None, context=None):
    context = context or {}
    if not rule.is_active or rule.request_kind != request_kind:
        return False
    if rule.department_id and employee.department_id != rule.department_id:
        return False
    if rule.office_location_id and employee.office_location_id != rule.office_location_id:
        return False
    if rule.specific_employee_id and employee.id != rule.specific_employee_id:
        return False
    if rule.employment_type and employee.employment_type != rule.employment_type:
        return False
    if rule.designation and (employee.designation or "").strip().lower() != rule.designation.strip().lower():
        return False
    if rule.leave_type_id and (leave_type is None or leave_type.id != rule.leave_type_id):
        return False
    if rule.min_amount is not None and (amount is None or amount < rule.min_amount):
        return False
    if rule.max_amount is not None and (amount is None or amount > rule.max_amount):
        return False
    for field in ("grade", "band", "cost_centre", "legal_entity"):
        configured = getattr(rule, field)
        actual = str(context.get(field, "") or "")
        if configured and configured.strip().lower() != actual.strip().lower():
            return False
    return True
```

- [ ] Update `resolve_workflow_with_source` and `create_approval_run` signatures:

```python
def resolve_workflow_with_source(employee, request_kind, leave_type=None, amount=None, context=None):
    ...
    for rule in rules:
        if _matches_rule(rule, employee, request_kind, leave_type=leave_type, amount=amount, context=context):
            return rule.workflow, "RULE"
```

```python
def create_approval_run(subject, request_kind, requester, actor=None, leave_type=None, subject_label="", amount=None, context=None):
    workflow = resolve_workflow(requester, request_kind, leave_type=leave_type, amount=amount, context=context)
```

- [ ] Update all existing call sites to pass existing behavior unchanged. For expense claims, salary revisions, promotion requests, and payroll runs, pass the relevant total amount in `amount`.
- [ ] Add tests:

```python
def test_expense_amount_rule_wins_before_default(employee, low_value_workflow, high_value_workflow):
    ApprovalWorkflowRule.objects.create(
        workflow=high_value_workflow,
        name="High value expense",
        request_kind=ApprovalRequestKind.EXPENSE_CLAIM,
        priority=1,
        min_amount=Decimal("50000.00"),
    )
    default = ApprovalWorkflow.objects.create(
        organisation=employee.organisation,
        name="Default expense",
        is_default=True,
        default_request_kind=ApprovalRequestKind.EXPENSE_CLAIM,
    )

    workflow, source = resolve_workflow_with_source(
        employee,
        ApprovalRequestKind.EXPENSE_CLAIM,
        amount=Decimal("75000.00"),
    )

    assert workflow == high_value_workflow
    assert source == "RULE"
    assert workflow != default
```

- [ ] Run `docker compose run --rm backend pytest apps/approvals/tests/test_workflow_resolution.py -q`.
- [ ] Expected: all workflow-resolution tests pass.

## Task 5: Implement Role-Based Approver Resolution

**Why:** The new approver types must resolve to actual `ApprovalAction` rows. This task keeps workflow execution deterministic and auditable.

- [ ] In `backend/apps/approvals/services.py`, add helper functions:

```python
def _manager_at_level(employee, level):
    current = employee
    for _ in range(level):
        current = getattr(current, "reporting_to", None)
        if current is None:
            return None
    return current


def _employees_for_role(organisation, role_code):
    from .role_resolver import employees_with_permission_role

    return employees_with_permission_role(organisation, role_code)


def _department_head(employee):
    head = getattr(employee.department, "head", None) if employee.department_id else None
    return head if head and head.organisation_id == employee.organisation_id else None


def _location_admin(employee):
    from .role_resolver import employees_with_scope

    return employees_with_scope(
        employee.organisation,
        role_code="LOCATION_ADMIN",
        office_location_id=employee.office_location_id,
    ).first()
```

- [ ] In `_resolve_stage_approvers`, add branches:

```python
elif approver.approver_type == ApprovalApproverType.NTH_LEVEL_MANAGER:
    employee = _manager_at_level(requester, approver.manager_level)
    if employee:
        resolved.append(_direct_assignment(employee, request_kind))
elif approver.approver_type == ApprovalApproverType.DEPARTMENT_HEAD:
    employee = _department_head(requester)
    if employee:
        resolved.append(_direct_assignment(employee, request_kind))
elif approver.approver_type == ApprovalApproverType.LOCATION_ADMIN:
    employee = _location_admin(requester)
    if employee:
        resolved.append(_direct_assignment(employee, request_kind))
elif approver.approver_type in {
    ApprovalApproverType.HR_BUSINESS_PARTNER,
    ApprovalApproverType.PAYROLL_ADMIN,
    ApprovalApproverType.FINANCE_APPROVER,
    ApprovalApproverType.ROLE,
}:
    role_code = approver.role_code or approver.approver_type
    for employee in _employees_for_role(organisation, role_code):
        resolved.append(_direct_assignment(employee, request_kind))
```

- [ ] Until P38 is implemented, create `backend/apps/approvals/role_resolver.py` compatibility shims used only by approvals:

```python
def employees_with_permission_role(organisation, role_code):
    from apps.employees.models import Employee

    if role_code in {"HR_BUSINESS_PARTNER", "PAYROLL_ADMIN", "FINANCE_APPROVER", "LOCATION_ADMIN"}:
        return Employee.objects.filter(
            organisation=organisation,
            user__organisation_memberships__organisation=organisation,
            user__organisation_memberships__is_org_admin=True,
            user__organisation_memberships__status="ACTIVE",
        ).select_related("user")
    return Employee.objects.none()


def employees_with_scope(organisation, role_code, **scope):
    return employees_with_permission_role(organisation, role_code)
```

- [ ] Add a clear follow-up note in P38 to replace these shims with real role assignments.
- [ ] Add tests for `NTH_LEVEL_MANAGER`, `DEPARTMENT_HEAD`, `PAYROLL_ADMIN`, and unresolved fallback.

## Task 6: Add Workflow Simulation Endpoint

**Why:** Admins need to preview "who will approve this?" before enabling a workflow. This prevents broken workflows where approvers are missing.

- [ ] In `backend/apps/approvals/serializers.py`, add:

```python
class ApprovalWorkflowSimulationRequestSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    request_kind = serializers.ChoiceField(choices=ApprovalRequestKind.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    leave_type_id = serializers.UUIDField(required=False)
    grade = serializers.CharField(required=False, allow_blank=True)
    band = serializers.CharField(required=False, allow_blank=True)
    cost_centre = serializers.CharField(required=False, allow_blank=True)
    legal_entity = serializers.CharField(required=False, allow_blank=True)


class ApprovalWorkflowSimulationStageSerializer(serializers.Serializer):
    sequence = serializers.IntegerField()
    name = serializers.CharField()
    mode = serializers.CharField()
    approvers = serializers.ListField(child=serializers.DictField())
    warnings = serializers.ListField(child=serializers.CharField())
```

- [ ] In `backend/apps/approvals/services.py`, add:

```python
def simulate_workflow(employee, request_kind, *, amount=None, leave_type=None, context=None):
    workflow, source = resolve_workflow_with_source(
        employee,
        request_kind,
        leave_type=leave_type,
        amount=amount,
        context=context,
    )
    stages = []
    for stage in workflow.stages.prefetch_related("approvers__approver_employee__user").order_by("sequence"):
        approvers = _resolve_stage_approvers(stage, employee, employee.organisation, request_kind)
        warnings = []
        if not approvers:
            warnings.append("No approver resolved for this stage.")
        stages.append(
            {
                "sequence": stage.sequence,
                "name": stage.name,
                "mode": stage.mode,
                "approvers": [
                    {
                        "employee_id": str(item["approver_employee"].id) if item["approver_employee"] else None,
                        "user_id": str(item["approver_user"].id),
                        "name": item["approver_user"].get_full_name() or item["approver_user"].email,
                        "assignment_source": item["assignment_source"],
                    }
                    for item in approvers
                ],
                "warnings": warnings,
            }
        )
    return {"workflow_id": str(workflow.id), "workflow_name": workflow.name, "source": source, "stages": stages}
```

- [ ] In `backend/apps/approvals/views.py`, add `OrgApprovalWorkflowSimulationView` with `permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]`.
- [ ] Register `path("workflows/simulate/", OrgApprovalWorkflowSimulationView.as_view(), name="org-approval-workflow-simulate")`.
- [ ] Add API test:

```python
def test_org_admin_can_simulate_three_stage_salary_revision(api_client, org_admin_user, employee):
    api_client.force_authenticate(org_admin_user)
    response = api_client.post(
        "/api/org/approvals/workflows/simulate/",
        {
            "employee_id": str(employee.id),
            "request_kind": "SALARY_REVISION",
            "amount": "120000.00",
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.data["workflow_name"]
    assert len(response.data["stages"]) >= 2
```

## Task 7: Add Workflow Readiness and Presets APIs

**Why:** Admins need to see whether every request kind has a safe workflow before production use. This also lets onboarding block critical HR flows until configured.

- [ ] In `backend/apps/approvals/services.py`, add:

```python
def get_workflow_readiness(organisation):
    from .catalog import APPROVAL_REQUEST_KIND_CATALOG

    result = []
    for meta in APPROVAL_REQUEST_KIND_CATALOG.values():
        default = get_default_workflow(organisation, meta.kind)
        active_rules = ApprovalWorkflowRule.objects.filter(
            workflow__organisation=organisation,
            request_kind=meta.kind,
            is_active=True,
            workflow__is_active=True,
        ).count()
        result.append(
            {
                "kind": meta.kind,
                "label": meta.label,
                "module": meta.module,
                "requires_default_workflow": meta.requires_default_workflow,
                "has_default_workflow": default is not None,
                "default_workflow_id": str(default.id) if default else None,
                "active_rule_count": active_rules,
                "ready": (default is not None) if meta.requires_default_workflow else True,
            }
        )
    return result
```

- [ ] Add `OrgApprovalWorkflowCatalogView`, `OrgApprovalWorkflowPresetView`, and `OrgApprovalWorkflowReadinessView`.
- [ ] Catalog response shape:

```json
{
  "request_kinds": [
    {
      "kind": "PROMOTION",
      "label": "Promotion",
      "module": "Employee Lifecycle",
      "requires_default_workflow": true,
      "supports_employee_assignment": true,
      "supports_amount_rules": true,
      "supports_leave_type_rules": false,
      "recommended_minimum_stages": 2
    }
  ],
  "approver_types": ["REPORTING_MANAGER", "NTH_LEVEL_MANAGER", "DEPARTMENT_HEAD", "PAYROLL_ADMIN"],
  "fallback_types": ["NONE", "REPORTING_MANAGER", "ROLE", "PRIMARY_ORG_ADMIN"],
  "stage_modes": ["ALL", "ANY"]
}
```

- [ ] Readiness test:

```python
def test_readiness_requires_all_catalog_request_kinds(organisation):
    readiness = get_workflow_readiness(organisation)
    required = {item["kind"] for item in readiness if item["requires_default_workflow"]}

    assert required == {
        "LEAVE",
        "ON_DUTY",
        "ATTENDANCE_REGULARIZATION",
        "EXPENSE_CLAIM",
        "PAYROLL_PROCESSING",
        "SALARY_REVISION",
        "COMPENSATION_TEMPLATE_CHANGE",
        "PROMOTION",
        "TRANSFER",
    }
```

## Task 8: Productize the Frontend Builder for Every Request Kind

**Why:** The backend can only be useful if org admins can configure it without API access.

- [ ] In `frontend/src/types/hr.ts`, update:

```ts
export type ApprovalRequestKind =
  | 'LEAVE'
  | 'ON_DUTY'
  | 'ATTENDANCE_REGULARIZATION'
  | 'EXPENSE_CLAIM'
  | 'PAYROLL_PROCESSING'
  | 'SALARY_REVISION'
  | 'COMPENSATION_TEMPLATE_CHANGE'
  | 'PROMOTION'
  | 'TRANSFER'
```

- [ ] In `frontend/src/lib/api/approvals.ts`, add:

```ts
export interface ApprovalRequestKindMeta {
  kind: ApprovalRequestKind
  label: string
  module: string
  requires_default_workflow: boolean
  supports_employee_assignment: boolean
  supports_amount_rules: boolean
  supports_leave_type_rules: boolean
  recommended_minimum_stages: number
}

export async function fetchApprovalWorkflowCatalog(): Promise<ApprovalWorkflowCatalog> {
  const { data } = await api.get('/org/approvals/workflows/catalog/')
  return data
}

export async function simulateApprovalWorkflow(payload: ApprovalWorkflowSimulationRequest): Promise<ApprovalWorkflowSimulationResult> {
  const { data } = await api.post('/org/approvals/workflows/simulate/', payload)
  return data
}
```

- [ ] In `frontend/src/pages/org/ApprovalWorkflowBuilderPage.tsx`, replace local request-kind options with catalog data:

```tsx
const { data: catalog } = useQuery({
  queryKey: ['approval-workflow-catalog'],
  queryFn: fetchApprovalWorkflowCatalog,
})

const requestKindOptions = catalog?.request_kinds ?? APPROVAL_REQUEST_KIND_OPTIONS.map((kind) => ({
  kind,
  label: labelForApprovalRequestKind(kind),
  module: 'Core',
  requires_default_workflow: true,
  supports_employee_assignment: true,
  supports_amount_rules: false,
  supports_leave_type_rules: kind === 'LEAVE',
  recommended_minimum_stages: 1,
}))
```

- [ ] Add grouped request-kind dropdown labels:

```tsx
{Object.entries(groupBy(requestKindOptions, (option) => option.module)).map(([module, options]) => (
  <optgroup key={module} label={module}>
    {options.map((option) => (
      <option key={option.kind} value={option.kind}>
        {option.label}
      </option>
    ))}
  </optgroup>
))}
```

- [ ] Show amount fields only when `supports_amount_rules` is true. Show leave type only when `supports_leave_type_rules` is true.
- [ ] Add a "Preview approvers" panel that calls `simulateApprovalWorkflow` with selected employee, request kind, amount, and routing context.
- [ ] Add UI test:

```ts
it('shows promotion and transfer as configurable workflow types', async () => {
  render(<ApprovalWorkflowBuilderPage />)

  expect(await screen.findByRole('option', { name: /Promotion/i })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: /Transfer/i })).toBeInTheDocument()
})
```

## Task 9: Add Readiness Page

**Why:** This is the operational control surface for org admins and CT onboarding teams.

- [ ] Create `frontend/src/pages/org/ApprovalWorkflowReadinessPage.tsx`:

```tsx
export function ApprovalWorkflowReadinessPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['approval-workflow-readiness'],
    queryFn: fetchApprovalWorkflowReadiness,
  })

  if (isLoading) return <PageLoader label="Loading workflow readiness" />

  const rows = data ?? []
  const missing = rows.filter((row) => !row.ready)

  return (
    <OrgPageShell title="Approval Workflow Readiness">
      <section className="rounded-xl border bg-white p-4">
        <h2 className="text-lg font-semibold">Coverage</h2>
        <p className="text-sm text-slate-600">
          {missing.length === 0
            ? 'Every request kind has an active default workflow.'
            : `${missing.length} request kind${missing.length === 1 ? '' : 's'} need configuration.`}
        </p>
      </section>
      <DataTable
        columns={[
          { key: 'module', header: 'Module' },
          { key: 'label', header: 'Request type' },
          { key: 'has_default_workflow', header: 'Default workflow' },
          { key: 'active_rule_count', header: 'Rules' },
          { key: 'ready', header: 'Ready' },
        ]}
        rows={rows}
      />
    </OrgPageShell>
  )
}
```

- [ ] Register `/org/settings/approval-readiness`.
- [ ] Add a settings link next to the existing workflow builder link.
- [ ] Add test:

```ts
it('flags missing workflow defaults', async () => {
  mockApprovalReadiness([
    { kind: 'LEAVE', label: 'Leave', module: 'Time Off', ready: true },
    { kind: 'PROMOTION', label: 'Promotion', module: 'Employee Lifecycle', ready: false },
  ])

  render(<ApprovalWorkflowReadinessPage />)

  expect(await screen.findByText('1 request kind needs configuration.')).toBeInTheDocument()
  expect(screen.getByText('Promotion')).toBeInTheDocument()
})
```

## Task 10: Cover Every Subject Flow With Integration Tests

**Why:** The catalog is only credible if every business module can actually start an approval run using the configured workflow.

- [ ] Add or update tests that assert each subject flow calls `create_approval_run` with the correct kind:

```python
@pytest.mark.parametrize(
    "request_kind",
    [
        ApprovalRequestKind.LEAVE,
        ApprovalRequestKind.ON_DUTY,
        ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
        ApprovalRequestKind.EXPENSE_CLAIM,
        ApprovalRequestKind.PAYROLL_PROCESSING,
        ApprovalRequestKind.SALARY_REVISION,
        ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
        ApprovalRequestKind.PROMOTION,
        ApprovalRequestKind.TRANSFER,
    ],
)
def test_every_catalog_kind_has_default_workflow_fixture(organisation, request_kind):
    workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name=f"Default {request_kind}",
        is_default=True,
        default_request_kind=request_kind,
        is_active=True,
    )
    ApprovalStage.objects.create(
        workflow=workflow,
        name="Stage 1",
        sequence=1,
        mode=ApprovalStageMode.ALL,
        fallback_type=ApprovalFallbackType.PRIMARY_ORG_ADMIN,
    )

    assert get_default_workflow(organisation, request_kind) == workflow
```

- [ ] Add module-specific tests for:
  - `backend/apps/timeoff/tests/test_services.py`: leave and on duty
  - `backend/apps/attendance/tests/test_services.py`: attendance regularization
  - `backend/apps/expenses/tests/test_services.py`: expense claim with amount context
  - `backend/apps/payroll/tests/test_services.py`: salary revision, compensation template change, payroll processing
  - `backend/apps/employees/tests/test_services.py`: promotion and transfer
- [ ] Run `docker compose run --rm backend pytest apps/approvals/tests apps/timeoff/tests apps/attendance/tests apps/expenses/tests apps/payroll/tests apps/employees/tests -q`.
- [ ] Expected: all tests pass.

## Task 11: Docker Verification

- [ ] Rebuild backend and frontend images:

```bash
docker compose build backend frontend
```

- [ ] Recreate services:

```bash
docker compose up -d --force-recreate backend frontend
```

- [ ] Run backend approval tests:

```bash
docker compose run --rm backend pytest apps/approvals/tests -q
```

- [ ] Run affected backend module tests:

```bash
docker compose run --rm backend pytest apps/timeoff/tests apps/attendance/tests apps/expenses/tests apps/payroll/tests apps/employees/tests -q
```

- [ ] Run frontend tests:

```bash
docker compose run --rm frontend npm run test -- ApprovalWorkflowBuilderPage ApprovalWorkflowReadinessPage
```

- [ ] Run lint/typecheck:

```bash
docker compose run --rm frontend npm run check
```

- [ ] Expected: all commands exit 0.

## Implementation Order

1. Task 1 catalog first, because backend and frontend both depend on it.
2. Tasks 2-5 backend schema and engine changes.
3. Tasks 6-7 admin APIs.
4. Tasks 8-9 frontend admin UX.
5. Task 10 integration coverage.
6. Task 11 Docker verification.

## Self-Review Checklist for Workers

- [ ] The catalog contains exactly the same request kinds as `ApprovalRequestKind.choices`.
- [ ] `PROMOTION` and `TRANSFER` are present in backend API responses and frontend dropdowns.
- [ ] Multi-stage workflows with 2 and 3 approval levels are covered by tests.
- [ ] A missing approver creates a simulation warning before the workflow is used.
- [ ] Existing leave, on-duty, attendance, expense, payroll, salary revision, compensation template, promotion, and transfer flows still create approval runs.
- [ ] No org can reference another org's employee, department, office location, leave type, or workflow in workflow rules or assignments.
