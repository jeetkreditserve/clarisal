import { orgAdminTest as test, expect } from '../fixtures/auth'

test.describe('Leave Plans', () => {
  test('leave plans page loads', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await expect(page.getByRole('heading', { name: 'Leave plans' })).toBeVisible({ timeout: 10000 })
  })

  test('build new plan action is visible', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await expect(page.getByRole('button', { name: 'Build new plan' })).toBeVisible({ timeout: 10000 })
  })

  test('builder page has leave cycle selector and create action', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await page.getByRole('button', { name: 'Build new plan' }).click()
    await expect(page).toHaveURL('/org/leave-plans/new', { timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Create leave plan' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('#leave-plan-name')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Leave cycle' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create leave plan' })).toBeVisible()
  })

  test('builder shows default leave type fields', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await page.getByRole('button', { name: 'Build new plan' }).click()
    await expect(page.getByRole('heading', { name: 'Leave types' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('#leave-type-name-0')).toBeVisible()
    await expect(page.locator('#leave-type-code-0')).toBeVisible()
  })

  test('leave plans catalogue section is visible', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await expect(page.getByText('Policy catalogue')).toBeVisible({ timeout: 10000 })
  })
})
