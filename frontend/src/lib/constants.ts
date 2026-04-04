import type {
  ApprovalApproverType,
  ApprovalFallbackType,
  ApprovalRequestKind,
  ApprovalStageMode,
  DocumentType,
  EmployeeStatus,
  EmploymentType,
  FamilyRelation,
  NoticeAudienceType,
  NoticeCategory,
  NoticeStatus,
} from '@/types/hr'

export const EMPLOYEE_STATUS_OPTIONS: Array<EmployeeStatus | ''> = ['', 'INVITED', 'PENDING', 'ACTIVE', 'RESIGNED', 'RETIRED', 'TERMINATED']
export const EMPLOYMENT_TYPE_OPTIONS: EmploymentType[] = ['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN']
export const DAY_SESSION_OPTIONS = ['FULL_DAY', 'FIRST_HALF', 'SECOND_HALF'] as const
export const OD_DURATION_OPTIONS = ['FULL_DAY', 'FIRST_HALF', 'SECOND_HALF', 'TIME_RANGE'] as const
export const FAMILY_RELATION_OPTIONS: FamilyRelation[] = ['SPOUSE', 'FATHER', 'MOTHER', 'SON', 'DAUGHTER', 'BROTHER', 'SISTER', 'OTHER']
export const HOLIDAY_CLASSIFICATION_OPTIONS = ['PUBLIC', 'RESTRICTED', 'COMPANY'] as const
export const HOLIDAY_SESSION_OPTIONS = [...DAY_SESSION_OPTIONS]
export const LEAVE_CYCLE_TYPE_OPTIONS = ['CALENDAR_YEAR', 'FINANCIAL_YEAR', 'CUSTOM_FIXED_START', 'EMPLOYEE_JOINING_DATE'] as const
export const LEAVE_CREDIT_FREQUENCY_OPTIONS = ['MANUAL', 'MONTHLY', 'QUARTERLY', 'HALF_YEARLY', 'YEARLY'] as const
export const NOTICE_AUDIENCE_TYPE_OPTIONS: NoticeAudienceType[] = ['ALL_EMPLOYEES', 'DEPARTMENTS', 'OFFICE_LOCATIONS', 'SPECIFIC_EMPLOYEES']
export const NOTICE_STATUS_OPTIONS: NoticeStatus[] = ['DRAFT', 'SCHEDULED', 'PUBLISHED', 'EXPIRED', 'ARCHIVED']
export const NOTICE_CATEGORY_OPTIONS: NoticeCategory[] = ['GENERAL', 'HR_POLICY', 'OPERATIONS', 'CELEBRATION', 'COMPLIANCE', 'URGENT']
export const APPROVAL_REQUEST_KIND_OPTIONS: ApprovalRequestKind[] = [
  'LEAVE',
  'ON_DUTY',
  'ATTENDANCE_REGULARIZATION',
  'PAYROLL_PROCESSING',
  'SALARY_REVISION',
  'COMPENSATION_TEMPLATE_CHANGE',
]
export const APPROVAL_APPROVER_TYPE_OPTIONS: ApprovalApproverType[] = ['REPORTING_MANAGER', 'SPECIFIC_EMPLOYEE', 'PRIMARY_ORG_ADMIN']
export const APPROVAL_FALLBACK_TYPE_OPTIONS: ApprovalFallbackType[] = ['NONE', 'SPECIFIC_EMPLOYEE', 'PRIMARY_ORG_ADMIN']
export const APPROVAL_STAGE_MODE_OPTIONS: ApprovalStageMode[] = ['ALL', 'ANY']
export const DOCUMENT_TYPE_OPTIONS: DocumentType[] = ['PAN', 'AADHAAR', 'EDUCATION_CERT', 'EMPLOYMENT_LETTER', 'OTHER']

export function createDefaultApprovalWorkflow() {
  return {
    name: 'Default Leave Workflow',
    description: '',
    is_default: true,
    default_request_kind: 'LEAVE' as ApprovalRequestKind,
    is_active: true,
    rules: [
      {
        name: 'Default leave rule',
        request_kind: 'LEAVE',
        priority: 100,
        is_active: true,
        department_id: null as string | null,
        office_location_id: null as string | null,
        specific_employee_id: null as string | null,
        employment_type: '',
        designation: '',
        leave_type_id: null as string | null,
      },
    ],
    stages: [
      {
        name: 'Manager review',
        sequence: 1,
        mode: 'ALL',
        fallback_type: 'PRIMARY_ORG_ADMIN',
        fallback_employee_id: null as string | null,
        reminder_after_hours: null as number | null,
        escalate_after_hours: null as number | null,
        escalation_target_type: 'NONE' as ApprovalFallbackType,
        escalation_employee_id: null as string | null,
        approvers: [{ approver_type: 'REPORTING_MANAGER', approver_employee_id: null as string | null }],
      },
    ],
  }
}

export function createDefaultHolidayCalendarForm() {
  return {
    name: '',
    year: new Date().getFullYear(),
    description: '',
    is_default: true,
    holidays: [{ name: '', holiday_date: '', classification: 'PUBLIC', session: 'FULL_DAY', description: '' }],
    location_ids: [] as string[],
  }
}

export function createDefaultLeaveCycleForm() {
  return {
    name: 'Default Leave Year',
    cycle_type: 'CALENDAR_YEAR',
    start_month: 1,
    start_day: 1,
    is_default: true,
    is_active: true,
  }
}

export function createDefaultLeavePlanForm() {
  return {
    leave_cycle_id: '',
    name: 'General Leave Plan',
    description: '',
    is_default: true,
    is_active: true,
    priority: 100,
    leave_types: [
      {
        code: 'CL',
        name: 'Casual Leave',
        description: '',
        color: '#2563eb',
        is_paid: true,
        is_loss_of_pay: false,
        annual_entitlement: '12.00',
        credit_frequency: 'MONTHLY',
        credit_day_of_period: null,
        prorate_on_join: true,
        carry_forward_mode: 'CAPPED',
        carry_forward_cap: '6.00' as string | null,
        max_balance: '18.00' as string | null,
        allows_half_day: true,
        requires_attachment: false,
        attachment_after_days: null as string | null,
        min_notice_days: 0,
        max_consecutive_days: null as number | null,
        allow_past_request: false,
        allow_future_request: true,
        is_active: true,
      },
    ],
    rules: [],
  }
}

export function createDefaultOnDutyPolicyForm() {
  return {
    name: 'Default On Duty Policy',
    description: '',
    is_default: true,
    is_active: true,
    allow_half_day: true,
    allow_time_range: true,
    requires_attachment: false,
    min_notice_days: 0,
    allow_past_request: false,
    allow_future_request: true,
  }
}

export function createDefaultNoticeForm() {
  return {
    title: '',
    body: '',
    category: 'GENERAL',
    audience_type: 'ALL_EMPLOYEES',
    status: 'DRAFT',
    is_sticky: false,
    scheduled_for: null as string | null,
    expires_at: null as string | null,
    department_ids: [] as string[],
    office_location_ids: [] as string[],
    employee_ids: [] as string[],
  }
}
