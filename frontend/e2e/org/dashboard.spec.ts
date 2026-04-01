import { orgAdminTest as test, expect } from '../fixtures/auth'

test.describe('Org Admin — Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/dashboard')
    // Wait for the page to finish loading
    await expect(page.getByText('People operations dashboard')).toBeVisible({ timeout: 10000 })
  })

  test('dashboard page loads at /org/dashboard with heading visible', async ({ page }) => {
    await expect(page.getByText('People operations dashboard')).toBeVisible()
    await expect(page.getByText('Organisation')).toBeVisible()
  })

  test('employee count metric card is visible', async ({ page }) => {
    await expect(page.getByText('Total employees')).toBeVisible()
    await expect(page.getByText('Active employees')).toBeVisible()
  })

  test('pending approvals section is visible', async ({ page }) => {
    await expect(page.getByText('Approvals and document review')).toBeVisible()
    await expect(page.getByText('Pending approvals')).first().toBeVisible()
  })

  test('notices section is visible via nav or content', async ({ page }) => {
    // The sidebar has a Notices link
    await expect(page.getByRole('link', { name: 'Notices' })).toBeVisible()
  })

  test('navigation sidebar shows org admin menu items', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Employees' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Departments' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Locations' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Organisation' })).toBeVisible()
  })

  test('org name is visible in the layout header', async ({ page }) => {
    // The topbar shows the organisation name from user.organisation_name
    await expect(page.getByText('Acme Workforce Pvt Ltd')).toBeVisible({ timeout: 10000 })
  })
})
