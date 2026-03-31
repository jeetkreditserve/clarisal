import type { AuthUser, UserRole } from '@/types/auth'

export function isControlTower(user: Pick<AuthUser, 'account_type'> | undefined): boolean {
  return user?.account_type === 'CONTROL_TOWER'
}

export function isOrgAdmin(user: Pick<AuthUser, 'has_org_admin_access'> | undefined): boolean {
  return Boolean(user?.has_org_admin_access)
}

export function isEmployee(user: Pick<AuthUser, 'has_employee_access'> | undefined): boolean {
  return Boolean(user?.has_employee_access)
}

export function getDefaultRoute(target: AuthUser | UserRole | undefined): string {
  if (!target) return '/auth/login'

  if (typeof target !== 'string') {
    return target.default_route || '/auth/login'
  }

  switch (target) {
    case 'CONTROL_TOWER':
      return '/ct/dashboard'
    case 'ORG_ADMIN':
      return '/org/dashboard'
    case 'EMPLOYEE':
      return '/me/dashboard'
    default:
      return '/auth/login'
  }
}
