from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.notifications.models import NotificationKind
from apps.notifications.services import create_notification
from apps.organisations.services import get_org_operations_guard

from .models import (
    ApprovalAction,
    ApprovalActionAssignmentSource,
    ApprovalActionStatus,
    ApprovalApproverType,
    ApprovalDelegation,
    ApprovalFallbackType,
    ApprovalRequestKind,
    ApprovalRun,
    ApprovalRunStatus,
    ApprovalStageMode,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)

DEFAULT_APPROVAL_REQUEST_KINDS = [
    ApprovalRequestKind.LEAVE,
    ApprovalRequestKind.ON_DUTY,
    ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
]


def ensure_default_workflow_configured(organisation):
    missing_request_kinds = [
        request_kind
        for request_kind in DEFAULT_APPROVAL_REQUEST_KINDS
        if not ApprovalWorkflow.objects.filter(
            organisation=organisation,
            is_default=True,
            default_request_kind=request_kind,
            is_active=True,
        ).exists()
    ]
    if missing_request_kinds:
        raise ValueError('Create and activate a default approval workflow for each request type before inviting employees.')


def _matches_rule(rule, employee, request_kind, leave_type=None):
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
    if rule.designation and (employee.designation or '').strip().lower() != rule.designation.strip().lower():
        return False
    if rule.leave_type_id and (leave_type is None or leave_type.id != rule.leave_type_id):
        return False
    return True


def get_default_workflow(organisation, request_kind):
    return ApprovalWorkflow.objects.filter(
        organisation=organisation,
        is_default=True,
        default_request_kind=request_kind,
        is_active=True,
    ).first()


def get_employee_assigned_workflow(employee, request_kind):
    workflow = None
    if request_kind == ApprovalRequestKind.LEAVE:
        workflow = employee.leave_approval_workflow
    elif request_kind == ApprovalRequestKind.ON_DUTY:
        workflow = employee.on_duty_approval_workflow
    elif request_kind == ApprovalRequestKind.ATTENDANCE_REGULARIZATION:
        workflow = employee.attendance_regularization_approval_workflow

    if workflow and workflow.organisation_id == employee.organisation_id and workflow.is_active:
        return workflow
    return None


def _requester_user_for_context(requester):
    return requester.user if requester is not None else None


def resolve_workflow_with_source(employee, request_kind, leave_type=None):
    assigned_workflow = get_employee_assigned_workflow(employee, request_kind)
    if assigned_workflow is not None:
        return assigned_workflow, 'ASSIGNMENT'

    organisation = employee.organisation
    rules = (
        ApprovalWorkflowRule.objects.select_related('workflow', 'department', 'office_location', 'specific_employee', 'leave_type')
        .filter(
            workflow__organisation=organisation,
            workflow__is_active=True,
            is_active=True,
            request_kind=request_kind,
        )
        .order_by('priority', 'created_at')
    )
    for rule in rules:
        if _matches_rule(rule, employee, request_kind, leave_type=leave_type):
            return rule.workflow, 'RULE'

    default_workflow = get_default_workflow(organisation, request_kind)
    if default_workflow is None:
        raise ValueError(f'No active default approval workflow is configured for {request_kind.lower().replace("_", " ")} requests.')
    return default_workflow, 'DEFAULT'


def resolve_workflow(employee, request_kind, leave_type=None):
    workflow, _ = resolve_workflow_with_source(employee, request_kind, leave_type=leave_type)
    return workflow


def get_active_approval_delegation(approver_employee, request_kind, on_date=None):
    effective_date = on_date or timezone.localdate()
    candidates = ApprovalDelegation.objects.select_related(
        'delegate_employee__user',
        'delegator_employee__user',
    ).filter(
        organisation=approver_employee.organisation,
        delegator_employee=approver_employee,
        is_active=True,
        start_date__lte=effective_date,
    )
    candidates = candidates.filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=effective_date))
    for delegation in candidates.order_by('-start_date', '-created_at'):
        if request_kind in delegation.request_kinds:
            return delegation
    return None


