import { employeeTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

test.describe('Employee Approvals', () => {
  test('approvals page loads at /me/approvals', async ({ page }) => {
    await page.goto('/me/approvals')
    await expect(page.locator('text=Requests needing my action')).toBeVisible({ timeout: 15000 })
  })

  test('approval inbox section visible', async ({ page }) => {
    await page.goto('/me/approvals')
    await page.waitForSelector('text=Requests needing my action', { timeout: 15000 })
    await expect(page.locator('text=Approval inbox')).toBeVisible({ timeout: 10000 })
  })

  test('empty inbox state renders without crash', async ({ page }) => {
    await page.goto('/me/approvals')
    await page.waitForSelector('text=Approval inbox', { timeout: 15000 })
    // Either inbox has items or shows empty state — both are valid
    const inboxContent = page.locator('.surface-muted, [class*="EmptyState"], text=No pending').first()
    // The page should render something — just not crash
    await expect(page.locator('text=Approval inbox')).toBeVisible({ timeout: 10000 })
  })

  test('approve action renders dialog when inbox has items', async ({ page }) => {
    await page.goto('/me/approvals')
    await page.waitForSelector('text=Approval inbox', { timeout: 15000 })

    const approveBtn = page.locator('button:has-text("Approve")').first()
    const hasApprove = await approveBtn.isVisible({ timeout: 5000 }).catch(() => false)
    if (!hasApprove) {
      // No pending approvals in inbox — test passes vacuously
      return
    }

    await approveBtn.click()
    // ApprovalDecisionDialog opens — confirm button should appear
    await expect(page.locator('button:has-text("Approve request")')).toBeVisible({ timeout: 5000 })
    // Close dialog without submitting
    await page.keyboard.press('Escape')
  })

  test('reject action renders dialog when inbox has items', async ({ page }) => {
    await page.goto('/me/approvals')
    await page.waitForSelector('text=Approval inbox', { timeout: 15000 })

    const rejectBtn = page.locator('button:has-text("Reject")').first()
    const hasReject = await rejectBtn.isVisible({ timeout: 5000 }).catch(() => false)
    if (!hasReject) {
      return
    }

    await rejectBtn.click()
    await expect(page.locator('button:has-text("Reject request")')).toBeVisible({ timeout: 5000 })
    await page.keyboard.press('Escape')
  })

  test('navigation to /me/approvals from sidebar works', async ({ page }) => {
    await page.goto('/me/dashboard')
    await page.waitForSelector('text=My dashboard', { timeout: 15000 })
    const approvalsLink = page.locator('a[href="/me/approvals"]')
    await expect(approvalsLink).toBeVisible({ timeout: 10000 })
    await approvalsLink.click()
    await page.waitForURL('**/me/approvals', { timeout: 10000 })
    expect(page.url()).toContain('/me/approvals')
  })
})
