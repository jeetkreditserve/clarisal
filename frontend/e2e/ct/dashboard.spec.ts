import { ctTest as test, expect } from '../fixtures/auth'

test.describe('CT Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ct/dashboard')
    await expect(page.getByRole('heading', { name: 'Platform dashboard' })).toBeVisible({ timeout: 10000 })
  })

  test('CT dashboard page loads', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Platform dashboard' })).toBeVisible()
  })

  test('Total organisations metric shows a numeric value', async ({ page }) => {
    const card = page.locator('.surface-card').filter({ hasText: 'Total organisations' })
    await expect(card).toBeVisible({ timeout: 10000 })
    const value = card.locator('p.text-3xl')
    await expect(value).toHaveText(/\d+/, { timeout: 10000 })
  })

  test('Active organisations metric shows a numeric value', async ({ page }) => {
    const card = page.locator('.surface-card').filter({ hasText: 'Active organisations' })
    await expect(card).toBeVisible({ timeout: 10000 })
    const value = card.locator('p.text-3xl')
    await expect(value).toHaveText(/\d+/, { timeout: 10000 })
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
    await expect(page.locator('text=Recent organisations').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('tbody a[href^="/ct/organisations/"]').first()).toBeVisible({ timeout: 10000 })
  })

  test('Create organisation button links to /ct/organisations/new', async ({ page }) => {
    await page.getByRole('link', { name: 'Create organisation' }).first().click()
    await expect(page).toHaveURL(/\/ct\/organisations\/new/, { timeout: 10000 })
  })
})