def _validate_delegation_loop(organisation, delegator_employee, delegate_employee, *, exclude_id=None):
    if delegator_employee.id == delegate_employee.id:
        raise ValueError('An employee cannot delegate approval authority to themselves.')

    edges = {}
    queryset = ApprovalDelegation.objects.filter(organisation=organisation, is_active=True)
    if exclude_id is not None:
        queryset = queryset.exclude(id=exclude_id)
    for delegation in queryset.values('delegator_employee_id', 'delegate_employee_id'):
        edges.setdefault(delegation['delegator_employee_id'], set()).add(delegation['delegate_employee_id'])
    edges.setdefault(delegator_employee.id, set()).add(delegate_employee.id)

    stack = [delegate_employee.id]
    seen = set()
    while stack:
        current = stack.pop()
        if current == delegator_employee.id:
            raise ValueError('This delegation would create a delegation loop.')
        if current in seen:
            continue
        seen.add(current)
        stack.extend(edges.get(current, set()))


def upsert_approval_delegation(
    organisation,
    *,
    delegator_employee,
    delegate_employee,
    request_kinds,
    start_date,
    end_date=None,
    is_active=True,
    actor=None,
    delegation=None,
):
    if delegator_employee.organisation_id != organisation.id or delegate_employee.organisation_id != organisation.id:
        raise ValueError('Delegation employees must belong to the active organisation.')
    _validate_delegation_loop(
        organisation,
        delegator_employee,
        delegate_employee,
        exclude_id=delegation.id if delegation else None,
    )
    if end_date is not None and end_date < start_date:
        raise ValueError('Delegation end date must be on or after the start date.')

    payload = {
        'delegator_employee': delegator_employee,
        'delegate_employee': delegate_employee,
        'request_kinds': request_kinds,
        'start_date': start_date,
        'end_date': end_date,
        'is_active': is_active,
    }
    if delegation is None:
        delegation = ApprovalDelegation.objects.create(
            organisation=organisation,
            created_by=actor,
            **payload,
        )
        event_name = 'approval.delegation.created'
    else:
        for attr, value in payload.items():
            setattr(delegation, attr, value)
        delegation.save()
        event_name = 'approval.delegation.updated'

    log_audit_event(actor, event_name, organisation=organisation, target=delegation)
    return delegation


def _resolve_stage_fallback(stage, organisation):
    if stage.fallback_type == ApprovalFallbackType.NONE:
        return None
    if stage.fallback_type == ApprovalFallbackType.SPECIFIC_EMPLOYEE and stage.fallback_employee:
        return stage.fallback_employee.user, stage.fallback_employee
    if stage.fallback_type == ApprovalFallbackType.PRIMARY_ORG_ADMIN and organisation.primary_admin_user:
        return organisation.primary_admin_user, None
    return None


def _resolve_assignment_with_delegation(approver_user, approver_employee, organisation, request_kind):
    assignment = {
        'approver_user': approver_user,
        'approver_employee': approver_employee,
        'assignment_source': ApprovalActionAssignmentSource.DIRECT,
        'original_approver_user': None,
        'original_approver_employee': None,
    }
    if approver_employee is None:
        return assignment

    delegation = get_active_approval_delegation(approver_employee, request_kind)
    if delegation is None:
        return assignment

    assignment.update(
        {
            'approver_user': delegation.delegate_employee.user,
            'approver_employee': delegation.delegate_employee,
            'assignment_source': ApprovalActionAssignmentSource.DELEGATED,
            'original_approver_user': approver_user,
            'original_approver_employee': approver_employee,
        }
    )
    return assignment


