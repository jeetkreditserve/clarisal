from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.approvals.models import ApprovalRequestKind, ApprovalRun, ApprovalRunStatus
from apps.approvals.services import cancel_approval_run, get_default_workflow
from apps.audit.services import log_audit_event
from apps.employees.models import Employee, EmployeeStatus, GovernmentIdType

from .models import (
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationAssignmentStatus,
    CompensationTemplate,
    CompensationTemplateLine,
    CompensationTemplateStatus,
    PayrollComponent,
    PayrollComponentType,
    PayrollRun,
    PayrollRunItem,
    PayrollRunItemStatus,
    PayrollRunStatus,
    PayrollRunType,
    PayrollTaxSlab,
    PayrollTaxSlabSet,
    Payslip,
)

ZERO = Decimal('0.00')
DEFAULT_FISCAL_YEAR = '2026-2027'
DEFAULT_COMPONENTS = [
    {'code': 'BASIC', 'name': 'Basic Pay', 'component_type': PayrollComponentType.EARNING, 'is_taxable': True},
    {'code': 'HRA', 'name': 'House Rent Allowance', 'component_type': PayrollComponentType.EARNING, 'is_taxable': True},
    {'code': 'PF_EMPLOYEE', 'name': 'Employee PF', 'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION, 'is_taxable': False},
    {'code': 'PF_EMPLOYER', 'name': 'Employer PF', 'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION, 'is_taxable': False},
]
DEFAULT_TAX_SLABS = [
    {'min_income': Decimal('0.00'), 'max_income': Decimal('300000.00'), 'rate_percent': Decimal('0.00')},
    {'min_income': Decimal('300000.00'), 'max_income': Decimal('700000.00'), 'rate_percent': Decimal('10.00')},
    {'min_income': Decimal('700000.00'), 'max_income': None, 'rate_percent': Decimal('20.00')},
]


def _normalize_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal('0.01'))
    return Decimal(str(value)).quantize(Decimal('0.01'))


def _fiscal_year_for_period(period_year, period_month):
    if period_month >= 4:
        return f'{period_year}-{period_year + 1}'
    return f'{period_year - 1}-{period_year}'


def _get_or_create_component(organisation, payload):
    component, _ = PayrollComponent.objects.get_or_create(
        organisation=organisation,
        code=payload['component_code'],
        defaults={
            'name': payload['name'],
            'component_type': payload['component_type'],
            'is_taxable': payload.get('is_taxable', True),
            'is_system_default': False,
        },
    )
    changed = False
    for field, key in (
        ('name', 'name'),
        ('component_type', 'component_type'),
        ('is_taxable', 'is_taxable'),
    ):
        expected = payload.get(key, getattr(component, field))
        if getattr(component, field) != expected:
            setattr(component, field, expected)
            changed = True
    if changed:
        component.save()
    return component


def _build_rendered_payslip(snapshot):
    lines = [
        f"Payslip: {snapshot['period_label']}",
        f"Employee: {snapshot['employee_name']}",
        f"Gross Pay: {snapshot['gross_pay']}",
        f"Income Tax: {snapshot['income_tax']}",
        f"Total Deductions: {snapshot['total_deductions']}",
        f"Net Pay: {snapshot['net_pay']}",
    ]
    return '\n'.join(lines)


def _calculate_annual_tax(tax_slab_set, annual_taxable_income):
    taxable = _normalize_decimal(annual_taxable_income) or ZERO
    annual_tax = ZERO
    for slab in tax_slab_set.slabs.order_by('min_income', 'created_at'):
        slab_start = slab.min_income
        slab_end = slab.max_income
        if taxable <= slab_start:
            continue
        upper_bound = taxable if slab_end is None else min(taxable, slab_end)
        taxable_slice = upper_bound - slab_start
        if taxable_slice <= ZERO:
            continue
        annual_tax += taxable_slice * (slab.rate_percent / Decimal('100.00'))
        if slab_end is None or taxable <= slab_end:
            break
    return annual_tax.quantize(Decimal('0.01'))


def _get_active_tax_slab_set(organisation, fiscal_year):
    tax_slab_set = PayrollTaxSlabSet.objects.filter(
        organisation=organisation,
        fiscal_year=fiscal_year,
        is_active=True,
    ).order_by('-created_at').first()
    if tax_slab_set:
        return tax_slab_set
    return PayrollTaxSlabSet.objects.filter(
        organisation=organisation,
        is_active=True,
    ).order_by('-created_at').first()


def _ensure_global_default_tax_master(actor=None):
    tax_slab_set = PayrollTaxSlabSet.objects.filter(
        organisation__isnull=True,
        is_system_master=True,
        is_active=True,
        country_code='IN',
    ).order_by('-created_at').first()
    if tax_slab_set:
        return tax_slab_set
    return create_tax_slab_set(
        fiscal_year=DEFAULT_FISCAL_YEAR,
        name='Default India Payroll Master',
        country_code='IN',
        slabs=DEFAULT_TAX_SLABS,
        actor=actor,
        organisation=None,
        is_active=True,
    )


def _resolve_payroll_requester_context(requester_user=None, requester_employee=None, organisation=None):
    if requester_employee is not None:
        return requester_employee.organisation, requester_user or requester_employee.user, requester_employee
    if requester_user is None or organisation is None:
        raise ValueError('A payroll requester user and organisation are required.')
    return organisation, requester_user, None


def _create_payroll_approval_run(subject, request_kind, organisation, requester_user, requester_employee=None, subject_label=''):
    workflow = get_default_workflow(organisation, request_kind)
    if workflow is None:
        raise ValueError(f'No active default approval workflow is configured for {request_kind.lower().replace("_", " ")} requests.')
    first_stage = workflow.stages.prefetch_related('approvers__approver_employee__user').order_by('sequence').first()
    if first_stage is None:
        raise ValueError('The selected approval workflow does not contain any stages.')

    with transaction.atomic():
        approval_run = ApprovalRun.objects.create(
            organisation=organisation,
            workflow=workflow,
            request_kind=request_kind,
            requested_by=requester_employee,
            requested_by_user=requester_user,
            status=ApprovalRunStatus.PENDING,
            current_stage_sequence=first_stage.sequence,
            subject_label=subject_label or str(subject),
            content_type=ContentType.objects.get_for_model(subject.__class__),
            object_id=subject.id,
        )
        from apps.approvals.services import _create_stage_actions

        _create_stage_actions(approval_run, first_stage)

    log_audit_event(
        requester_user,
        'approval.run.created',
        organisation=organisation,
        target=approval_run,
        payload={'request_kind': request_kind, 'workflow_id': str(workflow.id)},
    )
    return approval_run


def ensure_org_payroll_setup(organisation, actor=None):
    master = _ensure_global_default_tax_master(actor=actor)
    org_tax_slab_set = PayrollTaxSlabSet.objects.filter(organisation=organisation, is_active=True).order_by('-created_at').first()
    if org_tax_slab_set is None:
        org_tax_slab_set = create_tax_slab_set(
            fiscal_year=master.fiscal_year,
            name=f'{master.name} • {organisation.name}',
            country_code=master.country_code,
            slabs=[
                {
                    'min_income': slab.min_income,
                    'max_income': slab.max_income,
                    'rate_percent': slab.rate_percent,
                }
                for slab in master.slabs.all()
            ],
            actor=actor,
            organisation=organisation,
            source_set=master,
            is_active=True,
        )

    components = []
    for payload in DEFAULT_COMPONENTS:
        component, _ = PayrollComponent.objects.get_or_create(
            organisation=organisation,
            code=payload['code'],
            defaults={
                'name': payload['name'],
                'component_type': payload['component_type'],
                'is_taxable': payload['is_taxable'],
                'is_system_default': True,
            },
        )
        components.append(component)
    return {'tax_slab_set': org_tax_slab_set, 'components': components}


def create_tax_slab_set(*, fiscal_year, name, country_code, slabs, actor=None, organisation=None, source_set=None, is_active=True):
    if not slabs:
        raise ValueError('At least one tax slab is required.')
    is_system_master = organisation is None
    with transaction.atomic():
        tax_slab_set = PayrollTaxSlabSet.objects.create(
            organisation=organisation,
            source_set=source_set,
            name=name,
            country_code=country_code,
            fiscal_year=fiscal_year,
            is_active=is_active,
            is_system_master=is_system_master,
        )
        for slab in slabs:
            PayrollTaxSlab.objects.create(
                slab_set=tax_slab_set,
                min_income=_normalize_decimal(slab['min_income']),
                max_income=_normalize_decimal(slab.get('max_income')),
                rate_percent=_normalize_decimal(slab['rate_percent']),
            )
    log_audit_event(actor, 'payroll.tax_slab_set.created', organisation=organisation, target=tax_slab_set)
    return tax_slab_set


def update_tax_slab_set(tax_slab_set, *, name=None, fiscal_year=None, is_active=None, slabs=None, actor=None):
    if name is not None:
        tax_slab_set.name = name
    if fiscal_year is not None:
        tax_slab_set.fiscal_year = fiscal_year
    if is_active is not None:
        tax_slab_set.is_active = is_active
    tax_slab_set.save()
    if slabs is not None:
        tax_slab_set.slabs.all().delete()
        for slab in slabs:
            PayrollTaxSlab.objects.create(
                slab_set=tax_slab_set,
                min_income=_normalize_decimal(slab['min_income']),
                max_income=_normalize_decimal(slab.get('max_income')),
                rate_percent=_normalize_decimal(slab['rate_percent']),
            )
    log_audit_event(actor, 'payroll.tax_slab_set.updated', organisation=tax_slab_set.organisation, target=tax_slab_set)
    return tax_slab_set


def create_compensation_template(organisation, *, name, description='', lines, actor=None):
    ensure_org_payroll_setup(organisation, actor=actor)
    if not lines:
        raise ValueError('At least one compensation line is required.')
    with transaction.atomic():
        template = CompensationTemplate.objects.create(
            organisation=organisation,
            name=name,
            description=description,
            status=CompensationTemplateStatus.DRAFT,
        )
        for index, line in enumerate(lines, start=1):
            component = _get_or_create_component(organisation, line)
            CompensationTemplateLine.objects.create(
                template=template,
                component=component,
                monthly_amount=_normalize_decimal(line['monthly_amount']),
                sequence=index,
            )
    log_audit_event(actor, 'payroll.compensation_template.created', organisation=organisation, target=template)
    return template


def update_compensation_template(template, *, name=None, description=None, lines=None, actor=None):
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if template.status == CompensationTemplateStatus.APPROVED:
        template.status = CompensationTemplateStatus.DRAFT
    template.save()
    if lines is not None:
        template.lines.all().delete()
        for index, line in enumerate(lines, start=1):
            component = _get_or_create_component(template.organisation, line)
            CompensationTemplateLine.objects.create(
                template=template,
                component=component,
                monthly_amount=_normalize_decimal(line['monthly_amount']),
                sequence=index,
            )
    log_audit_event(actor, 'payroll.compensation_template.updated', organisation=template.organisation, target=template)
    return template


def submit_compensation_template_for_approval(template, *, requester_user, requester_employee=None):
    if template.status not in [CompensationTemplateStatus.DRAFT, CompensationTemplateStatus.REJECTED]:
        raise ValueError('Only draft or rejected templates can be submitted for approval.')
    organisation, requester_user, requester_employee = _resolve_payroll_requester_context(
        requester_user=requester_user,
        requester_employee=requester_employee,
        organisation=template.organisation,
    )
    approval_run = _create_payroll_approval_run(
        template,
        ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
        organisation,
        requester_user,
        requester_employee=requester_employee,
        subject_label=template.name,
    )
    template.approval_run = approval_run
    template.status = CompensationTemplateStatus.PENDING_APPROVAL
    template.save(update_fields=['approval_run', 'status', 'modified_at'])
    return template


def assign_employee_compensation(employee, template, *, effective_from, actor=None, auto_approve=False):
    version = employee.compensation_assignments.count() + 1
    with transaction.atomic():
        assignment = CompensationAssignment.objects.create(
            employee=employee,
            template=template,
            effective_from=effective_from,
            version=version,
            status=CompensationAssignmentStatus.APPROVED if auto_approve else CompensationAssignmentStatus.DRAFT,
        )
        for line in template.lines.select_related('component').all():
            CompensationAssignmentLine.objects.create(
                assignment=assignment,
                component=line.component,
                component_name=line.component.name,
                component_type=line.component.component_type,
                monthly_amount=line.monthly_amount,
                is_taxable=line.component.is_taxable,
                sequence=line.sequence,
            )
    log_audit_event(actor, 'payroll.compensation_assignment.created', organisation=employee.organisation, target=assignment)
    return assignment


def submit_compensation_assignment_for_approval(assignment, *, requester_user, requester_employee=None):
    if assignment.status not in [CompensationAssignmentStatus.DRAFT, CompensationAssignmentStatus.REJECTED]:
        raise ValueError('Only draft or rejected compensation assignments can be submitted for approval.')
    organisation, requester_user, requester_employee = _resolve_payroll_requester_context(
        requester_user=requester_user,
        requester_employee=requester_employee,
        organisation=assignment.employee.organisation,
    )
    approval_run = _create_payroll_approval_run(
        assignment,
        ApprovalRequestKind.SALARY_REVISION,
        organisation,
        requester_user,
        requester_employee=requester_employee,
        subject_label=f'{assignment.employee.user.full_name} salary revision',
    )
    assignment.approval_run = approval_run
    assignment.status = CompensationAssignmentStatus.PENDING_APPROVAL
    assignment.save(update_fields=['approval_run', 'status', 'modified_at'])
    return assignment


def get_effective_compensation_assignment(employee, as_of_date):
    return employee.compensation_assignments.filter(
        effective_from__lte=as_of_date,
        status=CompensationAssignmentStatus.APPROVED,
    ).order_by('-effective_from', '-version', '-created_at').first()


def create_payroll_run(organisation, *, period_year, period_month, actor=None, requester_user=None, requester_employee=None, source_run=None, run_type=PayrollRunType.REGULAR, name=''):
    ensure_org_payroll_setup(organisation, actor=actor or requester_user)
    if not name:
        month_label = date(period_year, period_month, 1).strftime('%b %Y')
        name = f'{month_label} Payroll'
        if run_type == PayrollRunType.RERUN:
            name = f'{month_label} Payroll Rerun'
    pay_run = PayrollRun.objects.create(
        organisation=organisation,
        name=name,
        period_year=period_year,
        period_month=period_month,
        run_type=run_type,
        source_run=source_run,
    )
    log_audit_event(actor or requester_user, 'payroll.run.created', organisation=organisation, target=pay_run)
    return pay_run


def _employee_payroll_snapshot(employee):
    return {
        'has_primary_bank': employee.bank_accounts.filter(is_primary=True).exists(),
        'has_pan': employee.government_ids.filter(id_type=GovernmentIdType.PAN).exists(),
        'has_aadhaar': employee.government_ids.filter(id_type=GovernmentIdType.AADHAAR).exists(),
    }


def calculate_pay_run(pay_run, *, actor=None):
    if pay_run.status == PayrollRunStatus.FINALIZED:
        raise ValueError('Finalized payroll runs cannot be recalculated.')
    if pay_run.approval_run_id and pay_run.approval_run.status == ApprovalRunStatus.PENDING:
        cancel_approval_run(pay_run.approval_run, actor=actor)
        pay_run.approval_run = None

    period_end = date(pay_run.period_year, pay_run.period_month, monthrange(pay_run.period_year, pay_run.period_month)[1])
    fiscal_year = _fiscal_year_for_period(pay_run.period_year, pay_run.period_month)
    tax_slab_set = _get_active_tax_slab_set(pay_run.organisation, fiscal_year)
    if tax_slab_set is None:
        raise ValueError('No active tax slab set is configured for this payroll period.')

    with transaction.atomic():
        pay_run.items.all().delete()
        employees = Employee.objects.filter(organisation=pay_run.organisation, status=EmployeeStatus.ACTIVE).select_related('user')
        for employee in employees:
            assignment = get_effective_compensation_assignment(employee, period_end)
            if assignment is None:
                PayrollRunItem.objects.create(
                    pay_run=pay_run,
                    employee=employee,
                    status=PayrollRunItemStatus.EXCEPTION,
                    message='No approved compensation assignment is effective for this period.',
                    snapshot={'readiness': _employee_payroll_snapshot(employee)},
                )
                continue

            gross_pay = ZERO
            employee_deductions = ZERO
            employer_contributions = ZERO
            taxable_monthly = ZERO
            lines_snapshot = []
            for line in assignment.lines.all():
                amount = _normalize_decimal(line.monthly_amount)
                lines_snapshot.append(
                    {
                        'component_name': line.component_name,
                        'component_type': line.component_type,
                        'monthly_amount': str(amount),
                        'is_taxable': line.is_taxable,
                    }
                )
                if line.component_type in [PayrollComponentType.EARNING, PayrollComponentType.REIMBURSEMENT]:
                    gross_pay += amount
                    if line.is_taxable:
                        taxable_monthly += amount
                elif line.component_type == PayrollComponentType.EMPLOYEE_DEDUCTION:
                    employee_deductions += amount
                elif line.component_type == PayrollComponentType.EMPLOYER_CONTRIBUTION:
                    employer_contributions += amount

            annual_tax = _calculate_annual_tax(tax_slab_set, taxable_monthly * Decimal('12.00'))
            income_tax = (annual_tax / Decimal('12.00')).quantize(Decimal('0.01'))
            total_deductions = (employee_deductions + income_tax).quantize(Decimal('0.01'))
            net_pay = (gross_pay - total_deductions).quantize(Decimal('0.01'))

            PayrollRunItem.objects.create(
                pay_run=pay_run,
                employee=employee,
                status=PayrollRunItemStatus.READY,
                gross_pay=gross_pay.quantize(Decimal('0.01')),
                employee_deductions=employee_deductions.quantize(Decimal('0.01')),
                employer_contributions=employer_contributions.quantize(Decimal('0.01')),
                income_tax=income_tax,
                total_deductions=total_deductions,
                net_pay=net_pay,
                snapshot={
                    'assignment_id': str(assignment.id),
                    'readiness': _employee_payroll_snapshot(employee),
                    'lines': lines_snapshot,
                },
            )

        pay_run.status = PayrollRunStatus.CALCULATED
        pay_run.calculated_at = timezone.now()
        pay_run.submitted_at = None
        pay_run.save(update_fields=['status', 'calculated_at', 'submitted_at', 'approval_run', 'modified_at'])

    log_audit_event(actor, 'payroll.run.calculated', organisation=pay_run.organisation, target=pay_run)
    return pay_run


def submit_pay_run_for_approval(pay_run, *, requester_user, requester_employee=None):
    if pay_run.status != PayrollRunStatus.CALCULATED:
        raise ValueError('Only calculated payroll runs can be submitted for approval.')
    organisation, requester_user, requester_employee = _resolve_payroll_requester_context(
        requester_user=requester_user,
        requester_employee=requester_employee,
        organisation=pay_run.organisation,
    )
    approval_run = _create_payroll_approval_run(
        pay_run,
        ApprovalRequestKind.PAYROLL_PROCESSING,
        organisation,
        requester_user,
        requester_employee=requester_employee,
        subject_label=pay_run.name,
    )
    pay_run.approval_run = approval_run
    pay_run.status = PayrollRunStatus.APPROVAL_PENDING
    pay_run.submitted_at = timezone.now()
    pay_run.save(update_fields=['approval_run', 'status', 'submitted_at', 'modified_at'])
    return pay_run


def finalize_pay_run(pay_run, *, actor=None, skip_approval=False):
    if pay_run.status not in [PayrollRunStatus.APPROVED, PayrollRunStatus.CALCULATED]:
        raise ValueError('Only approved or explicitly bypassed calculated payroll runs can be finalized.')
    if pay_run.status == PayrollRunStatus.CALCULATED and not skip_approval:
        raise ValueError('Approval is required before finalization.')

    with transaction.atomic():
        for item in pay_run.items.select_related('employee__user').filter(status=PayrollRunItemStatus.READY):
            snapshot = {
                'employee_id': str(item.employee_id),
                'employee_name': item.employee.user.full_name,
                'period_year': pay_run.period_year,
                'period_month': pay_run.period_month,
                'period_label': date(pay_run.period_year, pay_run.period_month, 1).strftime('%B %Y'),
                'gross_pay': str(item.gross_pay),
                'employee_deductions': str(item.employee_deductions),
                'employer_contributions': str(item.employer_contributions),
                'income_tax': str(item.income_tax),
                'total_deductions': str(item.total_deductions),
                'net_pay': str(item.net_pay),
                'lines': item.snapshot.get('lines', []),
            }
            Payslip.objects.update_or_create(
                pay_run_item=item,
                defaults={
                    'organisation': pay_run.organisation,
                    'employee': item.employee,
                    'pay_run': pay_run,
                    'slip_number': f'{pay_run.period_year}{pay_run.period_month:02d}-{item.employee.employee_code or item.employee_id}',
                    'period_year': pay_run.period_year,
                    'period_month': pay_run.period_month,
                    'snapshot': snapshot,
                    'rendered_text': _build_rendered_payslip(snapshot),
                },
            )

        pay_run.status = PayrollRunStatus.FINALIZED
        pay_run.finalized_at = timezone.now()
        pay_run.save(update_fields=['status', 'finalized_at', 'modified_at'])

    log_audit_event(actor, 'payroll.run.finalized', organisation=pay_run.organisation, target=pay_run)
    return pay_run


def rerun_payroll_run(pay_run, *, actor=None, requester_user=None, requester_employee=None):
    if pay_run.status != PayrollRunStatus.FINALIZED:
        raise ValueError('Only finalized payroll runs can be rerun.')
    new_run = create_payroll_run(
        pay_run.organisation,
        period_year=pay_run.period_year,
        period_month=pay_run.period_month,
        actor=actor,
        requester_user=requester_user,
        requester_employee=requester_employee,
        source_run=pay_run,
        run_type=PayrollRunType.RERUN,
    )
    log_audit_event(actor or requester_user, 'payroll.run.rerun_created', organisation=pay_run.organisation, target=new_run)
    return new_run

