import { orgAdminTest as test, expect } from '../fixtures/auth'

test.describe('Org Admin — Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/dashboard')
    await expect(page.getByRole('heading', { name: 'People operations dashboard' })).toBeVisible({ timeout: 10000 })
  })

  test('dashboard page loads at /org/dashboard with heading visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'People operations dashboard' })).toBeVisible()
    await expect(page.getByText('Organisation workspace')).toBeVisible()
  })

  test('employee count metric card is visible', async ({ page }) => {
    await expect(page.getByText('Total employees', { exact: true })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Active employees', { exact: true })).toBeVisible({ timeout: 10000 })
  })

  test('pending approvals section is visible', async ({ page }) => {
    await expect(page.getByText('Approvals and document review')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Documents awaiting review')).toBeVisible({ timeout: 10000 })
  })

  test('notices section is visible via nav or content', async ({ page }) => {
    // The sidebar has a Notices link
    await expect(page.getByRole('link', { name: 'Notices' })).toBeVisible()
  })

  test('navigation sidebar shows org admin menu items', async ({ page }) => {
    const nav = page.getByRole('navigation')
    await expect(nav.getByRole('link', { name: 'Dashboard' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Employees' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Departments' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Locations' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Holidays' })).toBeVisible()
  })

  test('workspace header shows organisation context badges', async ({ page }) => {
    await expect(page.getByText('Organisation workspace')).toBeVisible()
    await expect(page.getByText('Attendance live')).toBeVisible()
  })
})