def _resolve_stage_approvers(stage, requester, organisation, request_kind):
    resolved = []
    requester_user = _requester_user_for_context(requester)
    for stage_approver in stage.approvers.select_related('approver_employee__user').all():
        approver_user = None
        approver_employee = None

        if stage_approver.approver_type == ApprovalApproverType.REPORTING_MANAGER:
            manager = requester.reporting_to if requester is not None else None
            if manager and manager.id != requester.id:
                approver_user = manager.user
                approver_employee = manager
            else:
                fallback = _resolve_stage_fallback(stage, organisation)
                if fallback:
                    approver_user, approver_employee = fallback
        elif stage_approver.approver_type == ApprovalApproverType.SPECIFIC_EMPLOYEE and stage_approver.approver_employee:
            approver_user = stage_approver.approver_employee.user
            approver_employee = stage_approver.approver_employee
        elif stage_approver.approver_type == ApprovalApproverType.PRIMARY_ORG_ADMIN:
            approver_user = organisation.primary_admin_user

        if approver_user is None:
            continue
        if requester_user is not None and approver_user.id == requester_user.id and request_kind not in {
            ApprovalRequestKind.PAYROLL_PROCESSING,
            ApprovalRequestKind.SALARY_REVISION,
            ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
        }:
            fallback = _resolve_stage_fallback(stage, organisation)
            if fallback:
                approver_user, approver_employee = fallback
            else:
                continue
        resolved.append(_resolve_assignment_with_delegation(approver_user, approver_employee, organisation, request_kind))

    deduped = []
    seen = set()
    for assignment in resolved:
        user = assignment['approver_user']
        if user.id in seen:
            continue
        seen.add(user.id)
        deduped.append(assignment)
    if not deduped:
        raise ValueError(f'No approvers could be resolved for stage "{stage.name}".')
    return deduped


def _apply_subject_status(approval_run, new_status, rejection_reason=''):
    subject = approval_run.content_object
    if subject is None:
        return
    if hasattr(subject, 'status'):
        subject.status = new_status
    if rejection_reason and hasattr(subject, 'rejection_reason'):
        subject.rejection_reason = rejection_reason
    update_fields = ['status', 'modified_at'] if hasattr(subject, 'modified_at') else ['status']
    if rejection_reason and hasattr(subject, 'rejection_reason'):
        update_fields.append('rejection_reason')
    subject.save(update_fields=update_fields)
    if hasattr(subject, 'handle_approval_status_change'):
        subject.handle_approval_status_change(new_status, rejection_reason=rejection_reason)


def _create_stage_actions(approval_run, stage):
    actions = []
    requester = approval_run.requested_by
    for assignment in _resolve_stage_approvers(
        stage,
        requester,
        approval_run.organisation,
        approval_run.request_kind,
    ):
        actions.append(
            ApprovalAction.objects.create(
                approval_run=approval_run,
                stage=stage,
                approver_user=assignment['approver_user'],
                approver_employee=assignment['approver_employee'],
                assignment_source=assignment['assignment_source'],
                original_approver_user=assignment['original_approver_user'],
                original_approver_employee=assignment['original_approver_employee'],
            )
        )
    return actions


def create_approval_run(subject, request_kind, requester, actor=None, leave_type=None, subject_label=''):
    workflow = resolve_workflow(requester, request_kind, leave_type=leave_type)
    first_stage = workflow.stages.prefetch_related('approvers__approver_employee__user').order_by('sequence').first()
    if first_stage is None:
        raise ValueError('The selected approval workflow does not contain any stages.')

    with transaction.atomic():
        approval_run = ApprovalRun.objects.create(
            organisation=requester.organisation,
            workflow=workflow,
            request_kind=request_kind,
            requested_by=requester,
            requested_by_user=requester.user,
            status=ApprovalRunStatus.PENDING,
            current_stage_sequence=first_stage.sequence,
            subject_label=subject_label or str(subject),
            content_type=ContentType.objects.get_for_model(subject.__class__),
            object_id=subject.id,
        )
        _create_stage_actions(approval_run, first_stage)

    log_audit_event(
        actor or requester.user,
        'approval.run.created',
        organisation=requester.organisation,
        target=approval_run,
        payload={'request_kind': request_kind, 'workflow_id': str(workflow.id)},
    )
    return approval_run


