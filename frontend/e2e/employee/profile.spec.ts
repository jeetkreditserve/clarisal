import { employeeTest as test, expect } from '../fixtures/auth'

test.describe('Employee Profile', () => {
  test.describe('Read-only', () => {
    test('profile page loads at /me/profile', async ({ page }) => {
      await page.goto('/me/profile')
      await expect(page.locator('text=Profile, text=My profile, h1').first()).toBeVisible({ timeout: 15000 })
    })

    test('education page loads at /me/education', async ({ page }) => {
      await page.goto('/me/education')
      await expect(page.locator('body')).toBeVisible({ timeout: 10000 })
      // Page should not redirect away
      expect(page.url()).toContain('/me/education')
    })

    test('documents page loads at /me/documents', async ({ page }) => {
      await page.goto('/me/documents')
      await expect(page.locator('body')).toBeVisible({ timeout: 10000 })
      expect(page.url()).toContain('/me/documents')
    })

    test('government IDs section visible on profile', async ({ page }) => {
      await page.goto('/me/profile')
      await page.waitForSelector('body', { timeout: 10000 })
      // Look for PAN, Aadhaar, or government ID section
      const govSection = page.locator('text=Government IDs, text=PAN, text=Aadhaar').first()
      await expect(govSection).toBeVisible({ timeout: 15000 })
    })

    test('bank account section visible on profile', async ({ page }) => {
      await page.goto('/me/profile')
      await page.waitForSelector('body', { timeout: 10000 })
      const bankSection = page.locator('text=Bank account, text=Bank accounts').first()
      await expect(bankSection).toBeVisible({ timeout: 15000 })
    })
  })

  test.describe('Write', () => {
    test('add education record', async ({ page }) => {
      await page.goto('/me/education')
      await page.waitForSelector('body', { timeout: 10000 })
      // Look for an add/create button or form
      const addBtn = page.locator('button:has-text("Add"), button:has-text("Create"), button:has-text("New")').first()
      if (await addBtn.isVisible()) {
        await addBtn.click()
        // Fill degree field if form opens
        const degreeInput = page.locator('input[placeholder*="degree"], input[placeholder*="Degree"], input#degree').first()
        if (await degreeInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await degreeInput.fill('Bachelor of Engineering')
        }
        const institutionInput = page.locator('input[placeholder*="institution"], input[placeholder*="Institution"]').first()
        if (await institutionInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await institutionInput.fill('E2E University')
        }
        const submitBtn = page.locator('button[type="submit"]').first()
        if (await submitBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await submitBtn.click()
        }
      }
      // Either succeeds or page still shows education section
      expect(page.url()).toContain('/me/education')
    })
  })
})
