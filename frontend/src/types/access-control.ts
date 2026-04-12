export type AccessScopeKind =
  | 'ALL_ORGANISATIONS'
  | 'SELECTED_ORGANISATIONS'
  | 'CURRENT_ORGANISATION'
  | 'ALL_EMPLOYEES'
  | 'OWN_RECORD'
  | 'REPORTING_TREE'
  | 'SELECTED_DEPARTMENTS'
  | 'SELECTED_OFFICE_LOCATIONS'
  | 'SELECTED_LEGAL_ENTITIES'
  | 'SELECTED_COST_CENTRES'
  | 'SELECTED_EMPLOYMENT_TYPES'
  | 'SELECTED_GRADES'
  | 'SELECTED_BANDS'
  | 'SELECTED_DESIGNATIONS'
  | 'SELECTED_EMPLOYEES'

export interface EffectiveScopeSummary {
  kind: AccessScopeKind
  label: string
}

export type PermissionCode = string

export interface AccessPermission {
  id: string
  code: PermissionCode
  label: string
  domain: string
  resource: string
  action: string
  description: string
}

export interface AccessRole {
  id: string
  code: string
  scope: 'CONTROL_TOWER' | 'ORGANISATION'
  name: string
  description: string
  is_system: boolean
  permissions: PermissionCode[]
}

export interface AccessScope {
  id?: string
  scope_kind: AccessScopeKind
  organisation_id?: string | null
  department_id?: string | null
  office_location_id?: string | null
  employee_id?: string | null
  value_text?: string
  label: string
}

export interface AccessRoleAssignment {
  id: string
  user_id: string
  user_email: string
  user_full_name: string
  role_code: string
  role_name: string
  is_active: boolean
  scopes: AccessScope[]
}

export interface AccessUserSummary {
  id: string
  email: string
  full_name: string
  account_type: string
}

export interface AccessControlOverview {
  roles: AccessRole[]
  permissions: AccessPermission[]
  assignments: AccessRoleAssignment[]
  users: AccessUserSummary[]
}

export interface AccessRoleWritePayload {
  name: string
  description?: string
  permission_codes: PermissionCode[]
}

export interface AccessRoleAssignmentScopePayload {
  scope_kind: AccessScopeKind
  organisation_id?: string
  department_id?: string
  office_location_id?: string
  employee_id?: string
  value_text?: string
}

export interface AccessRoleAssignmentWritePayload {
  user_id: string
  role_code: string
  is_active?: boolean
  scopes: AccessRoleAssignmentScopePayload[]
}

export interface AccessSimulationPayload {
  user_id: string
  employee_id?: string
}

export interface AccessSimulationResult {
  user_id: string
  organisation_id: string
  effective_permissions: PermissionCode[]
  effective_scopes: EffectiveScopeSummary[]
  employee_access?: {
    employee_id: string
    allowed: boolean
  } | null
}
