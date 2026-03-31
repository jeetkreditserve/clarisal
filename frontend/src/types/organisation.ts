export type OrganisationStatus = 'PENDING' | 'PAID' | 'ACTIVE' | 'SUSPENDED'
export type OrganisationBillingStatus = 'PENDING_PAYMENT' | 'PAID'
export type OrganisationAccessState = 'PROVISIONING' | 'ACTIVE' | 'SUSPENDED'
export type OrganisationAddressType =
  | 'REGISTERED'
  | 'BILLING'
  | 'HEADQUARTERS'
  | 'WAREHOUSE'
  | 'CUSTOM'
export type LicenceBatchPaymentStatus = 'DRAFT' | 'PAID'
export type LicenceBatchLifecycleState = 'DRAFT' | 'PAID_PENDING_START' | 'ACTIVE' | 'EXPIRED'
export type OrganisationOnboardingStage =
  | 'ORG_CREATED'
  | 'LICENCES_ASSIGNED'
  | 'PAYMENT_CONFIRMED'
  | 'ADMIN_INVITED'
  | 'ADMIN_ACTIVATED'
  | 'MASTER_DATA_CONFIGURED'
  | 'EMPLOYEES_INVITED'

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
  country: string
  pincode: string
  gstin: string | null
  is_active: boolean
  created_at: string
  updated_at: string
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
  created_by_email: string | null
  paid_by_email: string | null
  paid_at: string | null
  created_at: string
  updated_at: string
}

export interface LicenceBatchDefaults {
  start_date: string
  end_date: string
  price_per_licence_per_month: string
  billing_months: number
  total_amount: string
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
  pan_number: string | null
  address: string
  phone: string
  email: string
  logo_url: string | null
  primary_admin_email: string | null
  paid_marked_at: string | null
  activated_at: string | null
  suspended_at: string | null
  created_by_email: string
  created_at: string
  updated_at: string
  addresses: OrganisationAddress[]
  state_transitions: StateTransition[]
  lifecycle_events: LifecycleEvent[]
  licence_ledger_entries: LicenceLedgerEntry[]
  licence_summary: LicenceSummary
  licence_batches: LicenceBatch[]
  batch_defaults: LicenceBatchDefaults
}

export interface OrgAdmin {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  is_active: boolean
  is_onboarding_email_sent: boolean
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
}
