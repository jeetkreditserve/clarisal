import { test as setup } from '@playwright/test'
import path from 'path'
import fs from 'fs'

const AUTH_DIR = path.join(__dirname, '../.auth')
const CT_AUTH_FILE = path.join(AUTH_DIR, 'ct.json')
const ORG_ADMIN_AUTH_FILE = path.join(AUTH_DIR, 'org-admin.json')
const EMPLOYEE_AUTH_FILE = path.join(AUTH_DIR, 'employee.json')

// Ensure the .auth directory exists before saving storage state
fs.mkdirSync(AUTH_DIR, { recursive: true })

setup('authenticate as CT', async ({ page }) => {
  await page.goto('/ct/login')
  await page.fill('#ct-email', 'admin@clarisal.com')
  await page.fill('#ct-password', 'ClarisalAdmin@2024!')
  await page.click('button[type="submit"]')
  await page.waitForURL('/ct/dashboard', { timeout: 15000 })
  await page.context().storageState({ path: CT_AUTH_FILE })
})

setup('authenticate as Org Admin', async ({ page }) => {
  await page.goto('/auth/login')
  await page.fill('#email', 'admin@acmeworkforce.com')
  await page.fill('#password', 'Admin@12345')
  await page.click('button[type="submit"]')
  await page.waitForURL('/org/dashboard', { timeout: 15000 })
  await page.context().storageState({ path: ORG_ADMIN_AUTH_FILE })
})

setup('authenticate as Employee', async ({ page }) => {
  await page.goto('/auth/login')
  await page.fill('#email', 'priya.sharma@acmeworkforce.com')
  await page.fill('#password', 'Employee@12345')
  await page.click('button[type="submit"]')
  await page.waitForURL('/me/dashboard', { timeout: 15000 })
  await page.context().storageState({ path: EMPLOYEE_AUTH_FILE })
})
