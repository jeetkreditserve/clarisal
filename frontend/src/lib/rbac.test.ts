import { describe, expect, it } from 'vitest'

import { canAccessScope, canManageAccessControl, hasAnyPermission, hasPermission } from '@/lib/rbac'

const baseUser = {
  effective_permissions: ['org.reports.read', 'org.access_control.manage'],
  effective_scopes: [{ kind: 'ALL_EMPLOYEES' as const, label: 'All employees' }],
}

describe('rbac helpers', () => {
  it('checks whether a permission exists on the user payload', () => {
    expect(hasPermission(baseUser, 'org.reports.read')).toBe(true)
    expect(hasPermission(baseUser, 'org.payroll.read')).toBe(false)
  })

  it('accepts any matching permission from a set', () => {
    expect(hasAnyPermission(baseUser, ['org.payroll.read', 'org.reports.read'])).toBe(true)
    expect(hasAnyPermission(baseUser, ['org.payroll.read', 'org.audit.read'])).toBe(false)
  })

  it('detects scoped access summaries', () => {
    expect(canAccessScope(baseUser, 'ALL_EMPLOYEES')).toBe(true)
    expect(canAccessScope(baseUser, 'SELECTED_OFFICE_LOCATIONS')).toBe(false)
  })

  it('flags users who can manage access control', () => {
    expect(canManageAccessControl(baseUser)).toBe(true)
    expect(
      canManageAccessControl({
        effective_permissions: ['ct.organisations.write'],
      }),
    ).toBe(true)
  })
})
