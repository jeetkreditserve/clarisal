import { test as base } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

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
