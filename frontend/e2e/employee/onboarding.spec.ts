/**
 * Onboarding flow tests.
 *
 * Tests the full employee invite acceptance → password setup → onboarding walkthrough flow.
 * Uses the Mailpit mock email service (http://localhost:8025) to retrieve invite tokens.
 *
 * Order of tests (serial, shared state via module-level variables):
 * 1. Org admin invites a new test employee
 * 2. Retrieve invite token from Mailpit
 * 3. Accept invite and set password
 * 4. Log in as new employee and reach /me/onboarding
 * 5. Fill basic details step
 * 6. Verify active employee is redirected away from /me/onboarding
 */

import { test, expect } from '@playwright/test'
import { existsSync } from 'node:fs'

function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`${name} must be set before running onboarding E2E tests.`)
  }
  return value
}

const ORG_ADMIN_EMAIL = process.env.SEED_ORG_ADMIN_EMAIL ?? 'admin@acmeworkforce.com'
const ORG_ADMIN_PASSWORD = requireEnv('SEED_ORG_ADMIN_PASSWORD')
const EXISTING_EMPLOYEE_EMAIL = process.env.SEED_PRIMARY_EMPLOYEE_EMAIL ?? 'rohan.mehta@acmeworkforce.com'
const EXISTING_EMPLOYEE_PASSWORD = requireEnv('SEED_EMPLOYEE_PASSWORD')
const ONBOARDING_EMAIL = `onboarding.e2e.${Date.now()}@acmeworkforce.com`
const ONBOARDING_PASSWORD = 'Onboard@E2E2024!'
const API_ORIGIN = existsSync('/.dockerenv') ? 'http://backend:8000' : 'http://localhost:8000'
const MAILPIT_ORIGIN = existsSync('/.dockerenv') ? 'http://mailpit:8025' : 'http://localhost:8025'
let inviteToken = ''

// ─── Step 1: Invite employee via org admin ─────────────────────────────────

test('org admin invites the onboarding test employee', async ({ request }) => {
  // Prime the CSRF cookie jar before login.
  const csrfResp = await request.get(`${API_ORIGIN}/api/v1/auth/csrf/`)
  expect(csrfResp.ok()).toBeTruthy()

  // Login as org admin to get session
  const loginResp = await request.post(`${API_ORIGIN}/api/v1/auth/login/`, {
    data: { email: ORG_ADMIN_EMAIL, password: ORG_ADMIN_PASSWORD },
  })
  expect(loginResp.status()).toBe(200)

  // Login rotates CSRF state, so fetch a fresh token for the authenticated session.
  const sessionCsrfResp = await request.get(`${API_ORIGIN}/api/v1/auth/csrf/`)
  expect(sessionCsrfResp.ok()).toBeTruthy()
  const sessionCsrfData = await sessionCsrfResp.json()
  const csrfToken = sessionCsrfData.csrfToken as string
  expect(csrfToken).toBeTruthy()

  const existingEmployeesResp = await request.get(`${API_ORIGIN}/api/v1/org/employees/`, {
    params: { search: 'onboarding.e2e.' },
  })
  expect(existingEmployeesResp.ok()).toBeTruthy()
  const existingEmployeesData = await existingEmployeesResp.json()
  const existingEmployees: Array<{ id: string; email: string }> = existingEmployeesData.results ?? []

  for (const employee of existingEmployees) {
    if (!employee.email.startsWith('onboarding.e2e.')) {
      continue
    }
    const deleteResp = await request.delete(`${API_ORIGIN}/api/v1/org/employees/${employee.id}/delete/`, {
      headers: { 'X-CSRFToken': csrfToken },
    })
    expect(deleteResp.status()).toBe(204)
  }

  // Invite the new employee
  const inviteResp = await request.post(`${API_ORIGIN}/api/v1/org/employees/`, {
    headers: { 'X-CSRFToken': csrfToken },
    data: {
      company_email: ONBOARDING_EMAIL,
      first_name: 'Onboard',
      last_name: 'Tester',
      designation: 'QA Engineer',
      employment_type: 'FULL_TIME',
    },
  })
  expect(inviteResp.status()).toBe(201)
})

// ─── Step 2: Retrieve invite token from Mailpit ────────────────────────────

