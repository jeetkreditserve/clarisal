import { employeeTest, orgAdminTest, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

employeeTest.describe('Employee Attendance Regularization', () => {
  employeeTest('employee can submit a regularization request', async ({ page }) => {
    await page.goto('/me/attendance')
    await expect(page.getByRole('heading', { name: 'My attendance' })).toBeVisible({ timeout: 15000 })

    const reasonField = page.locator('textarea[placeholder*="Reason"], textarea[placeholder*="reason"]').first()
    await reasonField.fill('Was present but forgot to punch.')
    await page.getByRole('button', { name: 'Submit regularization' }).click()

    await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 10000 })
  })
})

orgAdminTest.describe('Org Admin Attendance Approval Inbox', () => {
  orgAdminTest('org admin approval inbox renders for attendance-related requests', async ({ page }) => {
    await page.goto('/org/approval-workflows?tab=inbox')
    await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Approval inbox')).toBeVisible()
  })

  orgAdminTest('org admin can approve an attendance item when one is pending', async ({ page }) => {
    await page.goto('/org/approval-workflows?tab=inbox')
    await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible({ timeout: 15000 })

    const hasPendingAttendance = await page.locator('text=/attendance/i').first().isVisible({ timeout: 5000 }).catch(() => false)
    const approveButton = page.getByRole('button', { name: 'Approve' }).first()
    const hasApproveButton = await approveButton.isVisible({ timeout: 5000 }).catch(() => false)
    if (!hasPendingAttendance || !hasApproveButton) {
      return
    }

    await approveButton.click()
    await page.getByRole('button', { name: 'Approve request' }).click()
    await waitForToast(page, 'Approval recorded.')
  })
})
