import { orgAdminTest as test, expect } from '../fixtures/auth'

async function openLocationModal(page: Parameters<typeof test>[0]['page']) {
  await page.goto('/org/locations')
  await expect(page.getByRole('heading', { name: 'Office locations' })).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: 'Add location' }).click()
  await expect(page.getByRole('heading', { name: 'Add location' })).toBeVisible({ timeout: 5000 })
}

test.describe('Org Admin — Locations (read-only)', () => {
  test('locations page loads at /org/locations', async ({ page }) => {
    await page.goto('/org/locations')
    await expect(page.getByRole('heading', { name: 'Office locations' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Every office location links to an organisation address')).toBeVisible()
  })

  test('location directory and add action are visible', async ({ page }) => {
    await page.goto('/org/locations')
    await expect(page.getByRole('heading', { name: 'Location directory' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('button', { name: 'Add location' })).toBeVisible()
  })

  test('add location modal exposes the current required fields', async ({ page }) => {
    await openLocationModal(page)
    await expect(page.locator('#location-name')).toBeVisible()
    await expect(page.locator('#location-address')).toBeVisible()
    await expect(page.getByText('Mark as remote office location')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create location' })).toBeVisible()
  })

  test('form validation — empty name shows HTML5 required validation', async ({ page }) => {
    await openLocationModal(page)
    await page.getByRole('button', { name: 'Create location' }).click()
    const isInvalid = await page.locator('#location-name').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })
})

test.describe('Org Admin — Locations (existing records)', () => {
  test('seeded location cards expose edit and deactivate actions', async ({ page }) => {
    await page.goto('/org/locations')
    const locationCard = page.locator('.surface-muted').filter({ hasText: 'Registered Office' }).first()
    await expect(locationCard).toBeVisible({ timeout: 10000 })
    await expect(locationCard.getByRole('button', { name: 'Edit' })).toBeVisible()
    await expect(locationCard.getByRole('button', { name: 'Deactivate' })).toBeVisible()
  })

  test('remote seeded location shows the remote status badge', async ({ page }) => {
    await page.goto('/org/locations')
    const remoteCard = page.locator('.surface-muted').filter({ hasText: 'Distributed Workforce' }).first()
    await expect(remoteCard).toBeVisible({ timeout: 10000 })
    await expect(remoteCard.getByText('Remote')).toBeVisible()
  })

  test('editing an existing location pre-fills the modal', async ({ page }) => {
    await page.goto('/org/locations')
    const locationCard = page.locator('.surface-muted').filter({ hasText: 'Registered Office' }).first()
    await locationCard.getByRole('button', { name: 'Edit' }).click()
    await expect(page.getByRole('heading', { name: 'Edit location' })).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#location-name')).toHaveValue('Registered Office')
    await expect(page.locator('#location-address')).toContainText('Registered Office')
    await expect(page.getByRole('button', { name: 'Save changes' })).toBeVisible()
  })
})
