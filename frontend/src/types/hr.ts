export type EmploymentType = 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERN'
export type EmployeeStatus = 'INVITED' | 'PENDING' | 'ACTIVE' | 'RESIGNED' | 'RETIRED' | 'TERMINATED'
export type EmployeeOnboardingStatus = 'NOT_STARTED' | 'BASIC_DETAILS_PENDING' | 'DOCUMENTS_PENDING' | 'COMPLETE'
export type GovernmentIdType = 'PAN' | 'AADHAAR'
export type GovernmentIdStatus = 'PENDING' | 'VERIFIED' | 'REJECTED'
export type BankAccountType = 'SAVINGS' | 'CURRENT' | 'SALARY'
export type DocumentStatus = 'PENDING' | 'VERIFIED' | 'REJECTED'
export type DocumentType = string
export type OnboardingDocumentCategory =
  | 'IDENTITY_TAX'
  | 'ADDRESS'
  | 'BANKING_PAYROLL'
  | 'EDUCATION'
  | 'PREVIOUS_EMPLOYMENT'
  | 'STATUTORY_BENEFITS'
  | 'FAMILY_NOMINEE'
  | 'MEDICAL_SAFETY'
  | 'POLICY_ACK'
  | 'ROLE_COMPLIANCE'
  | 'CUSTOM'
export type EmployeeDocumentRequestStatus = 'REQUESTED' | 'SUBMITTED' | 'VERIFIED' | 'REJECTED' | 'WAIVED'
export type BloodType =
  | 'A_POSITIVE'
  | 'A_NEGATIVE'
  | 'B_POSITIVE'
  | 'B_NEGATIVE'
  | 'AB_POSITIVE'
  | 'AB_NEGATIVE'
  | 'O_POSITIVE'
  | 'O_NEGATIVE'
  | 'UNKNOWN'
export type FamilyRelation =
  | 'SPOUSE'
  | 'FATHER'
  | 'MOTHER'
  | 'SON'
  | 'DAUGHTER'
  | 'BROTHER'
  | 'SISTER'
  | 'OTHER'
export type LeaveRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'WITHDRAWN'
export type OnDutyRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'WITHDRAWN'
export type ApprovalRequestKind = 'LEAVE' | 'ON_DUTY'
export type ApprovalActionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SKIPPED' | 'CANCELLED'
export type HolidayCalendarStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
export type HolidayClassification = 'PUBLIC' | 'RESTRICTED' | 'COMPANY'
export type LeaveCycleType = 'CALENDAR_YEAR' | 'FINANCIAL_YEAR' | 'CUSTOM_FIXED_START' | 'EMPLOYEE_JOINING_DATE'
export type LeaveCreditFrequency = 'MANUAL' | 'MONTHLY' | 'QUARTERLY' | 'HALF_YEARLY' | 'YEARLY'
export type CarryForwardMode = 'NONE' | 'CAPPED' | 'UNLIMITED'
export type ApprovalApproverType = 'REPORTING_MANAGER' | 'SPECIFIC_EMPLOYEE' | 'PRIMARY_ORG_ADMIN'
export type ApprovalFallbackType = 'NONE' | 'SPECIFIC_EMPLOYEE' | 'PRIMARY_ORG_ADMIN'
export type ApprovalStageMode = 'ALL' | 'ANY'

export interface LinkedOrganisationAddress {
  id: string
  address_type: string
  address_type_label: string
  label: string
  line1: string
  line2: string
  city: string
  state: string
  state_code: string
  country: string
  country_code: string
  pincode: string
  gstin: string | null
  is_active: boolean
}

