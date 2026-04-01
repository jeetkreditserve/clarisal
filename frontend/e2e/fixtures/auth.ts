import { test as base, expect } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const CT_AUTH = path.join(__dirname, '../../.auth/ct.json')
const ORG_ADMIN_AUTH = path.join(__dirname, '../../.auth/org-admin.json')
const EMPLOYEE_AUTH = path.join(__dirname, '../../.auth/employee.json')

export const ctTest = base.extend({
  storageState: async (_context, applyStorageState) => {
    await applyStorageState(CT_AUTH)
  },
})

export const orgAdminTest = base.extend({
  storageState: async (_context, applyStorageState) => {
    await applyStorageState(ORG_ADMIN_AUTH)
  },
})

export const employeeTest = base.extend({
  storageState: async (_context, applyStorageState) => {
    await applyStorageState(EMPLOYEE_AUTH)
  },
})

export { expect }
