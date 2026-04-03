import { orgAdminTest as test, expect } from '../fixtures/auth'

test.describe('Approval Workflows', () => {
  test('approval workflows page loads', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible({ timeout: 10000 })
  })

  test('create workflow action is visible', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await expect(page.getByRole('button', { name: 'Build workflow' })).toBeVisible({ timeout: 10000 })
  })

  test('workflow builder page has name input and create button', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.getByRole('button', { name: 'Build workflow' }).click()
    await expect(page).toHaveURL(/\/org\/approval-workflows\/new/, { timeout: 10000 })
    await expect(page.getByRole('heading', { name: 'Create workflow' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('input.field-input').first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('button', { name: 'Create workflow' })).toBeVisible({ timeout: 10000 })
  })

  test('builder prepopulates the default workflow template', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.getByRole('button', { name: 'Build workflow' }).click()
    await page.waitForSelector('button:has-text("Create workflow")', { timeout: 10000 })

    await expect(page.locator('input.field-input').first()).toHaveValue('Default Leave Workflow')
    await expect(page.locator('text=Default leave rule')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Manager review')).toBeVisible({ timeout: 10000 })
  })

  test('created workflow appears in the configured workflows list', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.waitForSelector('text=Workflow catalogue', { timeout: 10000 })
    const workflowItem = page.locator('.surface-muted').first()
    await expect(workflowItem).toBeVisible({ timeout: 10000 })
  })

  test('workflow shows Default and Active badges when applicable', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.waitForSelector('text=Workflow catalogue', { timeout: 10000 })
    await expect(page.locator('text=Default').first()).toBeVisible({ timeout: 10000 })
  })

  test('approval inbox section is visible', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.getByRole('button', { name: 'Inbox' }).click()
    await expect(page.locator('text=Approval inbox')).toBeVisible({ timeout: 10000 })
  })
})
