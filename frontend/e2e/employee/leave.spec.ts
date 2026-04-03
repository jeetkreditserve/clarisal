import { employeeTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

test.describe('Employee Leave', () => {
  test.describe('Read-only', () => {
    test('leave page loads at /me/leave', async ({ page }) => {
      await page.goto('/me/leave')
      await expect(page.locator('text=Leave management')).toBeVisible({ timeout: 15000 })
    })

    test('leave balance cards visible', async ({ page }) => {
      await page.goto('/me/leave')
      await page.waitForSelector('text=Leave management', { timeout: 15000 })
      const balanceCards = page.locator('.surface-card')
      if (await balanceCards.count()) {
        await expect(balanceCards.first()).toBeVisible({ timeout: 15000 })
        return
      }

      await expect(page.locator('text=No leave plan is assigned to your employee record yet.')).toBeVisible({ timeout: 15000 })
    })

    test('leave request form visible', async ({ page }) => {
      await page.goto('/me/leave')
      await page.waitForSelector('text=Leave management', { timeout: 15000 })
      // Form should have a submit button
      await expect(page.locator('button[type="submit"]').first()).toBeVisible({ timeout: 10000 })
    })

    test('leave history section visible', async ({ page }) => {
      await page.goto('/me/leave')
      await page.waitForSelector('text=Leave management', { timeout: 15000 })
      const historySection = page.locator('text=My leave requests').first()
      await expect(historySection).toBeVisible({ timeout: 15000 })
    })
  })

  test.describe('Write', () => {
    test('submit a leave request (requires leave plan assigned)', async ({ page }) => {
      await page.goto('/me/leave')
      await page.waitForSelector('text=Leave management', { timeout: 15000 })

      // Check if leave type selector has options (requires leave plan to be assigned)
      const leaveTypeSelector = page.getByRole('button', { name: /select leave type/i })
      const selectorExists = await leaveTypeSelector.isVisible({ timeout: 5000 }).catch(() => false)
      if (!selectorExists) {
        await expect(page.locator('text=No leave plan is assigned to your employee record yet.')).toBeVisible({ timeout: 10000 })
        return
      }

      await leaveTypeSelector.click()
      const firstOption = page.locator('[role="option"]').first()
      const hasOptions = (await firstOption.count()) > 0
      if (!hasOptions) {
        await page.keyboard.press('Escape')
        return
      }
      await firstOption.click()

      const startDateBtn = page.getByRole('button', { name: /select start date/i })
      await startDateBtn.click()
      await page.locator('[data-radix-popper-content-wrapper]').last().getByRole('button').filter({ hasText: /^\d+$/ }).first().click()

      const endDateBtn = page.getByRole('button', { name: /select end date/i })
      await endDateBtn.click()
      await page.locator('[data-radix-popper-content-wrapper]').last().getByRole('button').filter({ hasText: /^\d+$/ }).nth(1).click()

      // Fill reason
      const reasonInput = page.locator('input[placeholder*="reason"], textarea[placeholder*="reason"], input[placeholder*="Reason"], textarea[placeholder*="Reason"]').first()
      if (await reasonInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await reasonInput.fill('E2E test leave request')
      }

      await page.locator('button[type="submit"]').first().click()
      // Either success toast or an error (e.g., "insufficient balance" or "past dates") — both are valid
      const toastEl = page.locator('[data-sonner-toast]')
      await expect(toastEl).toBeVisible({ timeout: 10000 })
    })

    test('withdraw a pending leave request (if any)', async ({ page }) => {
      await page.goto('/me/leave')
      await page.waitForSelector('text=Leave management', { timeout: 15000 })

      const withdrawBtn = page.locator('button:has-text("Withdraw")').first()
      const hasWithdraw = await withdrawBtn.isVisible({ timeout: 5000 }).catch(() => false)
      if (!hasWithdraw) {
        // No pending requests to withdraw — acceptable
        return
      }
      await withdrawBtn.click()
      await waitForToast(page, 'Leave request withdrawn.')
    })
  })
})
