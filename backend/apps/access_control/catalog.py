from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    label: str
    domain: str
    resource: str
    action: str
    description: str


@dataclass(frozen=True)
class SeedRoleSpec:
    code: str
    scope: str
    name: str
    description: str
    permissions: tuple[str, ...]


PERMISSIONS: tuple[PermissionSpec, ...] = (
    PermissionSpec("ct.organisations.read", "Read organisations", "ct", "organisations", "read", "View tenant records in Control Tower."),
    PermissionSpec("ct.organisations.write", "Manage organisations", "ct", "organisations", "write", "Create and update tenant records."),
    PermissionSpec("ct.billing.read", "Read billing", "ct", "billing", "read", "View licences, invoices, and payments."),
    PermissionSpec("ct.billing.write", "Manage billing", "ct", "billing", "write", "Modify licences, payment state, and billing settings."),
    PermissionSpec("ct.impersonation.start", "Start impersonation", "ct", "impersonation", "start", "Start a scoped Control Tower act-as session."),
    PermissionSpec("ct.audit.read", "Read CT audit", "ct", "audit", "read", "View Control Tower audit logs."),
    PermissionSpec("org.employees.read", "Read employees", "org", "employees", "read", "View employee profiles within assigned scope."),
    PermissionSpec("org.employees.write", "Manage employees", "org", "employees", "write", "Create and edit employee records within assigned scope."),
    PermissionSpec(
        "org.employee_sensitive.read",
        "Read sensitive employee fields",
        "org",
        "employees",
        "read_sensitive",
        "View compensation, identifiers, bank, and personal fields.",
    ),
    PermissionSpec("org.payroll.read", "Read payroll", "org", "payroll", "read", "View payroll data within assigned scope."),
    PermissionSpec("org.payroll.process", "Process payroll", "org", "payroll", "process", "Calculate, finalize, and publish payroll."),
    PermissionSpec("org.expenses.read", "Read expenses", "org", "expenses", "read", "View expense claims within assigned scope."),
    PermissionSpec("org.expenses.approve", "Approve expenses", "org", "expenses", "approve", "Approve assigned expense claims."),
    PermissionSpec(
        "org.approvals.workflow.manage",
        "Manage approval workflows",
        "org",
        "approvals",
        "workflow_manage",
        "Create and edit workflow definitions.",
    ),
    PermissionSpec(
        "org.approvals.action.approve",
        "Act on approvals",
        "org",
        "approvals",
        "approve",
        "Approve or reject assigned approval actions.",
    ),
    PermissionSpec("org.reports.read", "Read reports", "org", "reports", "read", "View reports allowed by role and data scope."),
    PermissionSpec(
        "org.reports.builder.manage",
        "Manage report templates",
        "org",
        "reports",
        "builder_manage",
        "Create, edit, and share report templates.",
    ),
    PermissionSpec("org.reports.export", "Export reports", "org", "reports", "export", "Export report data."),
    PermissionSpec("org.access_control.manage", "Manage org access", "org", "access_control", "manage", "Assign org roles and data scopes."),
    PermissionSpec("org.audit.read", "Read org audit", "org", "audit", "read", "View organisation audit logs."),
)


