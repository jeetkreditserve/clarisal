export type OrganisationStatus = 'PENDING' | 'PAID' | 'ACTIVE' | 'SUSPENDED'
export type OrganisationBillingStatus = 'PENDING_PAYMENT' | 'PAID'
export type OrganisationAccessState = 'PROVISIONING' | 'ACTIVE' | 'SUSPENDED'
export type OrganisationEntityType =
  | 'PRIVATE_LIMITED'
  | 'PUBLIC_LIMITED'
  | 'LIMITED_LIABILITY_PARTNERSHIP'
  | 'PARTNERSHIP_FIRM'
  | 'SOLE_PROPRIETORSHIP'
  | 'ONE_PERSON_COMPANY'
  | 'SECTION_8_COMPANY'
  | 'TRUST'
  | 'SOCIETY'
  | 'GOVERNMENT_BODY'
  | 'OTHER'
export type OrganisationAddressType =
  | 'REGISTERED'
  | 'BILLING'
  | 'HEADQUARTERS'
  | 'WAREHOUSE'
  | 'CUSTOM'
export type LicenceBatchPaymentStatus = 'DRAFT' | 'PAID'
export type LicenceBatchLifecycleState = 'DRAFT' | 'PAID_PENDING_START' | 'ACTIVE' | 'EXPIRED'
export type TenantDataExportType = 'EMPLOYEES' | 'PAYSLIPS' | 'LEAVE_HISTORY' | 'AUDIT_LOG'
export type TenantDataExportStatus = 'REQUESTED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
export type OrganisationOnboardingStage =
  | 'ORG_CREATED'
  | 'LICENCES_ASSIGNED'
  | 'PAYMENT_CONFIRMED'
  | 'ADMIN_INVITED'
  | 'ADMIN_ACTIVATED'
  | 'MASTER_DATA_CONFIGURED'
  | 'EMPLOYEES_INVITED'
export type OrgAdminSetupStep =
  | 'PROFILE'
  | 'ADDRESSES'
  | 'LOCATIONS'
  | 'DEPARTMENTS'
  | 'HOLIDAYS'
  | 'POLICIES'
  | 'EMPLOYEES'

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface OrganisationListItem {
  id: string
  name: string
  slug: string
  status: OrganisationStatus
  status_label: string
  billing_status: OrganisationBillingStatus
  access_state: OrganisationAccessState
  onboarding_stage: OrganisationOnboardingStage
  licence_count: number
  entity_type?: OrganisationEntityType
  created_at: string
}

export interface OrganisationAddress {
  id: string
  address_type: OrganisationAddressType
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
  created_at: string
  modified_at: string
}

export interface BootstrapAdminSummary {
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  status: 'DRAFT' | 'INVITE_PENDING' | 'INVITE_ACCEPTED'
  invited_user_id: string | null
  invited_user_email: string | null
  invitation_sent_at: string | null
  accepted_at: string | null
  modified_at: string
}

export interface OrganisationNote {
  id: string
  body: string
  created_at: string
  created_by: {
    id: string
    full_name: string
    email: string
  }
}

export interface StateTransition {
  id: string
  from_status: OrganisationStatus
  to_status: OrganisationStatus
  note: string
  transitioned_by_email: string
  created_at: string
}