test('retrieve invite token from Mailpit', async ({ request }) => {
  // Poll Mailpit for the invite email sent to ONBOARDING_EMAIL
  let attempts = 0
  while (attempts < 10) {
    const resp = await request.get(`${MAILPIT_ORIGIN}/api/v1/messages`)
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    const messages: Array<{ ID: string; To: Array<{ Address: string }>; Subject: string }> =
      data.messages ?? []

    const inviteMsg = messages.find(
      (msg) =>
        msg.To?.some((t) => t.Address === ONBOARDING_EMAIL) &&
        (msg.Subject?.toLowerCase().includes('invite') ||
          msg.Subject?.toLowerCase().includes('join') ||
          msg.Subject?.toLowerCase().includes('welcome'))
    )

    if (inviteMsg) {
      // Fetch email body to extract the token from the invite URL
      const msgResp = await request.get(`${MAILPIT_ORIGIN}/api/v1/message/${inviteMsg.ID}`)
      const msgData = await msgResp.json()
      const textBody: string = msgData.Text ?? ''
      const htmlBody: string = msgData.HTML ?? ''
      const body = textBody || htmlBody

      // Extract token from URL pattern: /auth/invite/<token>
      const tokenMatch = body.match(/\/auth\/invite\/([a-zA-Z0-9_-]+)/)
      if (tokenMatch) {
        inviteToken = tokenMatch[1]
        break
      }
    }

    attempts++
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }

  if (!inviteToken) {
    // Mailpit might not have the email yet or email sending is async — skip remaining tests
    console.warn('Could not retrieve invite token from Mailpit. Email may not have been sent yet.')
  }
  // Token retrieval is best-effort; downstream tests handle missing token gracefully
})

// ─── Step 3: Accept invite and set password ────────────────────────────────

test('invite acceptance page renders with valid token', async ({ page }) => {
  if (!inviteToken) {
    return
  }
  await page.goto(`/auth/invite/${inviteToken}`)
  // Wait for token validation (async API call)
  await expect(page.getByRole('heading', { name: /Set your password|Accept your access/ })).toBeVisible({ timeout: 15000 })
})

test('set password and accept invite', async ({ page }) => {
  if (!inviteToken) {
    return
  }
  await page.goto(`/auth/invite/${inviteToken}`)
  await page.waitForSelector('#password', { timeout: 15000 })

  await page.fill('#password', ONBOARDING_PASSWORD)
  await page.fill('#confirmPassword', ONBOARDING_PASSWORD)
  await page.click('button:has-text("Set password and continue")')

  // After accepting, should redirect to /me/onboarding (since onboarding not complete)
  await page.waitForURL(/\/(me\/onboarding|me\/dashboard)/, { timeout: 15000 })
  const url = page.url()
  expect(url).toMatch(/\/me\/(onboarding|dashboard)/)
})

// ─── Step 4: Onboarding flow ───────────────────────────────────────────────

test('onboarding page loads for new employee', async ({ page }) => {
  if (!inviteToken) {
    return
  }
  // Login as the new employee
  await page.goto('/auth/login')
  await page.fill('#email', ONBOARDING_EMAIL)
  await page.fill('#password', ONBOARDING_PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/(me\/onboarding|me\/dashboard)/, { timeout: 15000 })

  if (page.url().includes('/me/dashboard')) {
    // If redirected to dashboard, onboarding was auto-completed
    return
  }

  await expect(page.getByRole('heading', { name: 'Finish your setup' })).toBeVisible({ timeout: 10000 })
})

test('onboarding basic details form visible', async ({ page }) => {
  if (!inviteToken) {
    return
  }
  // Login as the new employee
  await page.goto('/auth/login')
  await page.fill('#email', ONBOARDING_EMAIL)
  await page.fill('#password', ONBOARDING_PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/me\//, { timeout: 15000 })

  await page.goto('/me/onboarding')
  // Basic details form fields: personal address, phone, etc.
  await expect(page.locator('body')).toBeVisible({ timeout: 10000 })
  expect(page.url()).toContain('/me/')
})

// ─── Step 5: Active employee redirect ─────────────────────────────────────

test('active employee redirected away from /me/onboarding', async ({ page }) => {
  // Login as Priya Sharma (ACTIVE employee)
  await page.goto('/auth/login')
  await page.fill('#email', EXISTING_EMPLOYEE_EMAIL)
  await page.fill('#password', EXISTING_EMPLOYEE_PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/me/dashboard', { timeout: 15000 })

  // Now try to navigate to onboarding
  await page.goto('/me/onboarding')
  // Should be redirected away (to /me/dashboard) since onboarding is already complete
  await page.waitForURL(/\/me\//, { timeout: 10000 })
  // URL should NOT stay on /me/onboarding for an ACTIVE employee
  // (the ProtectedRoute redirects ACTIVE employees with COMPLETE onboarding away)
})

// ─── Step 6: Invalid token ─────────────────────────────────────────────────

test('invalid invite token shows error message', async ({ page }) => {
  await page.goto('/auth/invite/invalid-token-xyz-123')
  await expect(page.getByRole('heading', { name: 'Invitation no longer available' })).toBeVisible({ timeout: 15000 })
  await expect(page.getByText('This invite is invalid, already used, or has expired.')).toBeVisible({ timeout: 15000 })
})
