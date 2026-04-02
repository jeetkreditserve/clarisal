import { ctTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

test.describe('CT Organisations', () => {
  test('Organisations list loads', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.getByRole('heading', { name: 'Organisations' })).toBeVisible({ timeout: 10000 })
  })

  test('Shows 4 organisations in the table', async ({ page }) => {
    await page.goto('/ct/organisations')
    // Wait for the table to populate
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('tbody tr')).toHaveCount(4, { timeout: 10000 })
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

    // Fill search then clear it
    await page.fill('input.field-input.pl-11', 'Acme')
    await page.waitForTimeout(600)
    await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 10000 })

    await page.fill('input.field-input.pl-11', '')
    await page.waitForTimeout(600)
    await expect(page.locator('tbody tr')).toHaveCount(4, { timeout: 10000 })
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

  test('Detail page shows org admin Aditi Rao in admins section', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' })
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page.getByRole('heading', { name: 'Acme Workforce Pvt Ltd' })).toBeVisible({ timeout: 10000 })

    // The admins table should list Aditi Rao
    await expect(page.locator('text=Aditi Rao').first()).toBeVisible({ timeout: 10000 })
  })

  test('Suspend Acme — confirm dialog then toast confirms suspension', async ({ page }) => {
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' })
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page.getByRole('heading', { name: 'Acme Workforce Pvt Ltd' })).toBeVisible({ timeout: 10000 })

    // Set up dialog acceptance BEFORE clicking the button
    page.once('dialog', (dialog) => dialog.accept())
    await page.click('button:has-text("Suspend access")')

    await waitForToast(page, 'Organisation suspended.')
  })

  test('Restore Acme after suspension — toast confirms restoration', async ({ page }) => {
    // Acme must already be suspended from the previous test (serial execution, workers=1)
    await page.goto('/ct/organisations')
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    const acmeRow = page.locator('tbody tr').filter({ hasText: 'Acme Workforce Pvt Ltd' })
    await acmeRow.locator('a:has-text("Open")').click()
    await expect(page.getByRole('heading', { name: 'Acme Workforce Pvt Ltd' })).toBeVisible({ timeout: 10000 })

    await page.click('button:has-text("Restore access")')
    await waitForToast(page, 'Organisation access restored.')
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
