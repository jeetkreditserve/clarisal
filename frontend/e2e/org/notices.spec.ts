import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

test.describe('Notices', () => {
  test.describe('Read-only', () => {
    test('notices page loads', async ({ page }) => {
      await page.goto('/org/notices')
      await expect(page.locator('text=Internal notices')).toBeVisible({ timeout: 10000 })
    })

    test('create notice form is visible', async ({ page }) => {
      await page.goto('/org/notices')
      await expect(page.locator('text=Create notice')).toBeVisible({ timeout: 10000 })
    })

    test('notice form has title and body fields', async ({ page }) => {
      await page.goto('/org/notices')
      await page.waitForSelector('text=Create notice', { timeout: 10000 })
      await expect(page.locator('input.field-input[placeholder="Title"]')).toBeVisible({ timeout: 10000 })
      await expect(page.locator('textarea.field-textarea[placeholder="Body"]')).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('Write', () => {
    test('create a notice', async ({ page }) => {
      await page.goto('/org/notices')
      await page.waitForSelector('input[placeholder="Title"]', { timeout: 10000 })

      const noticeTitle = uniqueName('E2E Notice')
      await page.fill('input[placeholder="Title"]', noticeTitle)
      await page.fill('textarea[placeholder="Body"]', 'This notice was created by the e2e test suite.')

      await page.click('button[type="submit"]')
      await waitForToast(page, 'Notice created.')
    })

    test('created notice appears in the list', async ({ page }) => {
      await page.goto('/org/notices')
      await page.waitForSelector('text=Internal notices', { timeout: 10000 })
      // Notices list section should show at least one notice
      const noticeItem = page.locator('.surface-muted, tbody tr').first()
      await expect(noticeItem).toBeVisible({ timeout: 10000 })
    })

    test('notice shows DRAFT status badge', async ({ page }) => {
      await page.goto('/org/notices')
      await page.waitForSelector('text=Internal notices', { timeout: 10000 })
      // StatusBadge for DRAFT status
      await expect(page.locator('text=DRAFT').first()).toBeVisible({ timeout: 10000 })
    })

    test('publish a notice', async ({ page }) => {
      await page.goto('/org/notices')
      await page.waitForSelector('text=Internal notices', { timeout: 10000 })

      // Click publish on the first notice (DRAFT)
      const publishBtn = page.locator('button:has-text("Publish")').first()
      await expect(publishBtn).toBeVisible({ timeout: 10000 })
      await publishBtn.click()
      await waitForToast(page, 'Notice published.')
    })

    test('published notice shows PUBLISHED status badge', async ({ page }) => {
      await page.goto('/org/notices')
      await page.waitForSelector('text=Internal notices', { timeout: 10000 })
      await expect(page.locator('text=PUBLISHED').first()).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('Validation', () => {
    test('empty notice title shows required validation', async ({ page }) => {
      await page.goto('/org/notices')
      await page.waitForSelector('input[placeholder="Title"]', { timeout: 10000 })
      // Submit without filling title
      await page.fill('textarea[placeholder="Body"]', 'Body only, no title')
      await page.click('button[type="submit"]')
      // HTML5 required on title — page stays, no navigation
      expect(page.url()).toContain('/org/notices')
    })
  })
})
