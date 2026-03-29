export type OrganisationStatus = 'PENDING' | 'PAID' | 'ACTIVE' | 'SUSPENDED'

export interface OrganisationListItem {
  id: string
  name: string
  slug: string
  status: OrganisationStatus
  licence_count: number
  created_at: string
}

export interface StateTransition {
  id: string
  from_status: OrganisationStatus
  to_status: OrganisationStatus
  note: string
  transitioned_by_email: string
  created_at: string
}

export interface Organisation {
  id: string
  name: string
  slug: string
  status: OrganisationStatus
  licence_count: number
  address: string
  phone: string
  email: string
  logo_url: string | null
  created_by_email: string
  created_at: string
  updated_at: string
  state_transitions: StateTransition[]
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
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