SEED_ROLES: dict[str, SeedRoleSpec] = {
    "CT_SUPER_ADMIN": SeedRoleSpec(
        code="CT_SUPER_ADMIN",
        scope="CONTROL_TOWER",
        name="Control Tower Super Admin",
        description="Full Control Tower access.",
        permissions=tuple(permission.code for permission in PERMISSIONS if permission.domain == "ct"),
    ),
    "CT_READ_ONLY": SeedRoleSpec(
        code="CT_READ_ONLY",
        scope="CONTROL_TOWER",
        name="Control Tower Read Only",
        description="Read-only CT visibility.",
        permissions=("ct.organisations.read", "ct.billing.read", "ct.audit.read"),
    ),
    "CT_SUPPORT": SeedRoleSpec(
        code="CT_SUPPORT",
        scope="CONTROL_TOWER",
        name="Control Tower Support",
        description="Tenant support with impersonation access.",
        permissions=("ct.organisations.read", "ct.impersonation.start", "ct.audit.read"),
    ),
    "CT_IMPLEMENTATION": SeedRoleSpec(
        code="CT_IMPLEMENTATION",
        scope="CONTROL_TOWER",
        name="Implementation Admin",
        description="Tenant implementation and setup management.",
        permissions=("ct.organisations.read", "ct.organisations.write", "ct.impersonation.start"),
    ),
    "CT_BILLING": SeedRoleSpec(
        code="CT_BILLING",
        scope="CONTROL_TOWER",
        name="Billing Admin",
        description="Billing administration.",
        permissions=("ct.organisations.read", "ct.billing.read", "ct.billing.write"),
    ),
    "CT_COMPLIANCE_AUDITOR": SeedRoleSpec(
        code="CT_COMPLIANCE_AUDITOR",
        scope="CONTROL_TOWER",
        name="Compliance Auditor",
        description="Read-only compliance visibility.",
        permissions=("ct.organisations.read", "ct.billing.read", "ct.audit.read"),
    ),
    "ORG_OWNER": SeedRoleSpec(
        code="ORG_OWNER",
        scope="ORGANISATION",
        name="Organisation Owner",
        description="Full organisation administration.",
        permissions=tuple(permission.code for permission in PERMISSIONS if permission.domain == "org"),
    ),
    "ORG_HR_ADMIN": SeedRoleSpec(
        code="ORG_HR_ADMIN",
        scope="ORGANISATION",
        name="HR Admin",
        description="Employee and workflow administration.",
        permissions=(
            "org.employees.read",
            "org.employees.write",
            "org.employee_sensitive.read",
            "org.approvals.workflow.manage",
            "org.reports.read",
        ),
    ),
    "ORG_PAYROLL_ADMIN": SeedRoleSpec(
        code="ORG_PAYROLL_ADMIN",
        scope="ORGANISATION",
        name="Payroll Admin",
        description="Payroll and statutory administration.",
        permissions=(
            "org.employees.read",
            "org.employee_sensitive.read",
            "org.payroll.read",
            "org.payroll.process",
            "org.reports.read",
            "org.reports.export",
        ),
    ),
    "ORG_FINANCE_APPROVER": SeedRoleSpec(
        code="ORG_FINANCE_APPROVER",
        scope="ORGANISATION",
        name="Finance Approver",
        description="Expense and approval action handling.",
        permissions=("org.expenses.read", "org.expenses.approve", "org.approvals.action.approve", "org.reports.read"),
    ),
    "ORG_MANAGER": SeedRoleSpec(
        code="ORG_MANAGER",
        scope="ORGANISATION",
        name="Manager",
        description="Manager access with approval actions.",
        permissions=("org.employees.read", "org.approvals.action.approve", "org.expenses.approve", "org.reports.read"),
    ),
    "ORG_RECRUITER": SeedRoleSpec(
        code="ORG_RECRUITER",
        scope="ORGANISATION",
        name="Recruiter",
        description="Recruitment-facing workforce access.",
        permissions=("org.employees.read", "org.reports.read"),
    ),
    "ORG_ASSET_ADMIN": SeedRoleSpec(
        code="ORG_ASSET_ADMIN",
        scope="ORGANISATION",
        name="Asset Admin",
        description="Asset-facing workforce access.",
        permissions=("org.employees.read", "org.reports.read"),
    ),
    "ORG_REPORTS_ANALYST": SeedRoleSpec(
        code="ORG_REPORTS_ANALYST",
        scope="ORGANISATION",
        name="Reports Analyst",
        description="Report builder and export access.",
        permissions=("org.reports.read", "org.reports.builder.manage", "org.reports.export"),
    ),
    "ORG_AUDITOR_READ_ONLY": SeedRoleSpec(
        code="ORG_AUDITOR_READ_ONLY",
        scope="ORGANISATION",
        name="Read Only Auditor",
        description="Read-only audit and reporting access.",
        permissions=("org.employees.read", "org.payroll.read", "org.expenses.read", "org.reports.read", "org.audit.read"),
    ),
}
