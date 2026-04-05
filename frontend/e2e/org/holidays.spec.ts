import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

async function openHolidayModal(page: Parameters<typeof test>[0]['page']) {
  await page.goto('/org/holidays')
  await expect(page.getByRole('heading', { name: 'Holiday calendars' })).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: 'Add holiday calendar' }).click()
  await expect(page.getByText('Create holiday calendar')).toBeVisible({ timeout: 5000 })
}

async function selectVisibleCalendarDate(page: Parameters<typeof test>[0]['page']) {
  const currentYear = String(new Date().getFullYear())
  await page.getByRole('button', { name: 'Select holiday date' }).click()
  await page.locator(`button[aria-label*="${currentYear}"]`).first().click()
}

test.describe('Org Admin — Holiday Calendars (read-only)', () => {
  test('holiday calendars page loads at /org/holidays', async ({ page }) => {
    await page.goto('/org/holidays')
    await expect(page.getByRole('heading', { name: 'Holiday calendars' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Define and publish annual holiday calendars')).toBeVisible()
  })

  test('calendar catalogue section is visible', async ({ page }) => {
    await page.goto('/org/holidays')
    await expect(page.getByText('Published and draft calendars')).toBeVisible({ timeout: 10000 })
  })

  test('create holiday calendar modal fields are present', async ({ page }) => {
    await openHolidayModal(page)
    await expect(page.getByPlaceholder('Calendar name')).toBeVisible()
    await expect(page.locator('input[type="number"]').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Select holiday date' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Add holiday' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save holiday calendar' })).toBeVisible()
  })
})

test.describe('Org Admin — Holiday Calendars (existing records)', () => {
  test('draft seeded calendar shows DRAFT badge and publish action', async ({ page }) => {
    await page.goto('/org/holidays')
    const calendarCard = page.locator('.surface-muted').filter({ hasText: 'Draft Holiday Calendar' }).first()
    await expect(calendarCard).toBeVisible({ timeout: 10000 })
    await expect(calendarCard.getByText('DRAFT', { exact: true })).toBeVisible()
    await expect(calendarCard.getByRole('button', { name: 'Publish' })).toBeVisible()
  })

  test('published seeded calendar hides publish action', async ({ page }) => {
    await page.goto('/org/holidays')
    const calendarCard = page.locator('.surface-muted').filter({ hasText: 'FY Operations Calendar' }).first()
    await expect(calendarCard).toBeVisible({ timeout: 10000 })
    await expect(calendarCard.getByText('PUBLISHED')).toBeVisible()
    await expect(calendarCard.getByRole('button', { name: 'Publish' })).toHaveCount(0)
  })

  test('editing a seeded calendar opens a prefilled modal', async ({ page }) => {
    await page.goto('/org/holidays')
    const calendarCard = page.locator('.surface-muted').filter({ hasText: 'Draft Holiday Calendar' }).first()
    await calendarCard.getByRole('button', { name: 'Edit' }).click()
    await expect(page.getByRole('heading', { name: 'Edit holiday calendar' })).toBeVisible({ timeout: 5000 })
    await expect(page.getByPlaceholder('Calendar name')).toHaveValue('Draft Holiday Calendar')
  })
})

test.describe('Org Admin — Holiday Calendars (validation)', () => {
  test('form validation — empty holiday name blocks submission', async ({ page }) => {
    await openHolidayModal(page)
    await page.getByPlaceholder('Calendar name').fill('Validation Test Calendar')
    await page.getByRole('button', { name: 'Save holiday calendar' }).click()
    const holidayNameInput = page.getByPlaceholder('Holiday name').first()
    const isInvalid = await holidayNameInput.evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })

  test('add holiday button adds a new holiday entry row', async ({ page }) => {
    await openHolidayModal(page)
    await expect(page.getByPlaceholder('Holiday name')).toHaveCount(1)
    await page.getByRole('button', { name: 'Add holiday' }).click()
    await expect(page.getByPlaceholder('Holiday name')).toHaveCount(2)
  })
})
