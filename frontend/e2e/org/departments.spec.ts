import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

test.describe('Org Admin — Departments (read-only)', () => {
  test('departments page loads at /org/departments', async ({ page }) => {
    await page.goto('/org/departments')
    await expect(page.getByText('Departments')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Define the organisation structure')).toBeVisible()
  })

  test('empty state is visible initially — no departments seeded', async ({ page }) => {
    await page.goto('/org/departments')
    await expect(page.getByText('Departments')).toBeVisible({ timeout: 10000 })
    // Department directory section shows empty state when no departments exist
    await expect(page.getByText('No departments added yet')).toBeVisible({ timeout: 10000 })
  })

  test('add department form is visible on the page', async ({ page }) => {
    await page.goto('/org/departments')
    await expect(page.getByText('Add department')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('#department-name')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create department' })).toBeVisible()
  })

  test('form validation — empty name shows HTML5 required validation', async ({ page }) => {
    await page.goto('/org/departments')
    await expect(page.getByRole('button', { name: 'Create department' })).toBeVisible({ timeout: 10000 })
    // Click submit without filling name
    await page.getByRole('button', { name: 'Create department' }).click()
    // HTML5 required validation should prevent submission
    const isInvalid = await page.locator('#department-name').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })
})

test.describe('Org Admin — Departments (write)', () => {
  test('create department — fill name, submit, success toast, department appears in list', async ({ page }) => {
    const deptName = uniqueName('Engineering')
    await page.goto('/org/departments')
    await expect(page.locator('#department-name')).toBeVisible({ timeout: 10000 })

    await page.locator('#department-name').fill(deptName)
    await page.locator('#department-description').fill('E2E test department')
    await page.getByRole('button', { name: 'Create department' }).click()
    await waitForToast(page, 'Department created.')

    // Department should appear in the directory
    await expect(page.getByText(deptName)).toBeVisible({ timeout: 8000 })
  })

  test('edit department — change name, save, toast success', async ({ page }) => {
    const deptName = uniqueName('HR')
    await page.goto('/org/departments')
    await expect(page.locator('#department-name')).toBeVisible({ timeout: 10000 })

    // Create the department first
    await page.locator('#department-name').fill(deptName)
    await page.getByRole('button', { name: 'Create department' }).click()
    await waitForToast(page, 'Department created.')
    await expect(page.getByText(deptName)).toBeVisible({ timeout: 8000 })

    // Now edit it
    const deptCard = page.locator('.surface-muted').filter({ hasText: deptName })
    await deptCard.getByRole('button', { name: 'Edit' }).click()

    // Form should switch to "Edit department" with "Save changes"
    await expect(page.getByRole('button', { name: 'Save changes' })).toBeVisible({ timeout: 5000 })

    const updatedName = `${deptName} Updated`
    await page.locator('#department-name').fill(updatedName)
    await page.getByRole('button', { name: 'Save changes' }).click()
    await waitForToast(page, 'Department updated.')
    await expect(page.getByText(updatedName)).toBeVisible({ timeout: 8000 })
  })
})

test.describe('Org Admin — Departments (destructive)', () => {
  test('create second department, then deactivate it', async ({ page }) => {
    const tempDeptName = uniqueName('Temp Dept')
    await page.goto('/org/departments')
    await expect(page.locator('#department-name')).toBeVisible({ timeout: 10000 })

    // Create the department
    await page.locator('#department-name').fill(tempDeptName)
    await page.getByRole('button', { name: 'Create department' }).click()
    await waitForToast(page, 'Department created.')
    await expect(page.getByText(tempDeptName)).toBeVisible({ timeout: 8000 })

    // Deactivate it — uses window.confirm
    const deptCard = page.locator('.surface-muted').filter({ hasText: tempDeptName })
    page.once('dialog', (dialog) => dialog.accept())
    await deptCard.getByRole('button', { name: 'Deactivate' }).click()
    await waitForToast(page, 'Department deactivated.')
  })
})
