import { employeeTest as test, expect } from '../fixtures/auth'

test.describe('Employee Dashboard', () => {
  test('dashboard page loads at /me/dashboard', async ({ page }) => {
    await page.goto('/me/dashboard')
    await expect(page.locator('text=My dashboard')).toBeVisible({ timeout: 15000 })
  })

  test('quick actions section visible', async ({ page }) => {
    await page.goto('/me/dashboard')
    await page.waitForSelector('text=My dashboard', { timeout: 15000 })
    await expect(page.locator('text=Quick actions')).toBeVisible({ timeout: 10000 })
  })

  test('request leave and submit on-duty quick action buttons visible', async ({ page }) => {
    await page.goto('/me/dashboard')
    await page.waitForSelector('text=Quick actions', { timeout: 15000 })
    await expect(page.locator('a:has-text("Request leave")').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('a:has-text("Submit on-duty")').first()).toBeVisible({ timeout: 10000 })
  })

  test('navigation sidebar shows employee menu items', async ({ page }) => {
    await page.goto('/me/dashboard')
    await page.waitForSelector('text=My dashboard', { timeout: 15000 })
    // Sidebar should have links to Leave, On-duty, Profile, etc.
    await expect(page.locator('nav a[href="/me/leave"], nav a[href*="leave"]').first()).toBeVisible({ timeout: 10000 })
  })

  test('continue onboarding button links to /me/onboarding', async ({ page }) => {
    await page.goto('/me/dashboard')
    await page.waitForSelector('text=My dashboard', { timeout: 15000 })
    const onboardingLink = page.getByRole('link', { name: 'Continue onboarding' }).first()
    await expect(onboardingLink).toBeVisible({ timeout: 10000 })
    await expect(onboardingLink).toHaveAttribute('href', '/me/onboarding')
  })

  test('month calendar widget renders', async ({ page }) => {
    await page.goto('/me/dashboard')
    await page.waitForSelector('text=My dashboard', { timeout: 15000 })
    const calendar = page.getByText('Month calendar').first()
    await expect(calendar).toBeVisible({ timeout: 15000 })
  })
})
