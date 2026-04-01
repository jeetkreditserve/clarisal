import { test as base } from '@playwright/test'
import path from 'path'

export const ctTest = base.extend<object>({
  storageState: path.join(__dirname, '../../.auth/ct.json'),
})

export const orgAdminTest = base.extend<object>({
  storageState: path.join(__dirname, '../../.auth/org-admin.json'),
})

export const employeeTest = base.extend<object>({
  storageState: path.join(__dirname, '../../.auth/employee.json'),
})

export { expect } from '@playwright/test'
