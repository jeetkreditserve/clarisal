from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.organisations.services import get_org_operations_guard

from .models import (
    ApprovalAction,
    ApprovalActionStatus,
    ApprovalApproverType,
    ApprovalFallbackType,
    ApprovalRequestKind,
    ApprovalRun,
    ApprovalRunStatus,
    ApprovalStage,
    ApprovalStageMode,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)


def ensure_default_workflow_configured(organisation):
    if not ApprovalWorkflow.objects.filter(organisation=organisation, is_default=True, is_active=True).exists():
        raise ValueError('Create and activate a default approval workflow before inviting employees.')


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


def resolve_workflow(employee, request_kind, leave_type=None):
    organisation = employee.organisation
    rules = (
        ApprovalWorkflowRule.objects.select_related('workflow', 'department', 'office_location', 'specific_employee', 'leave_type')
        .filter(workflow__organisation=organisation, workflow__is_active=True, is_active=True)
        .order_by('priority', 'created_at')
    )
    for rule in rules:
        if _matches_rule(rule, employee, request_kind, leave_type=leave_type):
            return rule.workflow

    default_workflow = ApprovalWorkflow.objects.filter(
        organisation=organisation,
        is_default=True,
        is_active=True,
    ).first()
    if default_workflow is None:
        raise ValueError('No active default approval workflow is configured for this organisation.')
    return default_workflow


def _resolve_stage_fallback(stage, requester):
    if stage.fallback_type == ApprovalFallbackType.NONE:
        return None
    if stage.fallback_type == ApprovalFallbackType.SPECIFIC_EMPLOYEE and stage.fallback_employee:
        return stage.fallback_employee.user, stage.fallback_employee
    if stage.fallback_type == ApprovalFallbackType.PRIMARY_ORG_ADMIN and requester.organisation.primary_admin_user:
        return requester.organisation.primary_admin_user, None
    return None


def _resolve_stage_approvers(stage, requester):
    resolved = []
    for stage_approver in stage.approvers.select_related('approver_employee__user').all():
        approver_user = None
        approver_employee = None

        if stage_approver.approver_type == ApprovalApproverType.REPORTING_MANAGER:
            manager = requester.reporting_to
            if manager and manager.id != requester.id:
                approver_user = manager.user
                approver_employee = manager
            else:
                fallback = _resolve_stage_fallback(stage, requester)
                if fallback:
                    approver_user, approver_employee = fallback
        elif stage_approver.approver_type == ApprovalApproverType.SPECIFIC_EMPLOYEE and stage_approver.approver_employee:
            approver_user = stage_approver.approver_employee.user
            approver_employee = stage_approver.approver_employee
        elif stage_approver.approver_type == ApprovalApproverType.PRIMARY_ORG_ADMIN:
            approver_user = requester.organisation.primary_admin_user

        if approver_user is None:
            continue
        if approver_user.id == requester.user_id:
            fallback = _resolve_stage_fallback(stage, requester)
            if fallback:
                approver_user, approver_employee = fallback
            else:
                continue
        resolved.append((approver_user, approver_employee))

    deduped = []
    seen = set()
    for user, employee in resolved:
        if user.id in seen:
            continue
        seen.add(user.id)
        deduped.append((user, employee))
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
    update_fields = ['status', 'updated_at'] if hasattr(subject, 'updated_at') else ['status']
    if rejection_reason and hasattr(subject, 'rejection_reason'):
        update_fields.append('rejection_reason')
    subject.save(update_fields=update_fields)


def _create_stage_actions(approval_run, stage):
    actions = []
    for approver_user, approver_employee in _resolve_stage_approvers(stage, approval_run.requested_by):
        actions.append(
            ApprovalAction.objects.create(
                approval_run=approval_run,
                stage=stage,
                approver_user=approver_user,
                approver_employee=approver_employee,
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
        'approval_run__requested_by__user',
        'approval_run__organisation',
    ).filter(
        approver_user=user,
        status=ApprovalActionStatus.PENDING,
        approval_run__status=ApprovalRunStatus.PENDING,
    )
    if organisation is not None:
        queryset = queryset.filter(approval_run__organisation=organisation)
    return queryset.order_by('created_at')


def _advance_or_complete_run(approval_run, actor):
    next_stage = approval_run.workflow.stages.prefetch_related('approvers__approver_employee__user').filter(
        sequence__gt=approval_run.current_stage_sequence
    ).order_by('sequence').first()
    if next_stage is None:
        approval_run.status = ApprovalRunStatus.APPROVED
        approval_run.save(update_fields=['status', 'updated_at'])
        _apply_subject_status(approval_run, 'APPROVED')
        log_audit_event(actor, 'approval.run.approved', organisation=approval_run.organisation, target=approval_run)
        return approval_run

    approval_run.current_stage_sequence = next_stage.sequence
    approval_run.save(update_fields=['current_stage_sequence', 'updated_at'])
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
        action.save(update_fields=['status', 'comment', 'acted_at', 'updated_at'])

        sibling_actions = action.approval_run.actions.filter(stage=action.stage)
        if action.stage.mode == ApprovalStageMode.ANY:
            sibling_actions.exclude(id=action.id).filter(status=ApprovalActionStatus.PENDING).update(
                status=ApprovalActionStatus.SKIPPED,
                acted_at=timezone.now(),
                updated_at=timezone.now(),
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
        action.save(update_fields=['status', 'comment', 'acted_at', 'updated_at'])

        action.approval_run.status = ApprovalRunStatus.REJECTED
        action.approval_run.save(update_fields=['status', 'updated_at'])
        action.approval_run.actions.exclude(id=action.id).filter(status=ApprovalActionStatus.PENDING).update(
            status=ApprovalActionStatus.CANCELLED,
            acted_at=timezone.now(),
            updated_at=timezone.now(),
        )
        _apply_subject_status(action.approval_run, 'REJECTED', rejection_reason=comment)

    log_audit_event(
        actor,
        'approval.action.rejected',
        organisation=action.approval_run.organisation,
        target=action,
        payload={'comment': comment},
    )
    return action


def cancel_approval_run(approval_run, actor=None):
    if approval_run.status != ApprovalRunStatus.PENDING:
        return approval_run
    with transaction.atomic():
        approval_run.status = ApprovalRunStatus.CANCELLED
        approval_run.save(update_fields=['status', 'updated_at'])
        approval_run.actions.filter(status=ApprovalActionStatus.PENDING).update(
            status=ApprovalActionStatus.CANCELLED,
            acted_at=timezone.now(),
            updated_at=timezone.now(),
        )
        _apply_subject_status(approval_run, 'CANCELLED')
    log_audit_event(actor, 'approval.run.cancelled', organisation=approval_run.organisation, target=approval_run)
    return approval_run