def get_pending_approval_actions_for_user(user, organisation=None):
    queryset = ApprovalAction.objects.select_related(
        'approval_run',
        'stage',
        'stage__sla_policy',
        'approval_run__requested_by__user',
        'approval_run__requested_by_user',
        'approval_run__organisation',
        'approver_user',
        'original_approver_user',
    ).filter(
        approver_user=user,
        status=ApprovalActionStatus.PENDING,
        approval_run__status=ApprovalRunStatus.PENDING,
    )
    if organisation is not None:
        queryset = queryset.filter(approval_run__organisation=organisation)
    return queryset.order_by('created_at')


def _approval_outcome_kind(approval_run, new_status):
    approved = new_status == ApprovalRunStatus.APPROVED
    if approval_run.request_kind == ApprovalRequestKind.LEAVE:
        return NotificationKind.LEAVE_APPROVED if approved else NotificationKind.LEAVE_REJECTED
    if approval_run.request_kind == ApprovalRequestKind.ATTENDANCE_REGULARIZATION:
        return (
            NotificationKind.ATTENDANCE_REGULARIZATION_APPROVED
            if approved
            else NotificationKind.ATTENDANCE_REGULARIZATION_REJECTED
        )
    if approval_run.request_kind in {
        ApprovalRequestKind.SALARY_REVISION,
        ApprovalRequestKind.COMPENSATION_TEMPLATE_CHANGE,
    }:
        return NotificationKind.COMPENSATION_APPROVED if approved else NotificationKind.COMPENSATION_REJECTED
    return NotificationKind.GENERAL


def _notify_approval_outcome(approval_run, *, new_status, actor, comment=''):
    requester_user = approval_run.requested_by_user
    if requester_user is None:
        return

    request_label = approval_run.get_request_kind_display().lower()
    title = f'Your {request_label} request has been {"approved" if new_status == ApprovalRunStatus.APPROVED else "rejected"}'
    body = f'Your {request_label} request has been {"approved" if new_status == ApprovalRunStatus.APPROVED else "rejected"}.'
    if comment:
        body = f'{body} Reason: {comment}'

    create_notification(
        recipient=requester_user,
        kind=_approval_outcome_kind(approval_run, new_status),
        title=title,
        body=body,
        organisation=approval_run.organisation,
        related_object=approval_run.content_object or approval_run,
        actor=actor,
    )

    from apps.notifications.tasks import send_approval_outcome_email

    transaction.on_commit(
        lambda: send_approval_outcome_email.delay(
            str(requester_user.id),
            subject=title,
            title=title,
            body=body,
        )
    )


def _advance_or_complete_run(approval_run, actor):
    next_stage = approval_run.workflow.stages.prefetch_related('approvers__approver_employee__user').filter(
        sequence__gt=approval_run.current_stage_sequence
    ).order_by('sequence').first()
    if next_stage is None:
        approval_run.status = ApprovalRunStatus.APPROVED
        approval_run.save(update_fields=['status', 'modified_at'])
        _apply_subject_status(approval_run, 'APPROVED')
        _notify_approval_outcome(approval_run, new_status=ApprovalRunStatus.APPROVED, actor=actor)
        log_audit_event(actor, 'approval.run.approved', organisation=approval_run.organisation, target=approval_run)
        return approval_run

    approval_run.current_stage_sequence = next_stage.sequence
    approval_run.save(update_fields=['current_stage_sequence', 'modified_at'])
    _create_stage_actions(approval_run, next_stage)
    log_audit_event(
        actor,
        'approval.run.advanced',
        organisation=approval_run.organisation,
        target=approval_run,
        payload={'current_stage_sequence': next_stage.sequence},
    )
    return approval_run


