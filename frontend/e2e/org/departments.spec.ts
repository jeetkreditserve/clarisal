import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

async function openDepartmentModal(page: Parameters<typeof test>[0]['page']) {
  await page.goto('/org/departments')
  await expect(page.getByRole('heading', { name: 'Departments' })).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: 'Add department' }).click()
  await expect(page.getByRole('heading', { name: 'Add department' })).toBeVisible({ timeout: 5000 })
}

test.describe('Org Admin — Departments (read-only)', () => {
  test('departments page loads at /org/departments', async ({ page }) => {
    await page.goto('/org/departments')
    await expect(page.getByRole('heading', { name: 'Departments' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Define the organisation structure')).toBeVisible()
  })

  test('directory and hierarchy sections are visible', async ({ page }) => {
    await page.goto('/org/departments')
    await expect(page.getByRole('heading', { name: 'Department directory' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Hierarchy diagram' })).toBeVisible({ timeout: 10000 })
  })

  test('add department modal opens with required fields', async ({ page }) => {
    await openDepartmentModal(page)
    await expect(page.locator('#department-name')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create department' })).toBeVisible()
  })

  test('form validation — empty name shows HTML5 required validation', async ({ page }) => {
    await openDepartmentModal(page)
    await page.getByRole('button', { name: 'Create department' }).click()
    const isInvalid = await page.locator('#department-name').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })
})

test.describe('Org Admin — Departments (existing records)', () => {
  test('seeded department cards expose edit and deactivate actions', async ({ page }) => {
    await page.goto('/org/departments')
    const departmentCard = page.locator('.surface-muted').filter({ hasText: 'Engineering' }).first()
    await expect(departmentCard).toBeVisible({ timeout: 10000 })
    await expect(departmentCard.getByRole('button', { name: 'Edit' })).toBeVisible()
    await expect(departmentCard.getByRole('button', { name: 'Deactivate' })).toBeVisible()
  })

  test('editing an existing department pre-fills the modal', async ({ page }) => {
    await page.goto('/org/departments')
    const departmentCard = page.locator('.surface-muted').filter({ hasText: 'Engineering' }).first()
    await departmentCard.getByRole('button', { name: 'Edit' }).click()
    await expect(page.getByRole('heading', { name: 'Edit department' })).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#department-name')).toHaveValue('Engineering')
  })

  test('hierarchy diagram includes nested seeded departments', async ({ page }) => {
    await page.goto('/org/departments')
    await expect(page.getByText('Platform Engineering').first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Product Engineering').first()).toBeVisible({ timeout: 10000 })
  })
})
