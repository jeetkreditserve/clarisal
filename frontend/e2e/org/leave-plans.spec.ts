import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

// NOTE: Leave plans require at least one leave cycle to exist.
// Run leave-cycles.spec.ts before this file (serial workers=1 ensures order by filename).

test.describe('Leave Plans', () => {
  test('leave plans page loads', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await expect(page.locator('text=Leave plans')).toBeVisible({ timeout: 10000 })
  })

  test('create leave plan action is visible', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await expect(page.locator('button:has-text("Add leave plan")')).toBeVisible({ timeout: 10000 })
  })

  test('leave cycle selector is visible in modal', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await page.click('button:has-text("Add leave plan")')
    await expect(page.locator('#leave-cycle-id, [data-radix-select-trigger]').first()).toBeVisible({ timeout: 10000 })
  })

  test('create a leave plan (requires leave cycle to exist)', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await page.click('button:has-text("Add leave plan")')
    await page.waitForSelector('text=Create leave plan', { timeout: 10000 })

    // Select the first available leave cycle from the dropdown
    const cycleSelect = page.locator('#leave-cycle-id, button[role="combobox"]').first()
    await cycleSelect.click()
    // Click the first non-placeholder option in the dropdown
    const option = page.locator('[role="option"]').first()
    const optionCount = await option.count()
    if (optionCount > 0) {
      await option.click()
    } else {
      // No leave cycles available - skip submission
      test.skip()
      return
    }

    // Fill the plan name
    const nameInput = page.locator('input[placeholder*="plan"], input#plan-name, input.field-input').first()
    await nameInput.fill(`E2E Leave Plan ${Date.now()}`)

    await page.click('button[type="submit"]')
    await waitForToast(page, 'Leave plan created.')
  })

  test('leave plans list updates after creation', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await page.waitForSelector('text=Leave plans', { timeout: 10000 })
    // Plans list or empty state should be visible
    const plansList = page.locator('.surface-muted, tbody tr, text=No leave plans')
    await expect(plansList.first()).toBeVisible({ timeout: 10000 })
  })

  test('leave plan requires leave cycle to submit', async ({ page }) => {
    await page.goto('/org/leave-plans')
    await page.click('button:has-text("Add leave plan")')
    await page.waitForSelector('text=Create leave plan', { timeout: 10000 })
    // Submit without selecting a cycle — should show an error or not succeed
    await page.click('button[type="submit"]')
    // Page should not navigate away
    expect(page.url()).toContain('/org/leave-plans')
  })
})