def approve_action(action, actor, comment=''):
    if action.approver_user_id != actor.id:
        raise ValueError('You are not allowed to act on this approval.')
    if action.status != ApprovalActionStatus.PENDING:
        raise ValueError('This approval action is no longer pending.')

    guard = get_org_operations_guard(action.approval_run.organisation)
    if guard['approval_actions_blocked']:
        raise ValueError(guard['reason'])

    with transaction.atomic():
        action.status = ApprovalActionStatus.APPROVED
        action.comment = comment
        action.acted_at = timezone.now()
        action.save(update_fields=['status', 'comment', 'acted_at', 'modified_at'])

        sibling_actions = action.approval_run.actions.filter(stage=action.stage)
        if action.stage.mode == ApprovalStageMode.ANY:
            sibling_actions.exclude(id=action.id).filter(status=ApprovalActionStatus.PENDING).update(
                status=ApprovalActionStatus.SKIPPED,
                acted_at=timezone.now(),
                modified_at=timezone.now(),
            )
            stage_complete = True
        else:
            stage_complete = not sibling_actions.filter(status=ApprovalActionStatus.PENDING).exists()

        if stage_complete:
            _advance_or_complete_run(action.approval_run, actor)

    log_audit_event(actor, 'approval.action.approved', organisation=action.approval_run.organisation, target=action)
    return action


def reject_action(action, actor, comment=''):
    if action.approver_user_id != actor.id:
        raise ValueError('You are not allowed to act on this approval.')
    if action.status != ApprovalActionStatus.PENDING:
        raise ValueError('This approval action is no longer pending.')

    guard = get_org_operations_guard(action.approval_run.organisation)
    if guard['approval_actions_blocked']:
        raise ValueError(guard['reason'])

    with transaction.atomic():
        action.status = ApprovalActionStatus.REJECTED
        action.comment = comment
        action.acted_at = timezone.now()
        action.save(update_fields=['status', 'comment', 'acted_at', 'modified_at'])

        action.approval_run.status = ApprovalRunStatus.REJECTED
        action.approval_run.save(update_fields=['status', 'modified_at'])
        action.approval_run.actions.exclude(id=action.id).filter(status=ApprovalActionStatus.PENDING).update(
            status=ApprovalActionStatus.CANCELLED,
            acted_at=timezone.now(),
            modified_at=timezone.now(),
        )
        _apply_subject_status(action.approval_run, 'REJECTED', rejection_reason=comment)
        _notify_approval_outcome(action.approval_run, new_status=ApprovalRunStatus.REJECTED, actor=actor, comment=comment)

    log_audit_event(
        actor,
        'approval.action.rejected',
        organisation=action.approval_run.organisation,
        target=action,
        payload={'comment': comment},
    )
    return action


def _get_stage_sla_policy(stage):
    policy = getattr(stage, 'sla_policy', None)
    if policy is None or not policy.is_active:
        return None
    return policy


def _resolve_escalation_target(action):
    policy = _get_stage_sla_policy(action.stage)
    if policy is None:
        return None, None
    if policy.escalation_target_type == ApprovalFallbackType.SPECIFIC_EMPLOYEE and policy.escalation_employee:
        return policy.escalation_employee.user, policy.escalation_employee
    if (
        policy.escalation_target_type == ApprovalFallbackType.PRIMARY_ORG_ADMIN
        and action.approval_run.organisation.primary_admin_user
    ):
        return action.approval_run.organisation.primary_admin_user, None
    return None, None


def send_pending_action_reminders(now=None):
    current_time = now or timezone.now()
    reminder_count = 0
    queryset = ApprovalAction.objects.select_related(
        'approval_run',
        'approver_user',
        'stage__sla_policy',
    ).filter(
        status=ApprovalActionStatus.PENDING,
        approval_run__status=ApprovalRunStatus.PENDING,
    )
    for action in queryset.iterator():
        policy = _get_stage_sla_policy(action.stage)
        if policy is None or not policy.reminder_after_hours or action.reminder_sent_at is not None:
            continue
        if action.created_at + timedelta(hours=policy.reminder_after_hours) > current_time:
            continue
        updated = ApprovalAction.objects.filter(
            id=action.id,
            reminder_sent_at__isnull=True,
            status=ApprovalActionStatus.PENDING,
        ).update(
            reminder_sent_at=current_time,
            modified_at=current_time,
        )
        if not updated:
            continue
        create_notification(
            recipient=action.approver_user,
            kind=NotificationKind.GENERAL,
            title=f'Approval reminder: {action.approval_run.subject_label}',
            body=f'This approval has been pending since {action.created_at.isoformat()}. Please review it.',
            organisation=action.approval_run.organisation,
            related_object=action.approval_run,
        )
        log_audit_event(
            None,
            'approval.action.reminder_sent',
            organisation=action.approval_run.organisation,
            target=action,
        )
        reminder_count += 1
    return reminder_count


