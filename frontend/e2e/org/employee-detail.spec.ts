import { orgAdminTest as test, expect } from '../fixtures/auth'

test.describe('Org Admin — Employee Detail', () => {
  // Navigate to Priya Sharma's detail page before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/employees')
    await expect(page.getByRole('heading', { name: 'Employees' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })

    // Search for Priya Sharma
    const searchInput = page.locator('input[placeholder="Search employees by name or email"]')
    await searchInput.fill('Priya')
    await page.waitForTimeout(600)

    // Click the Open link on Priya's row
    const priyaRow = page.locator('tbody tr').filter({ hasText: 'Priya Sharma' })
    await priyaRow.getByRole('link', { name: 'Open' }).click()
    await expect(page).toHaveURL(/\/org\/employees\/[^/]+$/, { timeout: 8000 })
    await expect(page.getByText('Employee detail')).toBeVisible({ timeout: 10000 })
  })

  test('navigate to employee detail for Priya Sharma', async ({ page }) => {
    await expect(page).toHaveURL(/\/org\/employees\/[^/]+$/)
    await expect(page.getByText('Employee detail')).toBeVisible()
  })

  test('employee name and email are displayed', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Priya Sharma' })).toBeVisible()
    await expect(page.getByText('priya.sharma@acmeworkforce.com')).toBeVisible()
  })

  test('employee status badge is visible', async ({ page }) => {
    // Status badge appears in the actions area of PageHeader
    const statusBadge = page.locator('span, div').filter({ hasText: /^(ACTIVE|INVITED|PENDING|RESIGNED|TERMINATED|RETIRED)$/ })
    await expect(statusBadge.first()).toBeVisible({ timeout: 8000 })
  })

  test('employment settings section is visible', async ({ page }) => {
    await expect(page.getByText('Employment settings')).toBeVisible()
    // The form has a designation input and employment type select
    await expect(page.locator('input[placeholder="Designation"]')).toBeVisible()
  })

  test('save employee changes button is visible', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Save employee changes' })).toBeVisible()
  })

  test('employment info visible — employment type select and date field', async ({ page }) => {
    await expect(page.getByText('Employment settings')).toBeVisible()
    await expect(page.getByRole('button', { name: /Full Time|Part Time|Contract|Intern/i }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Select joining date|\d{2} \w{3} \d{4}/ }).first()).toBeVisible()
  })

  test('back to employees link visible', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Back to employees' })).toBeVisible()
  })
})
