import type { Page } from '@playwright/test'
import { expect, orgAdminTest as test } from '../fixtures/auth'
import { uniqueName, waitForToast } from '../helpers'

function requireEnv(name: string) {
  const value = process.env[name]
  if (!value) {
    throw new Error(`${name} must be set before running the asset E2E.`)
  }
  return value
}

const ACME_EMPLOYEE_EMAIL = process.env.SEED_SECONDARY_EMPLOYEE_EMAIL ?? 'priya.sharma@acmeworkforce.com'
const EMPLOYEE_PASSWORD = requireEnv('SEED_EMPLOYEE_PASSWORD')
const ORG_ADMIN_EMAIL = process.env.SEED_ORG_ADMIN_EMAIL ?? 'admin@acmeworkforce.com'
const ORG_ADMIN_PASSWORD = requireEnv('SEED_ORG_ADMIN_PASSWORD')

async function findOptionValue(page: Page, selector: string, labelPart: string) {
  return page.locator(`${selector} option`).evaluateAll((options, expectedLabel) => {
    const match = options.find((option) => option.textContent?.includes(expectedLabel as string))
    return match ? (match as HTMLOptionElement).value : null
  }, labelPart)
}

async function waitForOptionValue(page: Page, selector: string, labelPart: string) {
  let value: string | null = null
  await expect
    .poll(async () => {
      value = await findOptionValue(page, selector, labelPart)
      return value
    }, { timeout: 15000 })
    .not.toBeNull()
  return value
}

test.describe('Org Admin — Assets', () => {
  test('issues, acknowledges, and returns an asset during offboarding', async ({ page, browser }) => {
    const assetName = uniqueName('QA Asset')
    const assetTag = `LAP-${Date.now()}`
    const serialNumber = `SN-${Date.now()}`

    await page.goto('/auth/login')
    await page.fill('#email', ORG_ADMIN_EMAIL)
    await page.fill('#password', ORG_ADMIN_PASSWORD)
    await page.click('button[type="submit"]')
    await page.waitForURL('/org/dashboard', { timeout: 15000 })

    const employeeContext = await browser.newContext()
    const employeePage = await employeeContext.newPage()

    await employeePage.goto('/auth/login')
    await employeePage.fill('#email', ACME_EMPLOYEE_EMAIL)
    await employeePage.fill('#password', EMPLOYEE_PASSWORD)
    await employeePage.click('button[type="submit"]')
    await employeePage.waitForURL('/me/dashboard', { timeout: 15000 })

    const employeeProfileResponse = await employeeContext.request.get('/api/v1/me/profile/')
    expect(employeeProfileResponse.ok()).toBeTruthy()
    const employeeProfile = await employeeProfileResponse.json()
    const employeeId = employeeProfile.employee.id as string

    await page.goto('/org/assets')
    await expect(page.getByRole('heading', { name: 'Asset inventory' })).toBeVisible({ timeout: 15000 })

    await page.locator('#asset-name').fill(assetName)
    await page.locator('#asset-tag').fill(assetTag)
    await page.locator('#asset-serial-number').fill(serialNumber)
    await page.locator('#asset-vendor').fill('QA Vendor')
    await page.getByRole('button', { name: 'Add asset' }).click()

    await waitForToast(page, 'Asset added to inventory.')

    await page.goto('/org/assets/assignments')
    await expect(page.getByRole('heading', { name: 'Asset assignments' })).toBeVisible({ timeout: 15000 })

    const assetId = await waitForOptionValue(page, '#assignment-asset', assetName)
    await page.locator('#assignment-asset').selectOption(assetId!)

    await expect
      .poll(async () => page.locator(`#assignment-employee option[value="${employeeId}"]`).count(), { timeout: 15000 })
      .toBeGreaterThan(0)
    await page.locator('#assignment-employee').selectOption(employeeId)
    await page.locator('#assignment-expected-return').fill('2026-12-31')
    await page.locator('#assignment-notes').fill('Return to IT on exit or role change.')
    await page.getByRole('button', { name: 'Assign asset' }).click()

    await waitForToast(page, 'Asset assigned to employee.')

    await employeePage.goto('/me/assets')
    await expect(employeePage.getByRole('heading', { name: 'My assets' })).toBeVisible({ timeout: 15000 })
    await expect(employeePage.getByText(assetName)).toBeVisible({ timeout: 15000 })
    await employeePage.getByRole('button', { name: 'Acknowledge receipt' }).click()
    await employeePage.getByRole('button', { name: 'Confirm acknowledgement' }).click()
    await waitForToast(employeePage, 'Asset acknowledgement recorded.')
    await employeeContext.close()

    await page.goto(`/org/employees/${employeeId}`)
    await expect(page.getByRole('heading', { name: employeeProfile.employee.full_name })).toBeVisible({ timeout: 15000 })

    const csrfResponse = await page.request.get('/api/v1/auth/csrf/')
    expect(csrfResponse.ok()).toBeTruthy()

    const csrfCookie = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')
    expect(csrfCookie?.value).toBeTruthy()

    const endEmploymentResponse = await page.request.post(`/api/v1/org/employees/${employeeId}/end-employment/`, {
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfCookie!.value,
      },
      data: {
        status: 'RESIGNED',
        date_of_exit: '2026-12-31',
        exit_reason: 'Asset recovery flow',
        exit_notes: 'Triggered by Playwright assets journey.',
      },
    })

    expect(endEmploymentResponse.status()).toBe(200)
    await page.reload()

    await expect(page.getByText('Pending asset recovery')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText(assetName)).toBeVisible({ timeout: 15000 })
    await page.getByRole('link', { name: 'Open asset assignments' }).click()
    await expect(page).toHaveURL(new RegExp(`/org/assets/assignments\\?employee=${employeeId}`), { timeout: 15000 })

    const assignmentCard = page.locator('div.rounded-\\[24px\\]').filter({ hasText: assetName }).first()
    await expect(assignmentCard).toBeVisible({ timeout: 15000 })
    await assignmentCard.getByRole('button', { name: 'Return asset' }).click()
    await page.getByRole('button', { name: 'Confirm return' }).click()
    await waitForToast(page, 'Asset return recorded.')
    await expect(assignmentCard).not.toBeVisible({ timeout: 15000 })
  })
})
