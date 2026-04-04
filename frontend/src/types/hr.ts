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
export type ApprovalRequestKind =
  | 'LEAVE'
  | 'ON_DUTY'
  | 'ATTENDANCE_REGULARIZATION'
  | 'PAYROLL_PROCESSING'
  | 'SALARY_REVISION'
  | 'COMPENSATION_TEMPLATE_CHANGE'
export type ApprovalActionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SKIPPED' | 'CANCELLED'
export type HolidayCalendarStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
export type HolidayClassification = 'PUBLIC' | 'RESTRICTED' | 'COMPANY'
export type LeaveCycleType = 'CALENDAR_YEAR' | 'FINANCIAL_YEAR' | 'CUSTOM_FIXED_START' | 'EMPLOYEE_JOINING_DATE'
export type LeaveCreditFrequency = 'MANUAL' | 'MONTHLY' | 'QUARTERLY' | 'HALF_YEARLY' | 'YEARLY'
export type CarryForwardMode = 'NONE' | 'CAPPED' | 'UNLIMITED'
export type ApprovalApproverType = 'REPORTING_MANAGER' | 'SPECIFIC_EMPLOYEE' | 'PRIMARY_ORG_ADMIN'
export type ApprovalFallbackType = 'NONE' | 'SPECIFIC_EMPLOYEE' | 'PRIMARY_ORG_ADMIN'
export type ApprovalStageMode = 'ALL' | 'ANY'
export type EffectiveApprovalWorkflowSource = 'ASSIGNMENT' | 'RULE' | 'DEFAULT' | 'UNCONFIGURED'
export type NoticeStatus = 'DRAFT' | 'SCHEDULED' | 'PUBLISHED' | 'EXPIRED' | 'ARCHIVED'
export type NoticeCategory = 'GENERAL' | 'HR_POLICY' | 'OPERATIONS' | 'CELEBRATION' | 'COMPLIANCE' | 'URGENT'
export type NoticeAudienceType = 'ALL_EMPLOYEES' | 'DEPARTMENTS' | 'OFFICE_LOCATIONS' | 'SPECIFIC_EMPLOYEES'
export type AttendanceImportMode = 'ATTENDANCE_SHEET' | 'PUNCH_SHEET'
export type AttendanceImportStatus = 'FAILED' | 'READY_FOR_REVIEW' | 'POSTED'
export type AttendanceDayStatus = 'PRESENT' | 'HALF_DAY' | 'ABSENT' | 'INCOMPLETE' | 'HOLIDAY' | 'WEEK_OFF' | 'ON_LEAVE' | 'ON_DUTY'
export type AttendanceRegularizationStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'WITHDRAWN'
export type BiometricProtocol = 'ZK_ADMS' | 'ESSL_EBIOSERVER' | 'MATRIX_COSEC' | 'SUPREMA_BIOSTAR' | 'HIKVISION_ISAPI'
export type OffboardingProcessStatus = 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
export type OffboardingTaskStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'WAIVED'
export type OffboardingTaskOwner = 'ORG_ADMIN' | 'MANAGER' | 'EMPLOYEE' | 'PAYROLL' | 'IT'

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
  modified_at: string
}

