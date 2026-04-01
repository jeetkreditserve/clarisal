import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

// NOTE: The HolidaysPage renders both the create form and the calendar list on the same page.
// There is no empty-state text rendered when no calendars exist — the right column simply shows
// an empty list. Tests reflect what is actually visible in the DOM.

test.describe('Org Admin — Holiday Calendars (read-only)', () => {
  test('holiday calendars page loads at /org/holidays', async ({ page }) => {
    await page.goto('/org/holidays')
    await expect(page.getByText('Holiday calendars')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Define and publish annual holiday calendars')).toBeVisible()
  })

  test('create form is visible on the page (no calendars seeded)', async ({ page }) => {
    await page.goto('/org/holidays')
    await expect(page.getByText('Create holiday calendar')).toBeVisible({ timeout: 10000 })
    // The published/draft list panel is also visible but empty
    await expect(page.getByText('Published and draft calendars')).toBeVisible()
  })

  test('create holiday calendar form fields are present', async ({ page }) => {
    await page.goto('/org/holidays')
    await expect(page.getByText('Create holiday calendar')).toBeVisible({ timeout: 10000 })
    await expect(page.getByPlaceholder('Calendar name')).toBeVisible()
    // Year number input
    await expect(page.locator('input[type="number"]').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save holiday calendar' })).toBeVisible()
  })
})

test.describe('Org Admin — Holiday Calendars (write)', () => {
  let calendarName: string

  test('create holiday calendar — fill name + year, submit, verify success toast', async ({ page }) => {
    calendarName = uniqueName('Q1 Holidays')
    await page.goto('/org/holidays')
    await expect(page.getByPlaceholder('Calendar name')).toBeVisible({ timeout: 10000 })

    await page.getByPlaceholder('Calendar name').fill(calendarName)
    // Year field is a number input, pre-filled with current year — keep it
    await page.getByPlaceholder('Description').fill('E2E test calendar')

    // Fill the default holiday entry (name + date are required)
    await page.getByPlaceholder('Holiday name').first().fill('New Year')
    await page.locator('input[type="date"]').first().fill('2025-01-01')

    await page.getByRole('button', { name: 'Save holiday calendar' }).click()
    await waitForToast(page, 'Holiday calendar created.')

    // Calendar should appear in the list panel on the right
    await expect(page.getByText(calendarName)).toBeVisible({ timeout: 8000 })
  })

  test('created calendar appears in list with DRAFT status badge', async ({ page }) => {
    calendarName = uniqueName('Summer Holidays')
    await page.goto('/org/holidays')
    await expect(page.getByPlaceholder('Calendar name')).toBeVisible({ timeout: 10000 })

    await page.getByPlaceholder('Calendar name').fill(calendarName)
    await page.getByPlaceholder('Holiday name').first().fill('Independence Day')
    await page.locator('input[type="date"]').first().fill('2025-08-15')
    await page.getByRole('button', { name: 'Save holiday calendar' }).click()
    await waitForToast(page, 'Holiday calendar created.')

    // The calendar card should show a DRAFT status badge
    const calendarCard = page.locator('.surface-muted').filter({ hasText: calendarName })
    await expect(calendarCard).toBeVisible({ timeout: 8000 })
    await expect(calendarCard.getByText('DRAFT')).toBeVisible()
  })

  test('publish calendar — click publish, status changes to PUBLISHED', async ({ page }) => {
    calendarName = uniqueName('Winter Holidays')
    await page.goto('/org/holidays')
    await expect(page.getByPlaceholder('Calendar name')).toBeVisible({ timeout: 10000 })

    // Create a calendar first
    await page.getByPlaceholder('Calendar name').fill(calendarName)
    await page.getByPlaceholder('Holiday name').first().fill('Christmas')
    await page.locator('input[type="date"]').first().fill('2025-12-25')
    await page.getByRole('button', { name: 'Save holiday calendar' }).click()
    await waitForToast(page, 'Holiday calendar created.')

    // Find the calendar card and click Publish
    const calendarCard = page.locator('.surface-muted').filter({ hasText: calendarName })
    await expect(calendarCard).toBeVisible({ timeout: 8000 })
    await calendarCard.getByRole('button', { name: 'Publish' }).click()

    // Status badge should change to PUBLISHED
    await expect(calendarCard.getByText('PUBLISHED')).toBeVisible({ timeout: 8000 })
  })

  test('published calendar does not show a Publish button', async ({ page }) => {
    calendarName = uniqueName('Festival Holidays')
    await page.goto('/org/holidays')
    await expect(page.getByPlaceholder('Calendar name')).toBeVisible({ timeout: 10000 })

    // Create and immediately publish
    await page.getByPlaceholder('Calendar name').fill(calendarName)
    await page.getByPlaceholder('Holiday name').first().fill('Diwali')
    await page.locator('input[type="date"]').first().fill('2025-10-20')
    await page.getByRole('button', { name: 'Save holiday calendar' }).click()
    await waitForToast(page, 'Holiday calendar created.')

    const calendarCard = page.locator('.surface-muted').filter({ hasText: calendarName })
    await calendarCard.getByRole('button', { name: 'Publish' }).click()
    await expect(calendarCard.getByText('PUBLISHED')).toBeVisible({ timeout: 8000 })

    // Publish button must not appear on an already-published calendar
    await expect(calendarCard.getByRole('button', { name: 'Publish' })).not.toBeVisible()
  })
})

test.describe('Org Admin — Holiday Calendars (validation)', () => {
  test('form validation — empty holiday name blocks submission', async ({ page }) => {
    await page.goto('/org/holidays')
    await expect(page.getByPlaceholder('Calendar name')).toBeVisible({ timeout: 10000 })

    // Fill calendar name but leave holiday name blank
    await page.getByPlaceholder('Calendar name').fill('Validation Test Calendar')
    // Holiday name is required — leave it blank
    await page.getByRole('button', { name: 'Save holiday calendar' }).click()

    // HTML5 validation should block submission (no toast)
    const holidayNameInput = page.getByPlaceholder('Holiday name').first()
    const isInvalid = await holidayNameInput.evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })

  test('add holiday button adds a new holiday entry row', async ({ page }) => {
    await page.goto('/org/holidays')
    await expect(page.getByRole('button', { name: 'Add holiday' })).toBeVisible({ timeout: 10000 })

    // Initially 1 holiday entry
    await expect(page.getByPlaceholder('Holiday name')).toHaveCount(1)

    await page.getByRole('button', { name: 'Add holiday' }).click()

    // Now 2 holiday entries
    await expect(page.getByPlaceholder('Holiday name')).toHaveCount(2)
  })
})
