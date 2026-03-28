export type UserRole = 'CONTROL_TOWER' | 'ORG_ADMIN' | 'EMPLOYEE'

export interface AuthUser {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: UserRole
  org_id: string | null
  is_active: boolean
}

export interface LoginResponse {
  access: string
  refresh: string
  user: Omit<AuthUser, 'full_name' | 'is_active'>
}

export interface ApiError {
  error?: string
  detail?: string
  [key: string]: unknown
}
