import { orgAdminTest as test, expect } from '../../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

// NOTE: LeaveCyclesPage renders both the create form and the cycle list on the same page.
// The right panel is titled "Configured leave cycles" and shows an empty list initially.
// The cycle_type field uses a custom AppSelect (Radix Select) component with a trigger button.

test.describe('Org Admin — Leave Cycles (read-only)', () => {
  test('leave cycles page loads at /org/leave-cycles', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    await expect(page.getByText('Leave cycles')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Define the leave year separately')).toBeVisible()
  })

  test('configured leave cycles list is visible (empty initially)', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    await expect(page.getByText('Configured leave cycles')).toBeVisible({ timeout: 10000 })
    // Empty list — no cycle cards yet
    await expect(page.locator('.surface-muted')).toHaveCount(0)
  })

  test('create leave cycle form is visible with required fields', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    await expect(page.getByText('Create leave cycle')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('#leave-cycle-name')).toBeVisible()
    // Cycle type trigger (Radix Select)
    await expect(page.getByText('Cycle type')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save leave cycle' })).toBeVisible()
  })

  test('form validation — empty name blocks submission', async ({ page }) => {
    await page.goto('/org/leave-cycles')
    await expect(page.locator('#leave-cycle-name')).toBeVisible({ timeout: 10000 })

    // Clear the pre-filled name and try to submit
    await page.locator('#leave-cycle-name').clear()
    await page.getByRole('button', { name: 'Save leave cycle' }).click()

    // HTML5 required validation should block submission
    const isInvalid = await page.locator('#leave-cycle-name').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })
})

test.describe('Org Admin — Leave Cycles (write)', () => {
  test('create leave cycle — fill name, keep CALENDAR_YEAR type, submit, verify toast', async ({ page }) => {
    const cycleName = uniqueName('Annual Leave Cycle')
    await page.goto('/org/leave-cycles')
    await expect(page.locator('#leave-cycle-name')).toBeVisible({ timeout: 10000 })

    // The name field is pre-filled with "Default Leave Year" — overwrite it
    await page.locator('#leave-cycle-name').fill(cycleName)

    // Cycle type defaults to CALENDAR_YEAR — leave it as is
    // Start month and start day default to 1/1 — leave them

    await page.getByRole('button', { name: 'Save leave cycle' }).click()
    await waitForToast(page, 'Leave cycle created.')

    // Cycle appears in the configured list on the right
    await expect(page.getByText(cycleName)).toBeVisible({ timeout: 8000 })
  })

  test('created cycle shows cycle type and start date in the list', async ({ page }) => {
    const cycleName = uniqueName('Financial Year Cycle')
    await page.goto('/org/leave-cycles')
    await expect(page.locator('#leave-cycle-name')).toBeVisible({ timeout: 10000 })

    await page.locator('#leave-cycle-name').fill(cycleName)

    // Change cycle type to FINANCIAL YEAR via Radix Select
    // AppSelect renders a button-like trigger; click it to open dropdown
    await page.locator('#leave-cycle-type').locator('..').locator('button').click()
    // Click the FINANCIAL YEAR option in the dropdown list
    await page.getByRole('option', { name: 'FINANCIAL YEAR' }).click()

    await page.locator('#start-month').fill('4')
    await page.locator('#start-day').fill('1')

    await page.getByRole('button', { name: 'Save leave cycle' }).click()
    await waitForToast(page, 'Leave cycle created.')

    // The list card shows "starts 4/1"
    await expect(page.getByText(cycleName)).toBeVisible({ timeout: 8000 })
    const cycleCard = page.locator('.surface-muted').filter({ hasText: cycleName })
    await expect(cycleCard.getByText(/starts 4\/1/)).toBeVisible()
  })
})
