from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    ApprovalActionsAllowed,
    BelongsToActiveOrg,
    IsEmployee,
    IsOrgAdmin,
    OrgAdminMutationAllowed,
)
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.departments.models import Department
from apps.employees.models import Employee
from apps.locations.models import OfficeLocation
from apps.timeoff.models import LeaveType

from .models import (
    ApprovalAction,
    ApprovalApproverType,
    ApprovalFallbackType,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from .serializers import (
    ApprovalActionDecisionSerializer,
    ApprovalActionSerializer,
    ApprovalWorkflowSerializer,
    ApprovalWorkflowWriteSerializer,
)
from .services import approve_action, get_pending_approval_actions_for_user, reject_action


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _get_employee(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        raise ValueError('Select an employee workspace to continue.')
    return employee


def _get_department(organisation, department_id):
    if not department_id:
        return None
    return Department.objects.get(organisation=organisation, id=department_id)


def _get_location(organisation, office_location_id):
    if not office_location_id:
        return None
    return OfficeLocation.objects.get(organisation=organisation, id=office_location_id)


def _get_employee_record(organisation, employee_id):
    if not employee_id:
        return None
    return Employee.objects.get(organisation=organisation, id=employee_id)


def _get_leave_type(organisation, leave_type_id):
    if not leave_type_id:
        return None
    return LeaveType.objects.get(leave_plan__organisation=organisation, id=leave_type_id)


def _upsert_workflow(organisation, payload, actor, workflow=None):
    stages_payload = payload.pop('stages', [])
    rules_payload = payload.pop('rules', [])
    if not stages_payload:
        raise ValueError('At least one approval stage is required.')

    sequences = [item['sequence'] for item in stages_payload]
    if len(sequences) != len(set(sequences)):
        raise ValueError('Each approval stage must have a unique sequence.')

    with transaction.atomic():
        if workflow is None:
            workflow = ApprovalWorkflow.objects.create(
                organisation=organisation,
                created_by=actor,
                **payload,
            )
        else:
            for attr, value in payload.items():
                setattr(workflow, attr, value)
            workflow.save()

        if workflow.is_default:
            ApprovalWorkflow.objects.filter(organisation=organisation).exclude(id=workflow.id).update(is_default=False)

        keep_rule_ids = []
        for rule_payload in rules_payload:
            rule_id = rule_payload.pop('id', None)
            data = {
                'name': rule_payload['name'],
                'request_kind': rule_payload['request_kind'],
                'priority': rule_payload.get('priority', 100),
                'is_active': rule_payload.get('is_active', True),
                'department': _get_department(organisation, rule_payload.get('department_id')),
                'office_location': _get_location(organisation, rule_payload.get('office_location_id')),
                'specific_employee': _get_employee_record(organisation, rule_payload.get('specific_employee_id')),
                'employment_type': rule_payload.get('employment_type', ''),
                'designation': rule_payload.get('designation', ''),
                'leave_type': _get_leave_type(organisation, rule_payload.get('leave_type_id')),
            }
            if rule_id:
                rule = workflow.rules.get(id=rule_id)
                for attr, value in data.items():
                    setattr(rule, attr, value)
                rule.save()
            else:
                rule = ApprovalWorkflowRule.objects.create(workflow=workflow, **data)
            keep_rule_ids.append(rule.id)
        workflow.rules.exclude(id__in=keep_rule_ids).delete()

        keep_stage_ids = []
        for stage_payload in stages_payload:
            stage_id = stage_payload.pop('id', None)
            approvers_payload = stage_payload.pop('approvers', [])
            stage_data = {
                'name': stage_payload['name'],
                'sequence': stage_payload['sequence'],
                'mode': stage_payload.get('mode'),
                'fallback_type': stage_payload.get('fallback_type', ApprovalFallbackType.NONE),
                'fallback_employee': _get_employee_record(organisation, stage_payload.get('fallback_employee_id')),
            }
            if stage_data['fallback_type'] == ApprovalFallbackType.SPECIFIC_EMPLOYEE and stage_data['fallback_employee'] is None:
                raise ValueError('A fallback employee is required for specific-employee fallback.')

            if stage_id:
                stage = workflow.stages.get(id=stage_id)
                for attr, value in stage_data.items():
                    setattr(stage, attr, value)
                stage.save()
            else:
                stage = ApprovalStage.objects.create(workflow=workflow, **stage_data)
            keep_stage_ids.append(stage.id)

            keep_approver_ids = []
            for approver_payload in approvers_payload:
                approver_id = approver_payload.get('id')
                approver_type = approver_payload['approver_type']
                approver_employee = _get_employee_record(organisation, approver_payload.get('approver_employee_id'))
                if approver_type == ApprovalApproverType.SPECIFIC_EMPLOYEE and approver_employee is None:
                    raise ValueError('A specific employee approver must be selected.')
                approver_data = {
                    'approver_type': approver_type,
                    'approver_employee': approver_employee,
                }
                if approver_id:
                    approver = stage.approvers.get(id=approver_id)
                    for attr, value in approver_data.items():
                        setattr(approver, attr, value)
                    approver.save()
                else:
                    approver = ApprovalStageApprover.objects.create(stage=stage, **approver_data)
                keep_approver_ids.append(approver.id)
            if not keep_approver_ids:
                raise ValueError(f'Stage "{stage.name}" must contain at least one approver.')
            stage.approvers.exclude(id__in=keep_approver_ids).delete()

        workflow.stages.exclude(id__in=keep_stage_ids).delete()

    return workflow


class OrgApprovalWorkflowListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        workflows = ApprovalWorkflow.objects.filter(organisation=organisation).prefetch_related(
            'rules',
            'stages__approvers__approver_employee__user',
            'stages__fallback_employee__user',
        )
        return Response(ApprovalWorkflowSerializer(workflows, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ApprovalWorkflowWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            workflow = _upsert_workflow(organisation, serializer.validated_data, request.user)
        except (ValueError, Department.DoesNotExist, OfficeLocation.DoesNotExist, Employee.DoesNotExist, LeaveType.DoesNotExist) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalWorkflowSerializer(workflow).data, status=status.HTTP_201_CREATED)


class OrgApprovalWorkflowDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        workflow = get_object_or_404(ApprovalWorkflow, organisation=organisation, id=pk)
        serializer = ApprovalWorkflowWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            workflow = _upsert_workflow(organisation, serializer.validated_data, request.user, workflow=workflow)
        except (ValueError, Department.DoesNotExist, OfficeLocation.DoesNotExist, Employee.DoesNotExist, LeaveType.DoesNotExist) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalWorkflowSerializer(workflow).data)


class OrgApprovalInboxView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = get_pending_approval_actions_for_user(request.user, organisation=organisation)
        return Response(ApprovalActionSerializer(queryset, many=True).data)


class MyApprovalInboxView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        queryset = get_pending_approval_actions_for_user(request.user, organisation=employee.organisation)
        return Response(ApprovalActionSerializer(queryset, many=True).data)


class OrgApprovalActionApproveView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, ApprovalActionsAllowed]

    def post(self, request, action_id):
        organisation = _get_admin_organisation(request)
        action = get_object_or_404(ApprovalAction, id=action_id, approval_run__organisation=organisation)
        serializer = ApprovalActionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            action = approve_action(action, request.user, serializer.validated_data['comment'])
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalActionSerializer(action).data)


class OrgApprovalActionRejectView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, ApprovalActionsAllowed]

    def post(self, request, action_id):
        organisation = _get_admin_organisation(request)
        action = get_object_or_404(ApprovalAction, id=action_id, approval_run__organisation=organisation)
        serializer = ApprovalActionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            action = reject_action(action, request.user, serializer.validated_data['comment'])
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalActionSerializer(action).data)


class MyApprovalActionApproveView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg, ApprovalActionsAllowed]

    def post(self, request, action_id):
        employee = _get_employee(request)
        action = get_object_or_404(ApprovalAction, id=action_id, approval_run__organisation=employee.organisation)
        serializer = ApprovalActionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            action = approve_action(action, request.user, serializer.validated_data['comment'])
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalActionSerializer(action).data)


class MyApprovalActionRejectView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg, ApprovalActionsAllowed]

    def post(self, request, action_id):
        employee = _get_employee(request)
        action = get_object_or_404(ApprovalAction, id=action_id, approval_run__organisation=employee.organisation)
        serializer = ApprovalActionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            action = reject_action(action, request.user, serializer.validated_data['comment'])
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalActionSerializer(action).data)
