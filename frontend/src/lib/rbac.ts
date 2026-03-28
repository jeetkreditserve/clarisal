import type { UserRole } from '@/types/auth'

export function isControlTower(role: UserRole | undefined): boolean {
  return role === 'CONTROL_TOWER'
}

export function isOrgAdmin(role: UserRole | undefined): boolean {
  return role === 'ORG_ADMIN'
}

export function isEmployee(role: UserRole | undefined): boolean {
  return role === 'EMPLOYEE'
}

export function isOrgAdminOrAbove(role: UserRole | undefined): boolean {
  return role === 'CONTROL_TOWER' || role === 'ORG_ADMIN'
}

export function getDefaultRoute(role: UserRole | undefined): string {
  switch (role) {
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
