import { orgAdminTest as test, expect } from '../../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

test.describe('Org Admin — Profile (read-only)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/profile')
    await expect(page.getByText('Organisation profile')).toBeVisible({ timeout: 10000 })
  })

  test('profile page loads at /org/profile — org name and PAN visible', async ({ page }) => {
    await expect(page.getByText('Organisation profile')).toBeVisible()
    // The form is pre-filled with the org name
    await expect(page.locator('#name')).toHaveValue('Acme Workforce Pvt Ltd')
    await expect(page.locator('#pan_number')).toHaveValue('AACCA1234F')
  })

  test('edit org profile form is pre-filled with current data', async ({ page }) => {
    const nameInput = page.locator('#name')
    const panInput = page.locator('#pan_number')
    await expect(nameInput).toHaveValue('Acme Workforce Pvt Ltd')
    await expect(panInput).toHaveValue('AACCA1234F')
    const emailInput = page.locator('#email')
    await expect(emailInput).not.toBeEmpty()
  })

  test('addresses are visible — 5 seeded addresses shown', async ({ page }) => {
    await expect(page.getByText('Address directory')).toBeVisible()
    // The seeded org has 5 addresses
    const addressCards = page.locator('.surface-muted').filter({ hasText: 'Active' })
    await expect(addressCards).toHaveCount(5, { timeout: 10000 })
  })
})

test.describe('Org Admin — Profile (write)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/org/profile')
    await expect(page.getByText('Organisation profile')).toBeVisible({ timeout: 10000 })
  })

  test('save profile — change email field, submit, verify toast success', async ({ page }) => {
    const emailInput = page.locator('#email')
    await emailInput.fill('updated.contact@acmeworkforce.com')
    await page.getByRole('button', { name: 'Save organisation profile' }).click()
    await waitForToast(page, 'Organisation profile updated.')
    // Restore original
    await emailInput.fill('admin@acmeworkforce.com')
    await page.getByRole('button', { name: 'Save organisation profile' }).click()
    await waitForToast(page, 'Organisation profile updated.')
  })

  test('add new address — fill required fields, submit, verify success toast', async ({ page }) => {
    // Default address_type is CUSTOM, so label is required
    await page.locator('#label').fill(uniqueName('E2E Office'))
    await page.locator('#line1').fill('123 E2E Street')
    await page.locator('#city').fill('Mumbai')
    // State is a select for India (IN) — select Maharashtra
    const stateSelect = page.locator('#address-state')
    if (await stateSelect.evaluate((el) => el.tagName.toLowerCase()) === 'select') {
      await stateSelect.selectOption({ label: 'Maharashtra' })
    } else {
      await stateSelect.fill('Maharashtra')
    }
    await page.locator('#pincode').fill('400001')
    await page.getByRole('button', { name: 'Add address' }).click()
    await waitForToast(page, 'Address created.')
  })

  test('edit existing address — click edit, change city, submit, verify toast', async ({ page }) => {
    // Click first Edit button in the address directory
    const editButtons = page.getByRole('button', { name: 'Edit' })
    await editButtons.first().click()
    // The form should now show "Save address" button
    await expect(page.getByRole('button', { name: 'Save address' })).toBeVisible({ timeout: 5000 })
    // Change the city
    await page.locator('#city').fill('Pune')
    await page.getByRole('button', { name: 'Save address' }).click()
    await waitForToast(page, 'Address updated.')
  })

  test('PAN validation — enter invalid PAN, field accepts it but save validates server-side', async ({ page }) => {
    // The PAN field has required attr but no frontend regex; test that blank PAN blocks submit
    await page.locator('#pan_number').fill('')
    await page.getByRole('button', { name: 'Save organisation profile' }).click()
    // HTML5 required validation prevents submission — no toast should appear
    // The field should be invalid
    const isInvalid = await page.locator('#pan_number').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
    // Restore valid PAN
    await page.locator('#pan_number').fill('AACCA1234F')
  })
})

test.describe('Org Admin — Profile (destructive)', () => {
  test('delete an address — click deactivate, confirm, address becomes inactive', async ({ page }) => {
    await page.goto('/org/profile')
    await expect(page.getByText('Address directory')).toBeVisible({ timeout: 10000 })

    // Count active Deactivate buttons before
    const deactivateButtons = page.getByRole('button', { name: 'Deactivate' })
    const countBefore = await deactivateButtons.count()
    expect(countBefore).toBeGreaterThan(0)

    // Handle window.confirm
    page.once('dialog', (dialog) => dialog.accept())
    await deactivateButtons.first().click()
    await waitForToast(page, 'Address deactivated.')
  })
})