def process_pending_action_escalations(now=None):
    current_time = now or timezone.now()
    escalation_count = 0
    queryset = ApprovalAction.objects.select_related(
        'approval_run',
        'approver_user',
        'approver_employee__user',
        'original_approver_user',
        'original_approver_employee__user',
        'stage',
        'stage__sla_policy',
        'stage__sla_policy__escalation_employee__user',
        'approval_run__organisation',
    ).filter(
        status=ApprovalActionStatus.PENDING,
        approval_run__status=ApprovalRunStatus.PENDING,
    )
    for action in queryset.iterator():
        policy = _get_stage_sla_policy(action.stage)
        if policy is None or not policy.escalate_after_hours or action.escalated_at is not None:
            continue
        if action.created_at + timedelta(hours=policy.escalate_after_hours) > current_time:
            continue
        target_user, target_employee = _resolve_escalation_target(action)
        if target_user is None or target_user.id == action.approver_user_id:
            continue

        with transaction.atomic():
            locked_action = ApprovalAction.objects.select_for_update(of=('self',)).select_related(
                'approval_run',
                'stage',
                'approval_run__organisation',
                'approver_user',
                'approver_employee',
                'original_approver_user',
                'original_approver_employee',
            ).get(id=action.id)
            if locked_action.status != ApprovalActionStatus.PENDING or locked_action.escalated_at is not None:
                continue

            existing_pending = locked_action.approval_run.actions.filter(
                stage=locked_action.stage,
                approver_user=target_user,
                status=ApprovalActionStatus.PENDING,
            ).exists()
            if not existing_pending:
                ApprovalAction.objects.create(
                    approval_run=locked_action.approval_run,
                    stage=locked_action.stage,
                    approver_user=target_user,
                    approver_employee=target_employee,
                    assignment_source=ApprovalActionAssignmentSource.ESCALATED,
                    original_approver_user=locked_action.original_approver_user or locked_action.approver_user,
                    original_approver_employee=locked_action.original_approver_employee or locked_action.approver_employee,
                    escalated_from_action=locked_action,
                )

            locked_action.status = ApprovalActionStatus.CANCELLED
            locked_action.acted_at = current_time
            locked_action.escalated_at = current_time
            locked_action.save(update_fields=['status', 'acted_at', 'escalated_at', 'modified_at'])

        create_notification(
            recipient=target_user,
            kind=NotificationKind.GENERAL,
            title=f'Escalated approval: {action.approval_run.subject_label}',
            body='A pending approval has been escalated to you because its SLA was missed.',
            organisation=action.approval_run.organisation,
            related_object=action.approval_run,
        )
        log_audit_event(
            None,
            'approval.action.escalated',
            organisation=action.approval_run.organisation,
            target=action.approval_run,
            payload={'action_id': str(action.id), 'target_user_id': str(target_user.id)},
        )
        escalation_count += 1
    return escalation_count


def cancel_approval_run(approval_run, actor=None, *, subject_status='CANCELLED'):
    if approval_run.status != ApprovalRunStatus.PENDING:
        return approval_run
    with transaction.atomic():
        approval_run.status = ApprovalRunStatus.CANCELLED
        approval_run.save(update_fields=['status', 'modified_at'])
        approval_run.actions.filter(status=ApprovalActionStatus.PENDING).update(
            status=ApprovalActionStatus.CANCELLED,
            acted_at=timezone.now(),
            modified_at=timezone.now(),
        )
        if subject_status is not None:
            _apply_subject_status(approval_run, subject_status)
    log_audit_event(actor, 'approval.run.cancelled', organisation=approval_run.organisation, target=approval_run)
    return approval_run
