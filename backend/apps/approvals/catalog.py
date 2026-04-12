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
    name='Manager review',
    sequence=1,
    mode=ApprovalStageMode.ALL,
    approver_types=('REPORTING_MANAGER',),
)

HR_STAGE = ApprovalStagePreset(
    name='HR review',
    sequence=2,
    mode=ApprovalStageMode.ALL,
    approver_types=('PRIMARY_ORG_ADMIN',),
)

FINANCE_STAGE = ApprovalStagePreset(
    name='Finance review',
    sequence=2,
    mode=ApprovalStageMode.ALL,
    approver_types=('FINANCE_APPROVER',),
)

PAYROLL_STAGE = ApprovalStagePreset(
    name='Payroll review',
    sequence=2,
    mode=ApprovalStageMode.ALL,
    approver_types=('PAYROLL_ADMIN',),
)


APPROVAL_REQUEST_KIND_CATALOG: dict[str, ApprovalRequestKindMeta] = {
    ApprovalRequestKind.LEAVE: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.LEAVE,
        label='Leave',
        module='Time Off',
        subject_label='Leave request',
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=False,
        supports_leave_type_rules=True,
        recommended_minimum_stages=1,
        presets=(MANAGER_STAGE, HR_STAGE),
    ),
    ApprovalRequestKind.ON_DUTY: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.ON_DUTY,
        label='On Duty',
        module='Attendance',
        subject_label='On-duty request',
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=False,
        supports_leave_type_rules=False,
        recommended_minimum_stages=1,
        presets=(MANAGER_STAGE, HR_STAGE),
    ),
    ApprovalRequestKind.ATTENDANCE_REGULARIZATION: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
        label='Attendance Regularization',
        module='Attendance',
        subject_label='Attendance regularization request',
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=False,
        supports_leave_type_rules=False,
        recommended_minimum_stages=1,
        presets=(MANAGER_STAGE, HR_STAGE),
    ),
    ApprovalRequestKind.EXPENSE_CLAIM: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.EXPENSE_CLAIM,
        label='Expense Claim',
        module='Expense',
        subject_label='Expense claim',
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(MANAGER_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.PAYROLL_PROCESSING: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.PAYROLL_PROCESSING,
        label='Payroll Processing',
        module='Payroll',
        subject_label='Payroll run',
        requires_default_workflow=True,
        supports_employee_assignment=False,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(PAYROLL_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.SALARY_REVISION: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.SALARY_REVISION,
        label='Salary Revision',
        module='Payroll',
        subject_label='Salary revision',
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(MANAGER_STAGE, PAYROLL_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
        label='Compensation Template Change',
        module='Payroll',
        subject_label='Compensation template change',
        requires_default_workflow=True,
        supports_employee_assignment=False,
        supports_amount_rules=False,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(PAYROLL_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.PROMOTION: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.PROMOTION,
        label='Promotion',
        module='Employee Lifecycle',
        subject_label='Promotion request',
        requires_default_workflow=True,
        supports_employee_assignment=True,
        supports_amount_rules=True,
        supports_leave_type_rules=False,
        recommended_minimum_stages=2,
        presets=(MANAGER_STAGE, HR_STAGE, FINANCE_STAGE),
    ),
    ApprovalRequestKind.TRANSFER: ApprovalRequestKindMeta(
        kind=ApprovalRequestKind.TRANSFER,
        label='Transfer',
        module='Employee Lifecycle',
        subject_label='Transfer request',
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
