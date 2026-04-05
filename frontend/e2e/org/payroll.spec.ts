import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

function uniquePeriodYear() {
  return String(2030 + new Date().getFullYear() % 50)
}

test.describe('Org Admin — Payroll Preview', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/payroll')
    await expect(page.getByRole('heading', { name: 'Payroll control room' })).toBeVisible({ timeout: 15000 })
  })

  test('creates a payroll run from the runs section', async ({ page }) => {
    await page.getByRole('button', { name: 'Runs' }).click()
    await page.getByPlaceholder('Year').fill(uniquePeriodYear())
    await page.getByPlaceholder('Month').fill('4')
    await page.getByRole('button', { name: 'Create payroll run' }).click()

    await waitForToast(page, 'Payroll run created.')
  })

  test('can trigger calculation when a runnable payroll row is available', async ({ page }) => {
    await page.getByRole('button', { name: 'Runs' }).click()

    const calculateButton = page.getByRole('button', { name: /calculate|recalculate/i }).first()
    const hasCalculate = await calculateButton.isVisible({ timeout: 5000 }).catch(() => false)
    if (!hasCalculate) {
      return
    }

    await calculateButton.click()
    await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 15000 })
  })
})
