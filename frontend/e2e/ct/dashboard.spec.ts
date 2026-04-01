import { ctTest as test, expect } from '../../fixtures/auth'

test.describe('CT Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ct/dashboard')
    // Wait for the page heading to confirm the page has loaded
    await expect(page.locator('h1')).toContainText('Platform dashboard', { timeout: 10000 })
  })

  test('CT dashboard page loads', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Platform dashboard')
  })

  test('Total organisations metric shows 4', async ({ page }) => {
    // MetricCard renders title in a <p> and value in a sibling <p> with text-3xl
    const card = page.locator('.surface-card').filter({ hasText: 'Total organisations' })
    await expect(card).toBeVisible({ timeout: 10000 })
    // The value is the p.text-3xl inside the card
    const value = card.locator('p.text-3xl')
    await expect(value).toHaveText('4', { timeout: 10000 })
  })

  test('Active organisations metric shows 1', async ({ page }) => {
    const card = page.locator('.surface-card').filter({ hasText: 'Active organisations' })
    await expect(card).toBeVisible({ timeout: 10000 })
    const value = card.locator('p.text-3xl')
    await expect(value).toHaveText('1', { timeout: 10000 })
  })

  test('All 6 metric card titles are visible', async ({ page }) => {
    const expectedTitles = [
      'Total organisations',
      'Active organisations',
      'Pending payment',
      'Allocated licences',
      'Employees onboarded',
      'Suspended organisations',
    ]
    for (const title of expectedTitles) {
      await expect(page.locator('text=' + title).first()).toBeVisible({ timeout: 10000 })
    }
  })

  test('Recent organisations table is visible with org names', async ({ page }) => {
    // The section card with "Recent organisations" title
    await expect(page.locator('text=Recent organisations').first()).toBeVisible({ timeout: 10000 })
    // At least one known org should appear in the table
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('tbody').getByText('Acme Workforce Pvt Ltd')).toBeVisible({ timeout: 10000 })
  })

  test('Create organisation button links to /ct/organisations/new', async ({ page }) => {
    await page.click('a:has-text("Create organisation")')
    await expect(page).toHaveURL(/\/ct\/organisations\/new/, { timeout: 10000 })
  })
})
