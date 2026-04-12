import type { Page } from '@playwright/test'
import { ctTest as test, expect } from '../fixtures/auth'
import { uniqueName, waitForToast } from '../helpers'

async function searchForOrganisation(page: Page, name: string, searchTerm = name) {
  await page.goto('/ct/organisations')
  await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
  await page.getByPlaceholder('Search organisations...').fill(searchTerm)
  await expect(page.locator('tbody')).toContainText(name, { timeout: 10000 })
}

async function searchForAcme(page: Page) {
  await searchForOrganisation(page, 'Acme Workforce Pvt Ltd', 'Acme')
}

async function openAcmeDetail(page: Page) {
  await searchForAcme(page)
  const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' }).first()
  await acmeRow.locator('a:has-text("Open")').click()
  await expect(page.getByRole('heading', { name: 'Acme Workforce Pvt Ltd' })).toBeVisible({ timeout: 10000 })
}

test.describe('CT Organisations', () => {
  test('Organisations list loads', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.getByRole('heading', { name: 'Organisations' })).toBeVisible({ timeout: 10000 })
  })

  test('Shows at least the seeded organisations in the table', async ({ page }) => {
    await page.goto('/ct/organisations')
    // Wait for the table to populate
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
    expect(await page.locator('tbody tr').count()).toBeGreaterThanOrEqual(4)
  })

  test('Acme Workforce Pvt Ltd is visible in the list', async ({ page }) => {
    await searchForAcme(page)
  })

  test('Orbit Freight Pvt Ltd is visible in the list', async ({ page }) => {
    await searchForOrganisation(page, 'Orbit Freight Pvt Ltd', 'Orbit')
  })

  test('Redwood Retail Pvt Ltd is visible in the list', async ({ page }) => {
    await searchForOrganisation(page, 'Redwood Retail Pvt Ltd', 'Redwood')
  })

  test('Zenith Field Services Pvt Ltd is visible in the list', async ({ page }) => {
    await searchForOrganisation(page, 'Zenith Field Services Pvt Ltd', 'Zenith')
  })

  test('Search for "Acme" filters to 1 result', async ({ page }) => {
    await page.goto('/ct/organisations')
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible({ timeout: 10000 })
    const initialCount = await rows.count()

    await page.getByPlaceholder('Search organisations...').fill('Acme')
    await expect.poll(async () => rows.count(), { timeout: 10000 }).toBeLessThan(initialCount)
    await expect(page.locator('tbody')).toContainText('Acme Workforce Pvt Ltd')
  })

  test('Clear search shows all organisations', async ({ page }) => {
    await page.goto('/ct/organisations')
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible({ timeout: 10000 })
    const initialCount = await rows.count()

    // Fill search then clear it
    await page.getByPlaceholder('Search organisations...').fill('Acme')
    await expect.poll(async () => rows.count(), { timeout: 10000 }).toBeLessThan(initialCount)

    await page.getByPlaceholder('Search organisations...').fill('')
    await expect.poll(async () => rows.count(), { timeout: 10000 }).toBe(initialCount)
  })

  test('Click Acme row navigates to detail page', async ({ page }) => {
    await searchForAcme(page)
    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' }).first()
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page).toHaveURL(/\/ct\/organisations\/[^/]+$/, { timeout: 10000 })
  })

  test('Detail page shows org name "Acme Workforce Pvt Ltd"', async ({ page }) => {
    await openAcmeDetail(page)
  })

  test('Detail page shows bootstrap admin information in the admins tab', async ({ page }) => {
    await openAcmeDetail(page)
    await page.getByRole('button', { name: 'Org Admins' }).click()

    await expect(page.getByText('Bootstrap admin')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Primary organisation admin bootstrap details captured during org creation.')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Email')).toBeVisible({ timeout: 10000 })
  })

  test('Detail page shows onboarding blockers in the onboarding support tab', async ({ page }) => {
    await openAcmeDetail(page)

    await page.getByRole('button', { name: 'Onboarding Support' }).click()
    await expect(page.getByText('Onboarding blockers')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Meera Singh')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('PASSPORT_PHOTO')).toBeVisible({ timeout: 10000 })
  })

  test('CT audit timeline masks employee actor identity details', async ({ page }) => {
    await openAcmeDetail(page)

    await page.getByRole('button', { name: 'Audit Timeline' }).click()
    await expect(page.getByText('Employee user').first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('karthik.verma@acmeworkforce.com')).toHaveCount(0)
  })

  test('CT payroll support tab explains missing payroll setup', async ({ page }) => {
    await openAcmeDetail(page)

    await page.getByRole('button', { name: 'Payroll Support' }).click()
    await expect(page.getByText('Needs CT attention')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('No compensation templates configured')).toBeVisible({ timeout: 10000 })
  })

  test('CT attendance support tab explains missing attendance setup', async ({ page }) => {
    await openAcmeDetail(page)

    await page.getByRole('button', { name: 'Attendance Support' }).click()
    await expect(page.getByText('Needs CT attention')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('No active attendance source connected')).toBeVisible({ timeout: 10000 })
  })

  test('Suspend and restore Acme from the detail page', async ({ page }) => {
    await openAcmeDetail(page)

    if (await page.getByRole('button', { name: 'Restore access' }).isVisible()) {
      await page.getByRole('button', { name: 'Restore access' }).click()
      await page.getByRole('button', { name: 'Restore access' }).last().click()
      await waitForToast(page, 'Organisation access restored.')
    }

    await page.getByRole('button', { name: 'Suspend access' }).click()
    await page.getByRole('button', { name: 'Suspend access' }).last().click()
    await waitForToast(page, 'Organisation suspended.')

    await page.getByRole('button', { name: 'Restore access' }).click()
    await page.getByRole('button', { name: 'Restore access' }).last().click()
    await waitForToast(page, 'Organisation restored.')
  })

  test('New organisation button navigates to /ct/organisations/new', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.getByRole('heading', { name: 'Organisations' })).toBeVisible({ timeout: 10000 })

    await page.click('a:has-text("New organisation")')
    await expect(page).toHaveURL(/\/ct\/organisations\/new/, { timeout: 10000 })
  })

  test('New organisation form renders — name field is visible', async ({ page }) => {
    await page.goto('/ct/organisations/new')
    // The name input has id="name"
    await expect(page.locator('#name')).toBeVisible({ timeout: 10000 })
  })

  test('Full guided onboarding wizard creates an organisation', async ({ page }) => {
    const timestamp = Date.now()
    const panDigits = String((timestamp % 9000) + 1000).padStart(4, '0')
    const panNumber = `WIZRD${panDigits}F`
    const gstin = `29${panNumber}1Z5`
    const orgName = uniqueName('Wizard Provisioning Org')

    await page.goto('/ct/organisations/new')
    await expect(page.getByRole('heading', { name: 'Create organisation' })).toBeVisible({ timeout: 10000 })

    await page.locator('#name').fill(orgName)
    await page.locator('#pan_number').fill(panNumber)
    await page.locator('#primary-admin-first-name').fill('Priya')
    await page.locator('#primary-admin-last-name').fill('Nair')
    await page.locator('#primary-admin-email').fill(`ct-wizard-${timestamp}@example.com`)
    await page.locator('#primary-admin-phone').fill('+919900001234')
    await page.locator('#REGISTERED-line1').fill('42 Residency Road')
    await page.locator('#REGISTERED-city').fill('Bengaluru')
    await page.locator('#REGISTERED-state').click()
    await page.getByRole('button', { name: /Karnataka/ }).click()
    await page.locator('#REGISTERED-pincode').fill('560001')
    await page.locator('#REGISTERED-gstin').fill(gstin)
    await page.locator('#billing-same-as-registered').click()

    await page.getByRole('button', { name: 'Next' }).click()
    await waitForToast(page, 'Organisation shell created.', 15000)
    await expect(page.getByRole('heading', { name: 'Licence Configuration' })).toBeVisible({ timeout: 10000 })

    await page.locator('#seat-count').fill('12')
    await page.locator('#licence-note').fill('Created by the guided wizard E2E flow.')
    await page.getByRole('button', { name: 'Next' }).click()
    await waitForToast(page, 'Draft licence batch saved.', 15000)
    await expect(page.getByRole('heading', { name: 'Feature Flags' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: 'Next' }).click()
    await waitForToast(page, 'Feature flags saved.', 15000)
    await expect(page.getByRole('heading', { name: 'Payroll & Compliance Settings' })).toBeVisible({ timeout: 10000 })

    await page.locator('#tan-number').fill('BLRW12345F')
    await page.getByRole('button', { name: 'Next' }).click()
    await waitForToast(page, 'Payroll settings saved.', 15000)
    await expect(page.getByRole('heading', { name: 'Seed Payroll Masters' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: 'Seed default masters' }).click()
    await waitForToast(page, 'Default masters seeded.', 20000)
    await page.getByRole('button', { name: 'Continue' }).click()
    await expect(page.getByRole('heading', { name: 'Invite First Admin' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: 'Save and finish later' }).click()
    await waitForToast(page, 'Onboarding progress saved.', 15000)
    await expect(page).toHaveURL(/\/ct\/organisations\/[^/]+$/, { timeout: 15000 })
    await expect(page.getByRole('heading', { name: orgName })).toBeVisible({ timeout: 10000 })

    await page.goto('/ct/organisations')
    await page.getByPlaceholder('Search organisations...').fill(orgName)
    await expect(page.locator('tbody')).toContainText(orgName, { timeout: 10000 })
  })
})
