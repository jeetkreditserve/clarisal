import { orgAdminTest as test, expect } from '../fixtures/auth'

async function openPolicyBuilder(page: Parameters<typeof test>[0]['page']) {
  await page.goto('/org/on-duty-policies')
  await expect(page.getByRole('heading', { name: 'On-duty policies' })).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: 'Build new policy' }).click()
  await page.waitForURL('**/org/on-duty-policies/new', { timeout: 10000 })
  await expect(page.getByRole('heading', { name: 'Create on-duty policy' })).toBeVisible({ timeout: 10000 })
}

test.describe('Org Admin — On-Duty Policies', () => {
  test('on-duty policies page loads', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await expect(page.getByRole('heading', { name: 'On-duty policies' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Govern travel, field work, and time-range OD submissions')).toBeVisible()
  })

  test('policy catalogue and builder action are visible', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    await expect(page.getByRole('heading', { name: 'Policy catalogue' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('button', { name: 'Build new policy' })).toBeVisible()
  })

  test('new policy builder exposes current form fields', async ({ page }) => {
    await openPolicyBuilder(page)
    await expect(page.locator('#od-policy-name')).toBeVisible()
    await expect(page.locator('#od-min-notice')).toBeVisible()
    await expect(page.getByText('Allow half-day OD')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create policy' })).toBeVisible()
  })

  test('empty policy name shows validation error on the builder', async ({ page }) => {
    await openPolicyBuilder(page)
    await page.locator('#od-policy-name').fill('')
    await page.getByRole('button', { name: 'Create policy' }).click()
    const isInvalid = await page.locator('#od-policy-name').evaluate((el: HTMLInputElement) => !el.validity.valid)
    expect(isInvalid).toBe(true)
  })

  test('seeded policy cards show default and active status', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    const defaultCard = page.locator('.surface-muted').filter({ hasText: 'Field Visit / Client Meeting' }).first()
    const warehouseCard = page.locator('.surface-muted').filter({ hasText: 'Warehouse Dispatch Support' }).first()
    await expect(defaultCard).toBeVisible({ timeout: 10000 })
    await expect(defaultCard.getByText('Default', { exact: true })).toBeVisible()
    await expect(defaultCard.getByText('Active', { exact: true })).toBeVisible()
    await expect(warehouseCard).toBeVisible()
  })

  test('opening a seeded policy builder pre-fills the form', async ({ page }) => {
    await page.goto('/org/on-duty-policies')
    const policyCard = page.locator('.surface-muted').filter({ hasText: 'Field Visit / Client Meeting' }).first()
    await policyCard.getByRole('button', { name: 'Open builder' }).click()
    await page.waitForURL('**/org/on-duty-policies/*', { timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Edit on-duty policy' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('#od-policy-name')).toHaveValue('Field Visit / Client Meeting')
    await expect(page.locator('#od-min-notice')).toHaveValue('0')
  })
})