export interface Location {
  id: string
  name: string
  organisation_address: LinkedOrganisationAddress | null
  organisation_address_id: string | null
  address: string
  city: string
  state: string
  country: string
  pincode: string
  is_remote: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Department {
  id: string
  name: string
  description: string
  parent_department_id: string | null
  parent_department_name: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EmployeeListItem {
  id: string
  employee_code: string | null
  full_name: string
  email: string
  designation: string
  employment_type: EmploymentType
  date_of_joining: string | null
  status: EmployeeStatus
  department_name: string | null
  office_location_name: string | null
}

export interface EmployeeProfile {
  date_of_birth?: string | null
  gender?: string
  marital_status?: string
  nationality?: string
  blood_type?: BloodType | ''
  phone_personal?: string
  phone_emergency?: string
  emergency_contact_name?: string
  emergency_contact_relation?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  state_code?: string
  country?: string
  country_code?: string
  pincode?: string
}

export interface FamilyMember {
  id: string
  full_name: string
  relation: FamilyRelation
  date_of_birth: string | null
  contact_number: string
  is_dependent: boolean
  created_at: string
  updated_at: string
}

export interface EmergencyContact {
  id: string
  full_name: string
  relation: string
  phone_number: string
  alternate_phone_number: string
  address: string
  is_primary: boolean
  created_at: string
  updated_at: string
}

export interface EducationRecord {
  id: string
  degree: string
  institution: string
  field_of_study: string
  start_year: number | null
  end_year: number | null
  grade: string
  is_current: boolean
  created_at: string
  updated_at: string
}

export interface GovernmentId {
  id: string
  id_type: GovernmentIdType
  identifier: string
  name_on_id: string
  status: GovernmentIdStatus
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface BankAccount {
  id: string
  account_holder_name: string
  bank_name: string
  account_number: string
  ifsc: string
  account_type: BankAccountType
  branch_name: string
  is_primary: boolean
  created_at: string
  updated_at: string
}

export interface EmployeeDetail {
  id: string
  employee_code: string | null
  suggested_employee_code: string
  full_name: string
  email: string
  designation: string
  employment_type: EmploymentType
  date_of_joining: string | null
  date_of_exit: string | null
  status: EmployeeStatus
  onboarding_status: EmployeeOnboardingStatus
  department: string | null
  office_location: string | null
  reporting_to: string | null
  profile: EmployeeProfile
  education_records: EducationRecord[]
  government_ids: GovernmentId[]
  bank_accounts: BankAccount[]
  family_members: FamilyMember[]
  emergency_contacts: EmergencyContact[]
}

export interface ProfileCompletion {
  percent: number
  completed_sections: string[]
  missing_sections: string[]
}

export interface EmployeeDashboard {
  profile_completion: ProfileCompletion
  pending_documents: number
  verified_documents: number
  rejected_documents: number
  pending_document_requests: number
  employee_code: string | null
  onboarding_status: EmployeeOnboardingStatus
  approvals: {
    count: number
    items: Array<{
      action_id: string
      label: string
      request_kind: string
      stage_name: string
    }>
  }
  notices: NoticeItem[]
  events: EmployeeEvent[]
  leave_balances: LeaveBalanceSnapshot[]
  calendar: CalendarMonthView
}

export interface MyProfileResponse {
  employee: EmployeeDetail
  profile: EmployeeProfile
  profile_completion: ProfileCompletion
}

export interface DocumentRecord {
  id: string
  document_type: DocumentType
  document_type_code: string
  document_request: string | null
  file_name: string
  file_size: number
  mime_type: string
  status: DocumentStatus
  metadata: Record<string, unknown>
  version: number
  uploaded_by_email: string | null
  reviewed_by_email: string | null
  reviewed_at: string | null
  created_at: string
}

export interface OnboardingDocumentType {
  id: string
  code: string
  name: string
  category: OnboardingDocumentCategory
  description: string
  is_active: boolean
  is_custom: boolean
  requires_identifier: boolean
  sort_order: number
}

export interface EmployeeDocumentRequest {
  id: string
  document_type: OnboardingDocumentType
  is_required: boolean
  status: EmployeeDocumentRequestStatus
  note: string
  rejection_note: string
  latest_uploaded_at: string | null
  verified_at: string | null
  latest_submission: DocumentRecord | null
  created_at: string
  updated_at: string
}

export interface OnboardingSummary {
  employee_id: string
  employee_status: EmployeeStatus
  onboarding_status: EmployeeOnboardingStatus
  profile_completion: ProfileCompletion
  required_document_count: number
  submitted_document_count: number
}

export interface MyOnboardingResponse {
  summary: OnboardingSummary
  employee: EmployeeDetail
  profile: EmployeeProfile
  family_members: FamilyMember[]
  emergency_contacts: EmergencyContact[]
  government_ids: GovernmentId[]
}

export interface ApprovalActionItem {
  id: string
  status: ApprovalActionStatus
  comment: string
  acted_at: string | null
  request_kind: ApprovalRequestKind
  subject_label: string
  requester_name: string
  requester_employee_id: string
  stage_name: string
  organisation_id: string
  created_at: string
  updated_at: string
}

export interface LeaveBalanceSnapshot {
  leave_type_id: string
  leave_type_name: string
  color: string
  available: string
  credited: string
  used: string
  pending: string
}

export interface NoticeItem {
  id: string
  title: string
  body: string
  audience_type: string
  status: string
  scheduled_for: string | null
  published_at: string | null
  department_ids: string[]
  office_location_ids: string[]
  employee_ids: string[]
  created_at: string
  updated_at: string
}

export interface EmployeeEvent {
  kind: 'BIRTHDAY' | 'WORK_ANNIVERSARY'
  label: string
  date: string
}

export interface CalendarEntry {
  date: string
  kind: 'HOLIDAY' | 'LEAVE' | 'ON_DUTY'
  label: string
  status: string
  color: string
  session: string
}

export interface CalendarDay {
  date: string
  entries: CalendarEntry[]
}

export interface CalendarMonthView {
  month: string | null
  days: CalendarDay[]
}

export interface LeaveTypeConfig {
  id: string
  code: string
  name: string
  description: string
  color: string
  is_paid: boolean
  is_loss_of_pay: boolean
  annual_entitlement: string
  credit_frequency: LeaveCreditFrequency
  credit_day_of_period: number | null
  prorate_on_join: boolean
  carry_forward_mode: CarryForwardMode
  carry_forward_cap: string | null
  max_balance: string | null
  allows_half_day: boolean
  requires_attachment: boolean
  attachment_after_days: string | null
  min_notice_days: number
  max_consecutive_days: number | null
  allow_past_request: boolean
  allow_future_request: boolean
  is_active: boolean
}

export interface LeaveCycle {
  id: string
  name: string
  cycle_type: LeaveCycleType
  start_month: number
  start_day: number
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LeavePlanRuleConfig {
  id: string
  name: string
  priority: number
  is_active: boolean
  department: string | null
  office_location: string | null
  specific_employee: string | null
  employment_type: string
  designation: string
}

export interface LeavePlan {
  id: string
  name: string
  description: string
  is_default: boolean
  is_active: boolean
  priority: number
  leave_cycle: LeaveCycle
  leave_types: LeaveTypeConfig[]
  rules: LeavePlanRuleConfig[]
  created_at: string
  updated_at: string
}

export interface LeaveRequestRecord {
  id: string
  employee: string
  employee_name: string
  leave_type: string
  leave_type_name: string
  start_date: string
  end_date: string
  start_session: string
  end_session: string
  total_units: string
  reason: string
  status: LeaveRequestStatus
  rejection_reason: string
  created_at: string
  updated_at: string
}

export interface LeaveOverview {
  balances: LeaveBalanceSnapshot[]
  requests: LeaveRequestRecord[]
  leave_plan: LeavePlan | null
}

export interface OnDutyPolicy {
  id: string
  name: string
  description: string
  is_default: boolean
  is_active: boolean
  allow_half_day: boolean
  allow_time_range: boolean
  requires_attachment: boolean
  min_notice_days: number
  allow_past_request: boolean
  allow_future_request: boolean
  created_at: string
  updated_at: string
}

export interface OnDutyRequestRecord {
  id: string
  employee: string
  employee_name: string
  policy: string
  policy_name: string
  start_date: string
  end_date: string
  duration_type: string
  start_time: string | null
  end_time: string | null
  total_units: string
  purpose: string
  destination: string
  status: OnDutyRequestStatus
  rejection_reason: string
  created_at: string
  updated_at: string
}

export interface HolidayRecord {
  id: string
  name: string
  holiday_date: string
  classification: HolidayClassification
  session: string
  description: string
}

export interface HolidayCalendar {
  id: string
  name: string
  year: number
  description: string
  status: HolidayCalendarStatus
  is_default: boolean
  location_ids: string[]
  holidays: HolidayRecord[]
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface ApprovalStageApproverConfig {
  id: string
  approver_type: ApprovalApproverType
  approver_employee_id: string | null
  approver_employee_name: string | null
}

export interface ApprovalStageConfig {
  id: string
  name: string
  sequence: number
  mode: ApprovalStageMode
  fallback_type: ApprovalFallbackType
  fallback_employee_id: string | null
  fallback_employee_name: string | null
  approvers: ApprovalStageApproverConfig[]
}

export interface ApprovalWorkflowRuleConfig {
  id: string
  name: string
  request_kind: ApprovalRequestKind
  priority: number
  is_active: boolean
  department: string | null
  department_name: string | null
  office_location: string | null
  office_location_name: string | null
  specific_employee: string | null
  specific_employee_name: string | null
  employment_type: string
  designation: string
  leave_type: string | null
  leave_type_name: string | null
}

export interface ApprovalWorkflowConfig {
  id: string
  name: string
  description: string
  is_default: boolean
  is_active: boolean
  rules: ApprovalWorkflowRuleConfig[]
  stages: ApprovalStageConfig[]
  created_at: string
  updated_at: string
}
