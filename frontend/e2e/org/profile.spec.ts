import { orgAdminTest as test, expect } from '../fixtures/auth'

async function openProfileAddressModal(page: Parameters<typeof test>[0]['page']) {
  await page.goto('/org/profile')
  await expect(page.getByRole('heading', { name: 'Organisation profile' })).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: 'Add address' }).click()
  await expect(page.getByRole('heading', { name: 'Add address' })).toBeVisible({ timeout: 5000 })
}

test.describe('Org Admin — Profile (read-only)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/profile')
    await expect(page.getByRole('heading', { name: 'Organisation profile' })).toBeVisible({ timeout: 10000 })
  })

  test('profile page loads at /org/profile — org name and PAN visible', async ({ page }) => {
    await expect(page.locator('#name')).toHaveValue('Acme Workforce Pvt Ltd')
    await expect(page.locator('#pan_number')).toHaveValue('AACCA1234F')
  })

  test('core profile form is pre-filled with current values', async ({ page }) => {
    await expect(page.locator('#country_code')).toContainText('India')
    await expect(page.locator('#currency')).toContainText('Indian Rupee')
    await expect(page.locator('#entity_type')).toContainText('Private Limited Company')
  })

  test('bootstrap admin card is visible', async ({ page }) => {
    const bootstrapCard = page.locator('.surface-muted').filter({ hasText: 'Primary admin' }).first()
    await expect(bootstrapCard).toBeVisible()
    await expect(bootstrapCard.getByText('Aditi Rao', { exact: true })).toBeVisible()
    await expect(bootstrapCard.getByText('admin@acmeworkforce.com', { exact: true })).toBeVisible()
  })

  test('address directory shows seeded mandatory and operational addresses', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Address directory' })).toBeVisible()
    await expect(page.getByText('Registered Office', { exact: true })).toBeVisible()
    await expect(page.getByText('Billing Address', { exact: true })).toBeVisible()
    await expect(page.getByText('Bengaluru HQ', { exact: true })).toBeVisible()
    await expect(page.getByText('East Fulfilment Hub', { exact: true })).toBeVisible()
    await expect(page.getByText('Pune Satellite Office', { exact: true })).toBeVisible()
  })
})

test.describe('Org Admin — Profile (address modal and validation)', () => {
  test('add address modal exposes the current fields', async ({ page }) => {
    await openProfileAddressModal(page)
    await expect(page.locator('#address_type')).toBeVisible()
    await expect(page.locator('#label')).toBeVisible()
    await expect(page.locator('#line1')).toBeVisible()
    await expect(page.locator('#city')).toBeVisible()
    await expect(page.locator('#address-state')).toBeVisible()
    await expect(page.locator('#pincode')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Add address' })).toBeVisible()
  })

  test('editing an existing address pre-fills the modal', async ({ page }) => {
    await page.goto('/org/profile')
    await expect(page.getByRole('heading', { name: 'Address directory' })).toBeVisible({ timeout: 10000 })
    const addressCard = page.locator('.surface-muted').filter({ hasText: 'Pune Satellite Office' }).first()
    await addressCard.getByRole('button', { name: 'Edit' }).click()
    await expect(page.getByRole('heading', { name: 'Edit address' })).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#label')).toHaveValue('Pune Satellite Office')
    await expect(page.locator('#city')).toHaveValue('Pune')
    await expect(page.getByRole('button', { name: 'Save address' })).toBeVisible()
  })

  test('non-mandatory address cards expose deactivate actions', async ({ page }) => {
    await page.goto('/org/profile')
    const addressCard = page.locator('.surface-muted').filter({ hasText: 'Bengaluru HQ' }).first()
    await expect(addressCard).toBeVisible({ timeout: 10000 })
    await expect(addressCard.getByRole('button', { name: 'Deactivate' })).toBeVisible()
  })

  test('PAN validation — blank PAN remains invalid before submit', async ({ page }) => {
    await page.goto('/org/profile')
    await page.locator('#pan_number').fill('')
    await page.getByRole('button', { name: 'Save organisation profile' }).click()
    const isInvalid = await page.locator('#pan_number').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
    await page.locator('#pan_number').fill('AACCA1234F')
  })
})
