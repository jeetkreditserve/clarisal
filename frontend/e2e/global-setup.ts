import { test as setup, type Page } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'
import fs from 'fs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const AUTH_DIR = path.join(__dirname, '../.auth')
const CT_AUTH_FILE = path.join(AUTH_DIR, 'ct.json')
const ORG_ADMIN_AUTH_FILE = path.join(AUTH_DIR, 'org-admin.json')
const EMPLOYEE_AUTH_FILE = path.join(AUTH_DIR, 'employee.json')

function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`${name} must be set before running Playwright global setup.`)
  }
  return value
}

const controlTowerEmail = process.env.CONTROL_TOWER_EMAIL ?? 'admin@clarisal.com'
const controlTowerPassword = requireEnv('CONTROL_TOWER_PASSWORD')
const orgAdminEmail = process.env.SEED_ORG_ADMIN_EMAIL ?? 'admin@acmeworkforce.com'
const orgAdminPassword = requireEnv('SEED_ORG_ADMIN_PASSWORD')
const employeeEmail = process.env.SEED_PRIMARY_EMPLOYEE_EMAIL ?? 'rohan.mehta@acmeworkforce.com'
const employeePassword = requireEnv('SEED_EMPLOYEE_PASSWORD')

// Ensure the .auth directory exists before saving storage state
fs.mkdirSync(AUTH_DIR, { recursive: true })

async function saveAuthenticatedState(page: Page, pathToState: string, label: string) {
  const cookies = await page.context().cookies()
  if (!cookies.some((cookie) => cookie.name === 'clarisal_sessionid')) {
    throw new Error(`${label} login did not persist a Clarisal session cookie. Check local cookie-domain configuration.`)
  }
  await page.context().storageState({ path: pathToState })
}

setup('authenticate as CT', async ({ page }) => {
  await page.goto('/ct/login')
  await page.fill('#ct-email', controlTowerEmail)
  await page.fill('#ct-password', controlTowerPassword)
  await page.click('button[type="submit"]')
  await page.waitForURL('/ct/dashboard', { timeout: 15000 })
  await saveAuthenticatedState(page, CT_AUTH_FILE, 'CT')
})

setup('authenticate as Org Admin', async ({ page }) => {
  await page.goto('/auth/login')
  await page.fill('#email', orgAdminEmail)
  await page.fill('#password', orgAdminPassword)
  await page.click('button[type="submit"]')
  await page.waitForURL('/org/dashboard', { timeout: 15000 })
  await saveAuthenticatedState(page, ORG_ADMIN_AUTH_FILE, 'Org Admin')
})

setup('authenticate as Employee', async ({ page }) => {
  await page.goto('/auth/login')
  await page.fill('#email', employeeEmail)
  await page.fill('#password', employeePassword)
  await page.click('button[type="submit"]')
  await page.waitForURL('/me/dashboard', { timeout: 15000 })
  await saveAuthenticatedState(page, EMPLOYEE_AUTH_FILE, 'Employee')
})
