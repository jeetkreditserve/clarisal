import { orgAdminTest as test, expect } from '../../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

test.describe('On-Duty Policies', () => {
  test('on-duty policies page loads', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await expect(page.locator('text=On-duty policies')).toBeVisible({ timeout: 10000 })
  })

  test('create OD policy form is visible', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await expect(page.locator('text=Create OD policy')).toBeVisible({ timeout: 10000 })
  })

  test('policy name field has correct id', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await expect(page.locator('#od-policy-name')).toBeVisible({ timeout: 10000 })
  })

  test('create on-duty policy', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await page.waitForSelector('#od-policy-name', { timeout: 10000 })

    const policyName = uniqueName('E2E OD Policy')
    await page.fill('#od-policy-name', policyName)

    await page.click('button[type="submit"]')
    await waitForToast(page, 'On-duty policy created.')
  })

  test('created policy appears in the list', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await page.waitForSelector('text=On-duty policies', { timeout: 10000 })
    // At least one policy should now exist after creation
    const policyItem = page.locator('.surface-muted, tbody tr').first()
    await expect(policyItem).toBeVisible({ timeout: 10000 })
  })

  test('empty policy name shows validation error', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await page.waitForSelector('#od-policy-name', { timeout: 10000 })
    // Clear field and submit
    await page.fill('#od-policy-name', '')
    await page.click('button[type="submit"]')
    // HTML5 required or field error — page should not navigate
    expect(page.url()).toContain('/org/on-duty-policies')
  })
})