export interface Department {
  id: string
  name: string
  description: string
  parent_department_id: string | null
  parent_department_name: string | null
  is_active: boolean
  created_at: string
  modified_at: string
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

export interface CtEmployeeListItem {
  id: string
  employee_code: string | null
  full_name: string
  designation: string
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
  modified_at: string
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
  modified_at: string
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
  modified_at: string
}

export interface GovernmentId {
  id: string
  id_type: GovernmentIdType
  identifier: string
  name_on_id: string
  status: GovernmentIdStatus
  metadata: Record<string, unknown>
  created_at: string
  modified_at: string
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
  modified_at: string
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
  probation_end_date: string | null
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
  leave_approval_workflow_id: string | null
  leave_approval_workflow_name: string | null
  on_duty_approval_workflow_id: string | null
  on_duty_approval_workflow_name: string | null
  attendance_regularization_approval_workflow_id: string | null
  attendance_regularization_approval_workflow_name: string | null
  effective_approval_workflows: {
    leave: EffectiveApprovalWorkflowSummary
    on_duty: EffectiveApprovalWorkflowSummary
    attendance_regularization: EffectiveApprovalWorkflowSummary
  }
  offboarding: OffboardingProcess | null
}

export interface OffboardingTask {
  id: string
  code: string
  title: string
  description: string
  owner: OffboardingTaskOwner
  status: OffboardingTaskStatus
  note: string
  due_date: string | null
  is_required: boolean
  completed_at: string | null
  completed_by_name: string
}

export interface OffboardingProcess {
  id: string
  status: OffboardingProcessStatus
  exit_status: EmployeeStatus
  date_of_exit: string
  exit_reason: string
  exit_notes: string
  started_at: string | null
  completed_at: string | null
  required_task_count: number
  completed_required_task_count: number
  pending_required_task_count: number
  pending_document_requests: number
  has_primary_bank_account: boolean
  tasks: OffboardingTask[]
}

export type FNFStatus = 'DRAFT' | 'CALCULATED' | 'APPROVED' | 'PAID' | 'CANCELLED'

export interface FullAndFinalSettlement {
  id: string
  employee_id: string
  employee_name: string
  offboarding_process_id: string | null
  last_working_day: string
  status: FNFStatus
  prorated_salary: string
  leave_encashment: string
  gratuity: string
  arrears: string
  other_credits: string
  tds_deduction: string
  pf_deduction: string
  loan_recovery: string
  other_deductions: string
  gross_payable: string
  net_payable: string
  notes: string
  approved_at: string | null
  paid_at: string | null
  created_at: string
  modified_at: string
}

export interface Arrears {
  id: string
  employee_id: string
  employee_name: string
  pay_run_id: string | null
  for_period_year: number
  for_period_month: number
  reason: string
  amount: string
  is_included_in_payslip: boolean
  created_at: string
}

export interface CtEmployeeDetail {
  id: string
  employee_code: string | null
  full_name: string
  designation: string
  employment_type: EmploymentType
  date_of_joining: string | null
  date_of_exit: string | null
  status: EmployeeStatus
  onboarding_status: EmployeeOnboardingStatus
  department_name: string | null
  office_location_name: string | null
  reporting_to_name: string | null
}

export interface CtSupportDiagnostic {
  code: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  detail: string
  action: string
}

export interface CtOrganisationPayrollRunSummary {
  id: string
  name: string
  period_year: number
  period_month: number
  run_type: PayrollRunType
  status: PayrollRunStatus
  created_at: string
  calculated_at: string | null
  submitted_at: string | null
  finalized_at: string | null
  ready_count: number
  exception_count: number
  exception_messages: string[]
  attendance_snapshot_summary: {
    attendance_source: string
    period_start: string | null
    period_end: string | null
    use_attendance_inputs?: boolean
    employee_count: number
    ready_item_count: number
    exception_item_count: number
    total_attendance_paid_days: string
    total_lop_days: string
    total_overtime_minutes: number
  }
}

export interface CtOrganisationPayrollSupportSummary {
  tax_slab_set_count: number
  compensation_template_count: number
  approved_assignment_count: number
  pending_assignment_count: number
  payslip_count: number
  diagnostics: CtSupportDiagnostic[]
  payroll_runs: CtOrganisationPayrollRunSummary[]
}

export interface CtOrganisationApprovalRunSummary {
  id: string
  request_kind: ApprovalRequestKind
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED'
  subject_label: string
  requester_name: string
  current_stage_sequence: number
  workflow_name: string
  pending_actions_count: number
  created_at: string
  modified_at: string
}

export interface CtOrganisationApprovalSupportSummary {
  workflows_count: number
  active_workflows_count: number
  default_workflows_count: number
  pending_runs_count: number
  approved_runs_count: number
  rejected_runs_count: number
  pending_actions_count: number
  recent_runs: CtOrganisationApprovalRunSummary[]
}

export interface CtOrganisationAttendanceSupportSummary {
  policy_count: number
  source_count: number
  active_source_count: number
  pending_regularizations: number
  diagnostics: CtSupportDiagnostic[]
  today_summary: {
    date: string
    total_employees: number
    present_count: number
    half_day_count: number
    absent_count: number
    incomplete_count: number
    on_leave_count: number
    on_duty_count: number
  }
  recent_imports: Array<{
    id: string
    mode: AttendanceImportMode
    status: AttendanceImportStatus
    original_filename: string
    valid_rows: number
    error_rows: number
    posted_rows: number
    created_at: string
  }>
}

export interface CtOrganisationOnboardingBlockedEmployee {
  id: string
  employee_code: string | null
  full_name: string
  designation: string
  status: EmployeeStatus
  onboarding_status: EmployeeOnboardingStatus
  pending_document_requests: number
  latest_document_activity_at: string | null
}

export interface CtOrganisationOnboardingBlockerType {
  document_type_code: string
  document_type_name: string
  blocked_employee_count: number
}

export interface CtOrganisationOnboardingSupportSummary {
  onboarding_status_counts: Record<EmployeeOnboardingStatus, number>
  document_request_status_counts: Record<EmployeeDocumentRequestStatus, number>
  blocked_employees: CtOrganisationOnboardingBlockedEmployee[]
  top_blocker_types: CtOrganisationOnboardingBlockerType[]
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
  offboarding: OffboardingProcess | null
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
  modified_at: string
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
  modified_at: string
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
  category: NoticeCategory
  audience_type: NoticeAudienceType
  status: NoticeStatus
  is_sticky: boolean
  scheduled_for: string | null
  published_at: string | null
  expires_at: string | null
  department_ids: string[]
  office_location_ids: string[]
  employee_ids: string[]
  created_at: string
  modified_at: string
}

export interface AttendanceImportErrorPreview {
  row_number: number
  employee_code: string
  message: string
}

export interface AttendanceImportJob {
  id: string
  mode: AttendanceImportMode
  status: AttendanceImportStatus
  original_filename: string
  uploaded_by_email: string | null
  total_rows: number
  valid_rows: number
  error_rows: number
  posted_rows: number
  normalized_file_available: boolean
  error_preview: AttendanceImportErrorPreview[]
  created_at: string
  modified_at: string
}

export interface AttendancePolicy {
  id: string
  name: string
  timezone_name: string
  default_start_time: string
  default_end_time: string
  grace_minutes: number
  full_day_min_minutes: number
  half_day_min_minutes: number
  overtime_after_minutes: number
  week_off_days: number[]
  allow_web_punch: boolean
  restrict_by_ip: boolean
  allowed_ip_ranges: string[]
  restrict_by_geo: boolean
  allowed_geo_sites: Array<Record<string, unknown>>
  is_default: boolean
  is_active: boolean
  created_at: string
  modified_at: string
}

export interface AttendanceShift {
  id: string
  name: string
  start_time: string
  end_time: string
  grace_minutes: number | null
  full_day_min_minutes: number | null
  half_day_min_minutes: number | null
  overtime_after_minutes: number | null
  is_overnight: boolean
  is_active: boolean
  created_at: string
  modified_at: string
}

export interface AttendanceShiftAssignment {
  id: string
  employee_id: string
  employee_name: string
  employee_code: string | null
  shift: string
  shift_name: string
  start_date: string
  end_date: string | null
  is_active: boolean
  created_at: string
  modified_at: string
}

export interface AttendanceDayRecord {
  id: string
  employee_id: string
  employee_name: string
  employee_code: string | null
  attendance_date: string
  status: AttendanceDayStatus
  source: string
  check_in_at: string | null
  check_out_at: string | null
  worked_minutes: number
  overtime_minutes: number
  late_minutes: number
  paid_fraction: string
  leave_fraction: string
  on_duty_fraction: string
  is_holiday: boolean
  is_week_off: boolean
  is_late: boolean
  needs_regularization: boolean
  raw_punch_count: number
  note: string
  metadata: Record<string, unknown>
  shift_name: string | null
  policy_name: string | null
  created_at: string
  modified_at: string
}

export interface AttendanceRegularization {
  id: string
  attendance_day: string | null
  attendance_date: string
  employee_name: string
  employee_code: string | null
  requested_check_in_at: string | null
  requested_check_out_at: string | null
  reason: string
  status: AttendanceRegularizationStatus
  rejection_reason: string
  approval_run_id: string | null
  created_at: string
  modified_at: string
}

export interface AttendanceSourceConfig {
  id: string
  name: string
  kind: 'API' | 'EXCEL' | 'DEVICE'
  configuration: Record<string, unknown>
  api_key_masked: string
  raw_api_key?: string
  is_active: boolean
  last_error: string
  created_at: string
  modified_at: string
}

export interface BiometricDevice {
  id: string
  name: string
  device_serial: string
  protocol: BiometricProtocol
  ip_address: string | null
  port: number
  auth_username: string
  oauth_client_id: string
  location_id: string | null
  secret_preview: string
  endpoint_path: string
  is_active: boolean
  last_sync_at: string | null
  created_at: string
}

export interface BiometricSyncLog {
  id: string
  synced_at: string
  records_fetched: number
  records_processed: number
  records_skipped: number
  errors: string[]
  success: boolean
}

export interface RecruitmentInterview {
  id: string
  application: string
  interviewer_id: string | null
  interviewer_name: string | null
  scheduled_at: string
  format: string
  feedback: string
  outcome: string
  meet_link: string
  created_at: string
}

export interface RecruitmentOfferLetter {
  id: string
  application_id: string
  ctc_annual: string
  joining_date: string | null
  status: string
  template_text: string
  sent_at: string | null
  accepted_at: string | null
  expires_at: string | null
  onboarded_employee_id: string | null
}

export interface RecruitmentApplication {
  id: string
  candidate: string
  candidate_name: string
  candidate_email: string
  job_posting_id: string
  job_posting_title: string
  stage: string
  applied_at: string
  notes: string
  rejection_reason: string
  interviews: RecruitmentInterview[]
  offer_letter: RecruitmentOfferLetter | null
}

export interface RecruitmentCandidateDetail {
  id: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  source: string
  created_at: string
  applications: RecruitmentApplication[]
}

export interface RecruitmentJobPosting {
  id: string
  title: string
  department_id: string | null
  department_name: string | null
  location_id: string | null
  location_name: string | null
  description: string
  requirements: string
  status: string
  posted_at: string | null
  closes_at: string | null
  application_count: number
  created_at: string
}

export interface PerformanceGoalCycle {
  id: string
  name: string
  start_date: string
  end_date: string
  status: string
  created_at: string
}

export interface PerformanceGoal {
  id: string
  cycle: string
  employee: string
  title: string
  description: string
  target: string
  metric: string
  weight: string
  status: string
  due_date: string | null
  progress_percent: number
  created_at: string
}

export interface PerformanceAppraisalCycle {
  id: string
  name: string
  review_type: string
  start_date: string
  end_date: string
  status: string
  is_probation_review: boolean
  created_at: string
}

export interface PerformanceReview {
  id: string
  cycle: string
  employee: string
  reviewer: string | null
  relationship: string
  ratings: Record<string, number>
  comments: string
  status: string
  submitted_at: string | null
}

export interface OrgAttendanceDashboard {
  date: string
  total_employees: number
  present_count: number
  half_day_count: number
  absent_count: number
  incomplete_count: number
  holiday_count: number
  week_off_count: number
  on_leave_count: number
  on_duty_count: number
  pending_regularizations: number
  days: AttendanceDayRecord[]
}

export interface OrgAttendanceReport {
  month: string
  employee_count: number
  present_days: number
  half_days: number
  absent_days: number
  incomplete_days: number
  late_marks: number
  overtime_minutes: number
  rows: AttendanceDayRecord[]
}

export interface EmployeeAttendanceSummary {
  today: AttendanceDayRecord
  policy: AttendancePolicy
  shift: AttendanceShift | null
  pending_regularizations: AttendanceRegularization[]
}

export interface EmployeeAttendanceCalendar {
  month: string
  days: Array<{
    date: string
    status: AttendanceDayStatus
    is_late: boolean
    needs_regularization: boolean
    worked_minutes: number
    overtime_minutes: number
  }>
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
  allows_encashment: boolean
  max_encashment_days_per_year: string | null
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
  leave_plan_count: number
  active_leave_plan_count: number
  created_at: string
  modified_at: string
}

export interface LeavePlanRuleConfig {
  id: string
  name: string
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
  modified_at: string
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
  modified_at: string
}

export interface LeaveOverview {
  balances: LeaveBalanceSnapshot[]
  requests: LeaveRequestRecord[]
  leave_plan: LeavePlan | null
}

export interface LeaveEncashmentRequest {
  id: string
  employee_id: string
  employee_name: string
  leave_type_id: string
  leave_type_name: string
  cycle_start: string
  cycle_end: string
  days_to_encash: string
  encashment_amount: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'PAID' | 'CANCELLED'
  rejection_reason: string
  created_at: string
  modified_at: string
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
  modified_at: string
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
  modified_at: string
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
  modified_at: string
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
  default_request_kind: ApprovalRequestKind | null
  is_active: boolean
  rules: ApprovalWorkflowRuleConfig[]
  stages: ApprovalStageConfig[]
  created_at: string
  modified_at: string
}

export interface EffectiveApprovalWorkflowSummary {
  request_kind: ApprovalRequestKind
  workflow_id: string | null
  workflow_name: string | null
  source: EffectiveApprovalWorkflowSource
}

export type PayrollComponentType = 'EARNING' | 'EMPLOYEE_DEDUCTION' | 'EMPLOYER_CONTRIBUTION' | 'REIMBURSEMENT'
export type CompensationTemplateStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED'
export type CompensationAssignmentStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED'
export type PayrollRunStatus = 'DRAFT' | 'CALCULATED' | 'APPROVAL_PENDING' | 'APPROVED' | 'REJECTED' | 'FINALIZED' | 'CANCELLED'
export type PayrollRunType = 'REGULAR' | 'RERUN'
export type StatutoryFilingType = 'PF_ECR' | 'ESI_MONTHLY' | 'FORM24Q' | 'PROFESSIONAL_TAX' | 'FORM16'
export type StatutoryFilingStatus = 'READY' | 'BLOCKED' | 'GENERATED' | 'SUPERSEDED' | 'CANCELLED'
export type StatutoryFilingArtifactFormat = 'CSV' | 'JSON' | 'XML' | 'PDF' | 'TEXT'

export interface PayrollTaxSlab {
  id: string
  min_income: string
  max_income: string | null
  rate_percent: string
}

export interface PayrollTaxSlabSet {
  id: string
  name: string
  country_code: string
  fiscal_year: string
  is_active: boolean
  is_system_master: boolean
  source_set_id: string | null
  slabs: PayrollTaxSlab[]
  created_at: string
  modified_at: string
}

export interface PayrollComponent {
  id: string
  code: string
  name: string
  component_type: PayrollComponentType
  is_taxable: boolean
  is_system_default: boolean
}

export interface CompensationTemplateLine {
  id: string
  component_id: string
  component: PayrollComponent
  monthly_amount: string
  sequence: number
}

export interface CompensationTemplate {
  id: string
  name: string
  description: string
  status: CompensationTemplateStatus
  approval_run_id: string | null
  lines: CompensationTemplateLine[]
  created_at: string
  modified_at: string
}

export interface CompensationAssignmentLine {
  id: string
  component_id: string
  component_name: string
  component_type: PayrollComponentType
  monthly_amount: string
  is_taxable: boolean
  sequence: number
}

export interface CompensationAssignment {
  id: string
  employee_id: string
  employee_name: string
  template: string
  template_name: string
  effective_from: string
  version: number
  status: CompensationAssignmentStatus
  approval_run_id: string | null
  lines: CompensationAssignmentLine[]
  created_at: string
  modified_at: string
}

export interface PayrollRunItem {
  id: string
  employee_id: string
  employee_name: string
  status: 'READY' | 'EXCEPTION'
  gross_pay: string
  employee_deductions: string
  employer_contributions: string
  income_tax: string
  total_deductions: string
  net_pay: string
  snapshot: Record<string, unknown>
  message: string
}

export interface PayrollRunAttendanceSnapshotEmployee {
  employee_id: string
  employee_code: string
  status: 'READY' | 'EXCEPTION'
  active_period_start?: string
  active_period_end?: string
  attendance_paid_days?: string
  effective_lop_days?: string
  attendance_overtime_minutes?: number
  reason?: string
}

export interface PayrollRunAttendanceSnapshot {
  attendance_source: string
  period_start: string
  period_end: string
  use_attendance_inputs: boolean
  employee_count: number
  ready_item_count: number
  exception_item_count: number
  total_attendance_paid_days: string
  total_lop_days: string
  total_overtime_minutes: number
  employees: PayrollRunAttendanceSnapshotEmployee[]
}

export interface PayrollRun {
  id: string
  name: string
  period_year: number
  period_month: number
  run_type: PayrollRunType
  status: PayrollRunStatus
  use_attendance_inputs: boolean
  approval_run_id: string | null
  source_run_id: string | null
  attendance_snapshot: PayrollRunAttendanceSnapshot
  calculated_at: string | null
  submitted_at: string | null
  finalized_at: string | null
  items: PayrollRunItem[]
  created_at: string
  modified_at: string
}

export interface Payslip {
  id: string
  employee_id: string
  pay_run_id: string
  slip_number: string
  period_year: number
  period_month: number
  snapshot: Record<string, unknown>
  rendered_text: string
  created_at: string
}

export interface StatutoryFilingBatch {
  id: string
  filing_type: StatutoryFilingType
  status: StatutoryFilingStatus
  artifact_format: StatutoryFilingArtifactFormat
  period_year: number | null
  period_month: number | null
  fiscal_year: string
  quarter: string
  checksum: string
  file_name: string
  content_type: string
  file_size_bytes: number
  generated_at: string | null
  source_signature: string
  validation_errors: string[]
  metadata: Record<string, unknown>
  structured_payload: Record<string, unknown>
  source_pay_run_ids: string[]
  created_at: string
  modified_at: string
}

export interface PayrollTdsChallan {
  id: string
  fiscal_year: string
  quarter: 'Q1' | 'Q2' | 'Q3' | 'Q4'
  period_year: number
  period_month: number
  bsr_code: string
  challan_serial_number: string
  deposit_date: string
  tax_deposited: string
  interest_amount: string
  fee_amount: string
  statement_receipt_number: string
  notes: string
  created_at: string
  modified_at: string
}

export interface OrgPayrollSummary {
  tax_slab_sets: PayrollTaxSlabSet[]
  components: PayrollComponent[]
  compensation_templates: CompensationTemplate[]
  compensation_assignments: CompensationAssignment[]
  pay_runs: PayrollRun[]
  statutory_filing_batches: StatutoryFilingBatch[]
  tds_challans: PayrollTdsChallan[]
  payslip_count: number
}
