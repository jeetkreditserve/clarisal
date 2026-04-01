import type { Page, Locator } from '@playwright/test'
import { expect } from '@playwright/test'

/** Waits for a sonner toast containing the given text (success or error). */
export async function waitForToast(page: Page, text: string, timeout = 8000) {
  await expect(page.locator('[data-sonner-toast]')).toContainText(text, { timeout })
}

/** Asserts that a table row containing the given text is visible. */
export async function expectTableRow(page: Page, text: string): Promise<Locator> {
  const row = page.locator('tbody tr').filter({ hasText: text })
  await expect(row).toBeVisible()
  return row
}

/** Generates a unique name with a timestamp suffix for write tests. */
export function uniqueName(base: string): string {
  return `${base} ${Date.now()}`
}
