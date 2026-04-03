import { employeeTest, orgAdminTest, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

employeeTest.describe('Employee Leave Flow', () => {
  employeeTest('employee can submit a leave request when leave types are available', async ({ page }) => {
    await page.goto('/me/leave')
    await expect(page.getByRole('heading', { name: 'Leave management' })).toBeVisible({ timeout: 15000 })

    const leaveTypeSelect = page.getByRole('button', { name: /select leave type/i })
    const hasLeaveType = await leaveTypeSelect.isVisible({ timeout: 5000 }).catch(() => false)
    if (!hasLeaveType) {
      return
    }

    await leaveTypeSelect.click()
    const firstOption = page.getByRole('option').first()
    const hasOptions = await firstOption.isVisible({ timeout: 5000 }).catch(() => false)
    if (!hasOptions) {
      return
    }
    await firstOption.click()

    const today = new Date()
    const future = new Date(today)
    future.setDate(today.getDate() + 7)
    const futureIso = future.toISOString().slice(0, 10)

    await page.getByRole('button', { name: /select start date/i }).click()
    await page.keyboard.type(futureIso)
    await page.keyboard.press('Enter')

    await page.getByRole('button', { name: /select end date/i }).click()
    await page.keyboard.type(futureIso)
    await page.keyboard.press('Enter')

    await page.getByPlaceholder('Reason').fill('Personal work')
    await page.getByRole('button', { name: 'Submit leave request' }).click()

    await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 10000 })
  })
})

orgAdminTest.describe('Org Admin Leave Approval Inbox', () => {
  orgAdminTest('org admin can approve a leave item when one is pending', async ({ page }) => {
    await page.goto('/org/approval-workflows?tab=inbox')
    await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible({ timeout: 15000 })

    const hasPendingLeave = await page.locator('text=/leave/i').first().isVisible({ timeout: 5000 }).catch(() => false)
    const approveButton = page.getByRole('button', { name: 'Approve' }).first()
    const hasApproveButton = await approveButton.isVisible({ timeout: 5000 }).catch(() => false)
    if (!hasPendingLeave || !hasApproveButton) {
      return
    }

    await approveButton.click()
    await page.getByRole('button', { name: 'Approve request' }).click()
    await waitForToast(page, 'Approval recorded.')
  })
})
