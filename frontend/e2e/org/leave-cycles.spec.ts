import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

async function openLeaveCycleModal(page: Parameters<typeof test>[0]['page']) {
  await page.goto('/org/leave-cycles')
  await expect(page.getByRole('heading', { name: 'Leave cycles' })).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: 'Add leave cycle' }).click()
  await expect(page.getByText('Create leave cycle')).toBeVisible({ timeout: 5000 })
}

test.describe('Org Admin — Leave Cycles (read-only)', () => {
  test('leave cycles page loads at /org/leave-cycles', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    await expect(page.getByRole('heading', { name: 'Leave cycles' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Maintain the leave-year structures')).toBeVisible()
  })

  test('cycle catalogue and metrics are visible', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    await expect(page.getByText('Cycle catalogue')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Configured cycles')).toBeVisible({ timeout: 10000 })
  })

  test('create leave cycle modal is visible with required fields', async ({ page }) => {
    await openLeaveCycleModal(page)
    await expect(page.locator('#leave-cycle-name')).toBeVisible()
    await expect(page.getByText('Cycle type')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save cycle' })).toBeVisible()
  })

  test('form validation — empty name blocks submission', async ({ page }) => {
    await openLeaveCycleModal(page)
    await page.locator('#leave-cycle-name').clear()
    await page.getByRole('button', { name: 'Save cycle' }).click()
    const isInvalid = await page.locator('#leave-cycle-name').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })
})

test.describe('Org Admin — Leave Cycles (existing records)', () => {
  test('seeded cycle cards show their operational windows', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    const calendarCycle = page.locator('.surface-muted').filter({ hasText: 'Calendar Leave Cycle' }).first()
    const fyCycle = page.locator('.surface-muted').filter({ hasText: 'FY Leave Cycle' }).first()
    await expect(calendarCycle).toBeVisible({ timeout: 10000 })
    await expect(calendarCycle.getByText('01 Jan -> 31 Dec')).toBeVisible()
    await expect(fyCycle).toBeVisible()
    await expect(fyCycle.getByText('01 Apr -> 31 Mar')).toBeVisible()
  })

  test('editing a seeded cycle pre-fills the modal', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    const fyCycle = page.locator('.surface-muted').filter({ hasText: 'FY Leave Cycle' }).first()
    await fyCycle.getByRole('button', { name: 'Edit' }).click()
    await expect(page.getByRole('heading', { name: 'Edit leave cycle' })).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#leave-cycle-name')).toHaveValue('FY Leave Cycle')
    await expect(page.getByRole('button', { name: 'Financial Year' })).toBeVisible()
  })

  test('switching the cycle type reveals custom fixed-start inputs', async ({ page }) => {
    await openLeaveCycleModal(page)
    await page.getByRole('button', { name: 'Calendar Year' }).click()
    await page.getByRole('button', { name: 'Custom Fixed Start' }).click()
    await expect(page.locator('#leave-cycle-month')).toBeVisible()
    await expect(page.locator('#leave-cycle-day')).toBeVisible()
  })
})
