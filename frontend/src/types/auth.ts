import type {
  LicenceSummary,
  OrganisationAccessState,
  OrganisationOnboardingStage,
  OrganisationStatus,
} from '@/types/organisation'
import type { EmployeeOnboardingStatus, EmployeeStatus } from '@/types/hr'

export type AccountType = 'CONTROL_TOWER' | 'WORKFORCE'
export type UserRole = 'CONTROL_TOWER' | 'ORG_ADMIN' | 'EMPLOYEE'
export type WorkspaceKind = 'CONTROL_TOWER' | 'ADMIN' | 'EMPLOYEE'

export interface AdminOrganisationSummary {
  organisation_id: string
  organisation_name: string
  status: OrganisationStatus
  access_state: OrganisationAccessState
  onboarding_stage: OrganisationOnboardingStage
  is_active_context: boolean
}

export interface EmployeeWorkspaceSummary {
  employee_id: string
  employee_code: string
  organisation_id: string
  organisation_name: string
  employee_status: EmployeeStatus
  onboarding_status: EmployeeOnboardingStatus
  is_active_context: boolean
}

export interface OrgOperationsGuard {
  licence_expired: boolean
  admin_mutations_blocked: boolean
  approval_actions_blocked: boolean
  seat_assignment_blocked: boolean
  reason: string
  summary: LicenceSummary
}

export interface AuthUser {
  id: string
  email: string
  account_type: AccountType
  first_name: string
  last_name: string
  full_name: string
  role: UserRole
  organisation_id: string | null
  organisation_name?: string | null
  organisation_status?: OrganisationStatus | null
  organisation_onboarding_stage?: OrganisationOnboardingStage | null
  organisation_access_state?: OrganisationAccessState | null
  active_workspace_kind?: WorkspaceKind | null
  default_route: string
  has_control_tower_access: boolean
  has_org_admin_access: boolean
  has_employee_access: boolean
  admin_organisations: AdminOrganisationSummary[]
  employee_workspaces: EmployeeWorkspaceSummary[]
  active_employee_status?: EmployeeStatus | null
  active_employee_onboarding_status?: EmployeeOnboardingStatus | null
  org_operations_guard?: OrgOperationsGuard | null
  is_active: boolean
}

export interface LoginResponse {
  user: AuthUser
}

export interface ApiError {
  error?: string
  detail?: string
  [key: string]: unknown
}