export interface LifecycleEvent {
  id: string
  event_type: string
  actor_email: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface LicenceLedgerEntry {
  id: string
  delta: number
  reason: string
  note: string
  effective_from: string
  created_by_email: string | null
  created_at: string
}

export interface LicenceSummary {
  active_paid_quantity: number
  allocated: number
  available: number
  overage: number
  has_overage: boolean
  utilisation_percent: number
}

export interface LicenceBatch {
  id: string
  quantity: number
  price_per_licence_per_month: string
  start_date: string
  end_date: string
  billing_months: number
  total_amount: string
  payment_status: LicenceBatchPaymentStatus
  lifecycle_state: LicenceBatchLifecycleState
  note: string
  payment_provider: string
  payment_reference: string
  invoice_reference: string
  created_by_email: string | null
  paid_by_email: string | null
  paid_at: string | null
  created_at: string
  modified_at: string
}

export interface TenantDataExportBatch {
  id: string
  export_type: TenantDataExportType
  status: TenantDataExportStatus
  file_name: string | null
  content_type: string | null
  file_size_bytes: number | null
  generated_at: string | null
  failure_reason: string
  metadata: Record<string, unknown>
  requested_by: {
    id: string
    full_name: string
    email: string
  } | null
  created_at: string
  modified_at: string
}

export interface TenantDataExportDownloadResponse {
  download_url: string
  file_name: string | null
}

export interface CtOrganisationAnalyticsPoint {
  date: string
  value: number
}

export interface CtOrganisationAnalyticsLatest {
  snapshot_date: string
  active_employees: number
  active_users: number
  attendance_days_count: number
  leave_requests_count: number
  payroll_runs_count: number
  pending_approvals_count: number
  metadata: Record<string, unknown>
}

export interface CtOrganisationAnalytics {
  latest: CtOrganisationAnalyticsLatest
  series: {
    active_employees: CtOrganisationAnalyticsPoint[]
    active_users: CtOrganisationAnalyticsPoint[]
    attendance_days_count: CtOrganisationAnalyticsPoint[]
    leave_requests_count: CtOrganisationAnalyticsPoint[]
    payroll_runs_count: CtOrganisationAnalyticsPoint[]
    pending_approvals_count: CtOrganisationAnalyticsPoint[]
  }
}

export interface LicenceBatchDefaults {
  start_date: string
  end_date: string
  price_per_licence_per_month: string
  billing_months: number
  total_amount: string
}

export interface OrganisationFeatureFlag {
  feature_code: string
  label: string
  is_enabled: boolean
  is_default: boolean
}

export interface OrganisationDetail {
  id: string
  name: string
  slug: string
  status: OrganisationStatus
  billing_status: OrganisationBillingStatus
  access_state: OrganisationAccessState
  onboarding_stage: OrganisationOnboardingStage
  licence_count: number
  country_code: string
  currency: string
  entity_type: OrganisationEntityType
  entity_type_label: string
  pan_number: string | null
  tan_number: string | null
  esi_branch_code: string
  address: string
  phone: string
  email: string
  logo_url: string | null
  primary_admin_email: string | null
  primary_admin: BootstrapAdminSummary | null
  bootstrap_admin: BootstrapAdminSummary | null
  paid_marked_at: string | null
  activated_at: string | null
  suspended_at: string | null
  created_by_email: string
  created_at: string
  modified_at: string
  admin_count: number
  employee_count: number
  holiday_calendar_count: number
  note_count: number
  configuration_summary: {
    locations: number
    departments: number
    leave_cycles: number
    leave_plans: number
    on_duty_policies: number
    approval_workflows: number
    notices: number
  }
  operations_guard: {
    licence_expired: boolean
    admin_mutations_blocked: boolean
    approval_actions_blocked: boolean
    seat_assignment_blocked: boolean
    reason: string
    summary: LicenceSummary
  }
  feature_flags: OrganisationFeatureFlag[]
  addresses: OrganisationAddress[]
  legal_identifiers: Array<{
    id: string
    country_code: string
    identifier_type: string
    identifier_type_label: string
    identifier: string
    is_primary: boolean
  }>
  tax_registrations: Array<{
    id: string
    country_code: string
    registration_type: string
    registration_type_label: string
    identifier: string
    state_code: string
    is_primary_billing: boolean
  }>
  state_transitions: StateTransition[]
  lifecycle_events: LifecycleEvent[]
  licence_ledger_entries: LicenceLedgerEntry[]
  licence_summary: LicenceSummary
  licence_batches: LicenceBatch[]
  batch_defaults: LicenceBatchDefaults
}

export interface OrgAdminSetupState {
  required: boolean
  started_at: string | null
  current_step: OrgAdminSetupStep
  current_step_index: number
  total_steps: number
  completed_at: string | null
  completed_by: {
    id: string
    full_name: string
    email: string
  } | null
  steps: Array<{
    key: OrgAdminSetupStep
    label: string
    is_complete: boolean
    sequence: number
  }>
}

export interface OrgAdmin {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  is_active: boolean
  is_onboarding_email_sent: boolean
  membership_status: 'INVITED' | 'ACTIVE' | 'INACTIVE' | 'REVOKED'
  invited_at: string | null
  accepted_at: string | null
  last_used_at: string | null
}

export interface CtDashboardStats {
  total_organisations: number
  active_organisations: number
  pending_organisations: number
  paid_organisations: number
  suspended_organisations: number
  total_employees: number
  total_licences: number
  allocated_licences: number
}

export interface OrgDashboardStats {
  total_employees: number
  active_employees: number
  invited_employees: number
  pending_employees: number
  resigned_employees: number
  retired_employees: number
  terminated_employees: number
  by_department: Array<{ department_name: string; count: number }>
  by_location: Array<{ location_name: string; count: number }>
  recent_joins: Array<{
    id: string
    employee_code: string | null
    designation: string
    date_of_joining: string
    user__first_name: string
    user__last_name: string
  }>
  licence_used: number
  licence_total: number
  onboarding_stage: OrganisationOnboardingStage
  pending_approvals: number
  documents_awaiting_review: number
}
