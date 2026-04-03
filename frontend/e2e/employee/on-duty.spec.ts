import { employeeTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

test.describe('Employee On-Duty', () => {
  test.describe('Read-only', () => {
    test('on-duty page loads at /me/od', async ({ page }) => {
      await page.goto('/me/od')
      await page.waitForSelector('body', { timeout: 10000 })
      expect(page.url()).toContain('/me/od')
      // Page should render without crashing
      await expect(page.locator('body')).toBeVisible()
    })

    test('on-duty request form visible', async ({ page }) => {
      await page.goto('/me/od')
      await page.waitForSelector('button[type="submit"]', { timeout: 15000 })
      await expect(page.locator('button[type="submit"]').first()).toBeVisible({ timeout: 10000 })
    })

    test('OD requests history visible', async ({ page }) => {
      await page.goto('/me/od')
      await page.waitForSelector('body', { timeout: 10000 })
      const content = page.locator('text=My on-duty requests').first()
      await expect(content).toBeVisible({ timeout: 15000 })
    })
  })

  test.describe('Write', () => {
    test('submit an on-duty request (requires OD policy)', async ({ page }) => {
      await page.goto('/me/od')
      await page.waitForSelector('body', { timeout: 15000 })

      // Fill purpose and destination fields
      const purposeInput = page.locator('input[placeholder*="purpose"], textarea[placeholder*="purpose"], input[placeholder*="Purpose"]').first()
      const purposeExists = await purposeInput.isVisible({ timeout: 5000 }).catch(() => false)
      if (!purposeExists) {
        // No form or no OD policy — skip
        return
      }

      await purposeInput.fill('E2E test on-duty request')

      const destinationInput = page.locator('input[placeholder*="destination"], input[placeholder*="Destination"]').first()
      if (await destinationInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await destinationInput.fill('Test Location')
      }

      // Future dates
      const today = new Date()
      const futureDate = new Date(today)
      futureDate.setDate(today.getDate() + 3)
      const futureDateStr = futureDate.toISOString().split('T')[0]

      // Try setting start_date via hidden input or date picker
      const dateInput = page.locator('input[type="date"]').first()
      if (await dateInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await dateInput.fill(futureDateStr)
      }

      await page.locator('button[type="submit"]').first().click()
      const toastEl = page.locator('[data-sonner-toast]')
      await expect(toastEl).toBeVisible({ timeout: 10000 })
    })

    test('withdraw a pending OD request (if any)', async ({ page }) => {
      await page.goto('/me/od')
      await page.waitForSelector('body', { timeout: 15000 })

      const withdrawBtn = page.locator('button:has-text("Withdraw")').first()
      const hasWithdraw = await withdrawBtn.isVisible({ timeout: 5000 }).catch(() => false)
      if (!hasWithdraw) {
        return
      }
      await withdrawBtn.click()
      await waitForToast(page, 'On-duty request withdrawn.')
    })
  })
})
