import { ctTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

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
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody')).toContainText('Acme Workforce Pvt Ltd', { timeout: 10000 })
  })

  test('Orbit Freight Pvt Ltd is visible in the list', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody')).toContainText('Orbit Freight Pvt Ltd', { timeout: 10000 })
  })

  test('Redwood Retail Pvt Ltd is visible in the list', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody')).toContainText('Redwood Retail Pvt Ltd', { timeout: 10000 })
  })

  test('Zenith Field Services Pvt Ltd is visible in the list', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody')).toContainText('Zenith Field Services Pvt Ltd', { timeout: 10000 })
  })

  test('Search for "Acme" filters to 1 result', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    await page.fill('input.field-input.pl-11', 'Acme')
    // Search may be debounced — wait for the table to update
    await page.waitForTimeout(600)
    await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 10000 })
    await expect(page.locator('tbody')).toContainText('Acme Workforce Pvt Ltd')
  })

  test('Clear search shows all organisations', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
    const initialCount = await page.locator('tbody tr').count()

    // Fill search then clear it
    await page.fill('input.field-input.pl-11', 'Acme')
    await page.waitForTimeout(600)
    await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 10000 })

    await page.fill('input.field-input.pl-11', '')
    await page.waitForTimeout(600)
    await expect(page.locator('tbody tr')).toHaveCount(initialCount, { timeout: 10000 })
  })

  test('Click Acme row navigates to detail page', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    // Click the "Open" action link for the Acme row
    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' })
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page).toHaveURL(/\/ct\/organisations\/[^/]+$/, { timeout: 10000 })
  })

  test('Detail page shows org name "Acme Workforce Pvt Ltd"', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' })
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page.getByRole('heading', { name: 'Acme Workforce Pvt Ltd' })).toBeVisible({ timeout: 10000 })
  })

  test('Detail page shows bootstrap admin information in the admins tab', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' })
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page.getByRole('heading', { name: 'Acme Workforce Pvt Ltd' })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: 'Org Admins' }).click()

    await expect(page.getByText('Bootstrap admin')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Primary organisation admin bootstrap details captured during org creation.')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Email')).toBeVisible({ timeout: 10000 })
  })

  test('Suspend and restore Acme from the detail page', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' })
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page.getByRole('heading', { name: 'Acme Workforce Pvt Ltd' })).toBeVisible({ timeout: 10000 })

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
})
