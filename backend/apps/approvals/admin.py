from django.contrib import admin

from .models import (
    ApprovalAction,
    ApprovalRun,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'default_request_kind', 'is_default', 'is_active', 'created_at')
    list_filter = ('default_request_kind', 'is_default', 'is_active', 'organisation')
    search_fields = ('name', 'organisation__name')


@admin.register(ApprovalWorkflowRule)
class ApprovalWorkflowRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'workflow', 'request_kind', 'priority', 'is_active')
    list_filter = ('request_kind', 'is_active')
    search_fields = ('name', 'workflow__name')


@admin.register(ApprovalStage)
class ApprovalStageAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'name', 'sequence', 'mode', 'fallback_type')
    list_filter = ('mode', 'fallback_type')
    search_fields = ('name', 'workflow__name')


@admin.register(ApprovalStageApprover)
class ApprovalStageApproverAdmin(admin.ModelAdmin):
    list_display = ('stage', 'approver_type', 'approver_employee')
    list_filter = ('approver_type',)


@admin.register(ApprovalRun)
class ApprovalRunAdmin(admin.ModelAdmin):
    list_display = ('request_kind', 'organisation', 'requested_by', 'status', 'current_stage_sequence', 'created_at')
    list_filter = ('request_kind', 'status', 'organisation')
    search_fields = ('subject_label', 'requested_by__user__email')


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ('approval_run', 'approver_user', 'status', 'acted_at')
    list_filter = ('status',)
    search_fields = ('approver_user__email', 'approval_run__subject_label')
