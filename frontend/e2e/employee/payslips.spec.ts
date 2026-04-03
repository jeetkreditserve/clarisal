import { employeeTest as test, expect } from '../fixtures/auth'

test.describe('Employee Payslips Preview', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/me/payslips')
    await expect(page.getByRole('heading', { name: 'Payslips Preview' })).toBeVisible({ timeout: 15000 })
  })

  test('payslips page renders either an empty state or a slip list', async ({ page }) => {
    const emptyState = page.getByText('No payslips available yet')
    const slipList = page.getByText(/Slip number/i).first()

    const hasEmptyState = await emptyState.isVisible({ timeout: 3000 }).catch(() => false)
    if (hasEmptyState) {
      await expect(emptyState).toBeVisible()
      return
    }

    await expect(slipList).toBeVisible()
  })

  test('employee can inspect slip details when payslips exist', async ({ page }) => {
    const emptyState = page.getByText('No payslips available yet')
    if (await emptyState.isVisible({ timeout: 3000 }).catch(() => false)) {
      return
    }

    await page.locator('button[type="button"]').filter({ hasText: /\d{1,2}\/\d{4}/ }).first().click()
    await expect(page.getByText('Gross pay')).toBeVisible()
    await expect(page.getByText('Total deductions')).toBeVisible()
    await expect(page.getByText('Net pay')).toBeVisible()
  })
})
