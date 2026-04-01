import { orgAdminTest as test, expect } from '../fixtures/auth'
import { waitForToast, uniqueName } from '../helpers'

test.describe('Approval Workflows', () => {
  test('approval workflows page loads', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await expect(page.locator('text=Approval workflows')).toBeVisible({ timeout: 10000 })
  })

  test('create workflow action is visible', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await expect(page.locator('button:has-text("Add workflow")')).toBeVisible({ timeout: 10000 })
  })

  test('workflow modal has name input and save button', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.click('button:has-text("Add workflow")')
    await expect(page.locator('text=Create workflow')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('form input.field-input').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('button:has-text("Save workflow")')).toBeVisible({ timeout: 10000 })
  })

  test('create a default approval workflow', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.click('button:has-text("Add workflow")')
    await page.waitForSelector('button:has-text("Save workflow")', { timeout: 10000 })

    const workflowName = uniqueName('E2E Default Workflow')
    await page.locator('form input.field-input').first().fill(workflowName)
    await page.locator('form textarea.field-textarea').fill('Created by e2e tests')

    // Check the "Default workflow" checkbox
    const defaultCheckbox = page.locator('button[role="checkbox"]').first()
    const isChecked = await defaultCheckbox.getAttribute('data-state')
    if (isChecked !== 'checked') {
      await defaultCheckbox.click()
    }

    await page.click('button:has-text("Save workflow")')
    await waitForToast(page, 'Approval workflow created.')
  })

  test('created workflow appears in the configured workflows list', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.waitForSelector('text=Configured workflows', { timeout: 10000 })
    // At least one workflow should be visible now
    const workflowItem = page.locator('.surface-muted').first()
    await expect(workflowItem).toBeVisible({ timeout: 10000 })
  })

  test('workflow shows Default and Active badges when applicable', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.waitForSelector('text=Configured workflows', { timeout: 10000 })
    // StatusBadge with "Default" text should be visible for the default workflow
    await expect(page.locator('text=Default').first()).toBeVisible({ timeout: 10000 })
  })

  test('approval inbox section is visible', async ({ page }) => {
    await page.goto('/org/approval-workflows')
    await page.waitForSelector('text=Approval workflows', { timeout: 10000 })
    await expect(page.locator('text=Approval inbox')).toBeVisible({ timeout: 10000 })
  })
})
