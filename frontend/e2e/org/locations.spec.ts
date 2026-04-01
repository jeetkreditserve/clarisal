import { orgAdminTest as test, expect } from '../../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

test.describe('Org Admin — Locations (read-only)', () => {
  test('locations page loads at /org/locations', async ({ page }) => {
    await page.goto('/org/locations')
    await expect(page.getByText('Office locations')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Every office location must link to an organisation address')).toBeVisible()
  })

  test('empty state is visible initially — no locations seeded', async ({ page }) => {
    await page.goto('/org/locations')
    await expect(page.getByText('Office locations')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('No locations added yet')).toBeVisible({ timeout: 10000 })
  })

  test('add location form is visible on the page', async ({ page }) => {
    await page.goto('/org/locations')
    await expect(page.getByText('Add location')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('#location-name')).toBeVisible()
    await expect(page.locator('#location-address')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create location' })).toBeVisible()
  })

  test('form validation — empty name shows HTML5 required validation', async ({ page }) => {
    await page.goto('/org/locations')
    await expect(page.getByRole('button', { name: 'Create location' })).toBeVisible({ timeout: 10000 })
    // Click submit without filling required fields
    await page.getByRole('button', { name: 'Create location' }).click()
    // HTML5 required validation should prevent submission
    const isInvalid = await page.locator('#location-name').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })
})

test.describe('Org Admin — Locations (write)', () => {
  test('create location — fill name + linked address, submit, success toast', async ({ page }) => {
    const locationName = uniqueName('Head Office')
    await page.goto('/org/locations')
    await expect(page.locator('#location-name')).toBeVisible({ timeout: 10000 })

    await page.locator('#location-name').fill(locationName)

    // Select any available address from the dropdown
    const addressSelect = page.locator('#location-address')
    const options = await addressSelect.locator('option').all()
    // options[0] is the placeholder, pick options[1] if available
    if (options.length > 1) {
      const optionValue = await options[1].getAttribute('value')
      if (optionValue) {
        await addressSelect.selectOption(optionValue)
      }
    }

    await page.getByRole('button', { name: 'Create location' }).click()
    await waitForToast(page, 'Location created.')

    // Location should appear in the directory
    await expect(page.getByText(locationName)).toBeVisible({ timeout: 8000 })
  })

  test('location appears in the list after creation', async ({ page }) => {
    const locationName = uniqueName('Branch Office')
    await page.goto('/org/locations')
    await expect(page.locator('#location-name')).toBeVisible({ timeout: 10000 })

    await page.locator('#location-name').fill(locationName)

    const addressSelect = page.locator('#location-address')
    const options = await addressSelect.locator('option').all()
    if (options.length > 1) {
      const optionValue = await options[1].getAttribute('value')
      if (optionValue) {
        await addressSelect.selectOption(optionValue)
      }
    }

    await page.getByRole('button', { name: 'Create location' }).click()
    await waitForToast(page, 'Location created.')

    // Verify in location directory
    await expect(page.getByText('Location directory')).toBeVisible()
    await expect(page.getByText(locationName)).toBeVisible({ timeout: 8000 })
  })

  test('edit location — change name, save, toast success', async ({ page }) => {
    const locationName = uniqueName('Regional Office')
    await page.goto('/org/locations')
    await expect(page.locator('#location-name')).toBeVisible({ timeout: 10000 })

    // Create a location to edit
    await page.locator('#location-name').fill(locationName)
    const addressSelect = page.locator('#location-address')
    const options = await addressSelect.locator('option').all()
    if (options.length > 1) {
      const optionValue = await options[1].getAttribute('value')
      if (optionValue) {
        await addressSelect.selectOption(optionValue)
      }
    }
    await page.getByRole('button', { name: 'Create location' }).click()
    await waitForToast(page, 'Location created.')
    await expect(page.getByText(locationName)).toBeVisible({ timeout: 8000 })

    // Edit it
    const locationCard = page.locator('.surface-muted').filter({ hasText: locationName })
    await locationCard.getByRole('button', { name: 'Edit' }).click()

    // Form should switch to "Edit location" with "Save changes"
    await expect(page.getByRole('button', { name: 'Save changes' })).toBeVisible({ timeout: 5000 })

    const updatedName = `${locationName} Updated`
    await page.locator('#location-name').fill(updatedName)
    await page.getByRole('button', { name: 'Save changes' }).click()
    await waitForToast(page, 'Location updated.')
    await expect(page.getByText(updatedName)).toBeVisible({ timeout: 8000 })
  })
})

test.describe('Org Admin — Locations (destructive)', () => {
  test('deactivate location — create, deactivate, confirm dialog', async ({ page }) => {
    const locationName = uniqueName('Temp Location')
    await page.goto('/org/locations')
    await expect(page.locator('#location-name')).toBeVisible({ timeout: 10000 })

    // Create the location
    await page.locator('#location-name').fill(locationName)
    const addressSelect = page.locator('#location-address')
    const options = await addressSelect.locator('option').all()
    if (options.length > 1) {
      const optionValue = await options[1].getAttribute('value')
      if (optionValue) {
        await addressSelect.selectOption(optionValue)
      }
    }
    await page.getByRole('button', { name: 'Create location' }).click()
    await waitForToast(page, 'Location created.')
    await expect(page.getByText(locationName)).toBeVisible({ timeout: 8000 })

    // Deactivate it — uses window.confirm
    const locationCard = page.locator('.surface-muted').filter({ hasText: locationName })
    page.once('dialog', (dialog) => dialog.accept())
    await locationCard.getByRole('button', { name: 'Deactivate' }).click()
    await waitForToast(page, 'Location deactivated.')
  })
})
