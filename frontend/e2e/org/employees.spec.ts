import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast } from '../helpers'

// Shared email for invite + duplicate tests
let invitedEmail = ''

test.describe('Org Admin — Employees (read-only)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/employees')
    await expect(page.getByRole('heading', { name: 'Employees' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
  })

  test('employee list loads at /org/employees — shows 10+ employees', async ({ page }) => {
    await expect(page.getByText('Employee directory')).toBeVisible()
    const rows = page.locator('tbody tr')
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(10)
  })

  test('filter by status works — select ACTIVE, table updates', async ({ page }) => {
    await page.getByRole('button', { name: 'All statuses' }).click()
    await page.getByRole('button', { name: 'Active' }).click()
    await expect(page.getByRole('button', { name: 'Active' })).toBeVisible({ timeout: 8000 })
    await expect(page.locator('tbody')).toContainText('ACTIVE')
  })

  test('search by name "Priya" finds Priya Sharma', async ({ page }) => {
    const searchInput = page.locator('input[placeholder="Search employees by name or email"]')
    await searchInput.fill('Priya')
    await page.waitForTimeout(600)
    await expect(page.locator('tbody tr').filter({ hasText: 'Priya Sharma' })).toBeVisible({ timeout: 8000 })
  })

  test('employee status badges are visible in the table', async ({ page }) => {
    // At least one status badge should be visible in the rows
    const badge = page.locator('tbody tr').first().locator('[class*="badge"], [class*="Badge"], span').filter({ hasText: /ACTIVE|INVITED|PENDING/ })
    await expect(badge.first()).toBeVisible({ timeout: 8000 })
  })

  test('click employee row Open link navigates to detail page', async ({ page }) => {
    // Find Priya Sharma row and click Open
    const searchInput = page.locator('input[placeholder="Search employees by name or email"]')
    await searchInput.fill('Priya')
    await page.waitForTimeout(600)
    const priyaRow = page.locator('tbody tr').filter({ hasText: 'Priya Sharma' })
    await priyaRow.getByRole('link', { name: 'Open' }).click()
    await expect(page).toHaveURL(/\/org\/employees\/[^/]+$/, { timeout: 8000 })
    await expect(page.getByText('Priya Sharma')).toBeVisible({ timeout: 8000 })
  })

  test('invite employee button is visible', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Invite employee' })).toBeVisible()
  })

  test('invite form opens when button is clicked', async ({ page }) => {
    await page.getByRole('button', { name: 'Invite employee' }).click()
    await expect(page.getByText('Invite employee', { exact: false }).nth(1)).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#first_name')).toBeVisible()
    await expect(page.locator('#company_email')).toBeVisible()
  })
})

test.describe('Org Admin — Employees (invite modal)', () => {
  test('invite modal includes core employee fields', async ({ page }) => {
    await page.goto('/org/employees')
    await expect(page.getByRole('heading', { name: 'Employees' })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: 'Invite employee' }).click()
    await expect(page.locator('#first_name')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#last_name')).toBeVisible()
    await expect(page.locator('#company_email')).toBeVisible()
    await expect(page.locator('#designation')).toBeVisible()
  })

  test('invite modal shows document request options', async ({ page }) => {
    await page.goto('/org/employees')
    await expect(page.getByRole('heading', { name: 'Employees' })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: 'Invite employee' }).click()
    await expect(page.getByText('Requested onboarding documents')).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('checkbox', { name: /Address Proof/i })).toBeVisible()
  })
})
