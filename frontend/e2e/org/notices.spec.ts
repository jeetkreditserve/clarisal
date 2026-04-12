import { orgAdminTest as test, expect } from '../fixtures/auth'

test.describe('Org Admin — Notices', () => {
  test('notices page loads', async ({ page }) => {
    await page.goto('/org/notices')
    await expect(page.getByRole('heading', { name: 'Announcement center' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Publish richer internal notices')).toBeVisible()
  })

  test('filters, list section, and compose action are visible', async ({ page }) => {
    await page.goto('/org/notices')
    await expect(page.getByRole('heading', { name: 'Filters' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Notices' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Compose notice' })).toBeVisible()
  })

  test('compose notice opens the full-page builder', async ({ page }) => {
    await page.goto('/org/notices')
    await page.getByRole('button', { name: 'Compose notice' }).click()
    await page.waitForURL('**/org/notices/new', { timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Compose notice' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Notice basics' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create notice' })).toBeVisible()
  })

  test('seeded notices render published, scheduled, and draft states', async ({ page }) => {
    await page.goto('/org/notices')

    const publishedCard = page.locator('.surface-muted').filter({ hasText: 'Performance calibration window opens Monday' }).first()
    const scheduledCard = page.locator('.surface-muted').filter({ hasText: 'Bengaluru HQ access maintenance' }).first()
    const draftCard = page.locator('.surface-muted').filter({ hasText: 'Finance policy refresh draft' }).first()

    await expect(publishedCard).toBeVisible({ timeout: 10000 })
    await expect(publishedCard.locator('.status-pill').filter({ hasText: 'Published' }).first()).toBeVisible()
    await expect(scheduledCard).toBeVisible()
    await expect(scheduledCard.locator('.status-pill').filter({ hasText: 'Scheduled' }).first()).toBeVisible()
    await expect(draftCard).toBeVisible()
    await expect(draftCard.getByRole('button', { name: 'Edit' })).toBeVisible()
  })

  test('search filter narrows the notice list', async ({ page }) => {
    await page.goto('/org/notices')
    const searchInput = page.locator('#notice-search')
    await searchInput.fill('finance policy')
    await expect(page.getByText('Finance policy refresh draft')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Performance calibration window opens Monday')).toHaveCount(0)
  })

  test('editing a seeded notice opens the editor with existing values', async ({ page }) => {
    await page.goto('/org/notices')
    const draftCard = page.locator('.surface-muted').filter({ hasText: 'Finance policy refresh draft' }).first()
    await draftCard.getByRole('button', { name: 'Edit' }).click()
    await page.waitForURL('**/org/notices/*', { timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Edit notice' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('input.field-input').first()).toHaveValue('Finance policy refresh draft')
    await expect(page.locator('textarea.field-textarea')).toContainText('Draft notice reserved for targeted finance users.')
  })
})
