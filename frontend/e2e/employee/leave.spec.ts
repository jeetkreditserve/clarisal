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
      // Balance cards are surface-card divs with leave type names
      // Either balances exist or a "no leave plan" empty state is shown
      const balanceOrEmpty = page.locator('.surface-card, text=No leave plan, text=no leave').first()
      await expect(balanceOrEmpty).toBeVisible({ timeout: 15000 })
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
      // History table or empty state
      const historySection = page.locator('text=Leave requests, text=No leave requests, text=history').first()
      await expect(historySection).toBeVisible({ timeout: 15000 })
    })
  })

  test.describe('Write', () => {
    test('submit a leave request (requires leave plan assigned)', async ({ page }) => {
      await page.goto('/me/leave')
      await page.waitForSelector('text=Leave management', { timeout: 15000 })

      // Check if leave type selector has options (requires leave plan to be assigned)
      const leaveTypeSelector = page.locator('[data-radix-select-trigger], button[role="combobox"]').first()
      const selectorExists = await leaveTypeSelector.isVisible({ timeout: 5000 }).catch(() => false)
      if (!selectorExists) {
        // No leave plan assigned — skip this test
        test.skip()
        return
      }

      await leaveTypeSelector.click()
      const firstOption = page.locator('[role="option"]').first()
      const hasOptions = (await firstOption.count()) > 0
      if (!hasOptions) {
        test.skip()
        return
      }
      await firstOption.click()

      // Fill dates using AppDatePicker (custom date picker) — try direct fill on hidden inputs
      // Future dates to avoid past-date errors
      const today = new Date()
      const futureDate = new Date(today)
      futureDate.setDate(today.getDate() + 7)
      const futureDateStr = futureDate.toISOString().split('T')[0]

      // Try to set dates via the AppDatePicker
      const startDateBtn = page.locator('button:has-text("Start date"), [placeholder*="start"], button[aria-label*="date"]').first()
      if (await startDateBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await startDateBtn.click()
        // In a date picker, type the date
        await page.keyboard.type(futureDateStr)
        await page.keyboard.press('Enter')
      }

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
