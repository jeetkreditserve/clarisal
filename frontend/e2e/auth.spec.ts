import { test, expect } from '@playwright/test'

function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`${name} must be set before running auth E2E tests.`)
  }
  return value
}

const controlTowerEmail = process.env.CONTROL_TOWER_EMAIL ?? 'admin@clarisal.com'
const controlTowerPassword = requireEnv('CONTROL_TOWER_PASSWORD')
const orgAdminEmail = process.env.SEED_ORG_ADMIN_EMAIL ?? 'admin@acmeworkforce.com'
const orgAdminPassword = requireEnv('SEED_ORG_ADMIN_PASSWORD')
const employeeEmail = process.env.SEED_PRIMARY_EMPLOYEE_EMAIL ?? 'rohan.mehta@acmeworkforce.com'
const employeePassword = requireEnv('SEED_EMPLOYEE_PASSWORD')

test.describe('Authentication', () => {
  test('/ redirects to /auth/login', async ({ page }) => {
    await page.goto('/')
    await page.waitForURL('**/auth/login')
    expect(page.url()).toContain('/auth/login')
  })

  test.describe('CT login', () => {
    test('CT login with valid credentials → /ct/dashboard', async ({ page }) => {
      await page.goto('/ct/login')
      await page.fill('#ct-email', controlTowerEmail)
      await page.fill('#ct-password', controlTowerPassword)
      await page.click('button[type="submit"]')
      await page.waitForURL('**/ct/dashboard', { timeout: 15000 })
      expect(page.url()).toContain('/ct/dashboard')
    })

    test('CT login with wrong password shows error', async ({ page }) => {
      await page.goto('/ct/login')
      await page.fill('#ct-email', controlTowerEmail)
      await page.fill('#ct-password', 'wrongpassword')
      await page.click('button[type="submit"]')
      await expect(page.locator('.notice-error')).toBeVisible({ timeout: 10000 })
    })

    test('CT login with empty form shows browser validation', async ({ page }) => {
      await page.goto('/ct/login')
      await page.click('button[type="submit"]')
      // HTML5 required attribute prevents navigation; URL should remain on /ct/login
      expect(page.url()).toContain('/ct/login')
      await expect(page.locator('.notice-error')).not.toBeVisible()
    })

    test('CT password reset page renders with email field', async ({ page }) => {
      await page.goto('/ct/reset-password')
      await expect(page.locator('input[type="email"], input#email')).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('Workforce login', () => {
    test('Workforce login as org admin → /org/dashboard', async ({ page }) => {
      await page.goto('/auth/login')
      await page.fill('#email', orgAdminEmail)
      await page.fill('#password', orgAdminPassword)
      await page.click('button[type="submit"]')
      await page.waitForURL('**/org/dashboard', { timeout: 15000 })
      expect(page.url()).toContain('/org/dashboard')
    })

    test('Workforce login as employee → /me/dashboard', async ({ page }) => {
      await page.goto('/auth/login')
      await page.fill('#email', employeeEmail)
      await page.fill('#password', employeePassword)
      await page.click('button[type="submit"]')
      await page.waitForURL('**/me/dashboard', { timeout: 15000 })
      expect(page.url()).toContain('/me/dashboard')
    })

    test('Workforce login with wrong password shows error', async ({ page }) => {
      await page.goto('/auth/login')
      await page.fill('#email', orgAdminEmail)
      await page.fill('#password', 'wrongpassword')
      await page.click('button[type="submit"]')
      await expect(page.locator('.notice-error')).toBeVisible({ timeout: 10000 })
    })

    test('Workforce password reset page renders with email field', async ({ page }) => {
      await page.goto('/auth/reset-password')
      await expect(page.locator('input[type="email"], input#email')).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('Protected route redirects', () => {
    test('Accessing /ct/dashboard without auth redirects to /ct/login', async ({ page }) => {
      await page.goto('/ct/dashboard')
      await page.waitForURL('**/ct/login', { timeout: 10000 })
      expect(page.url()).toContain('/ct/login')
    })

    test('Accessing /org/dashboard without auth redirects to /auth/login', async ({ page }) => {
      await page.goto('/org/dashboard')
      await page.waitForURL('**/auth/login', { timeout: 10000 })
      expect(page.url()).toContain('/auth/login')
    })

    test('Accessing /me/dashboard without auth redirects to /auth/login', async ({ page }) => {
      await page.goto('/me/dashboard')
      await page.waitForURL('**/auth/login', { timeout: 10000 })
      expect(page.url()).toContain('/auth/login')
    })
  })
})
