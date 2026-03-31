import { chromium } from 'playwright'

const baseUrl = 'http://127.0.0.1:5173'
const controlTowerEmail = process.env.CONTROL_TOWER_EMAIL ?? 'admin@calrisal.com'
const controlTowerPassword = process.env.CONTROL_TOWER_PASSWORD ?? 'change-me-in-production'
const orgAdminEmail = process.env.SEED_ORG_ADMIN_EMAIL ?? 'admin@acmeworkforce.com'
const orgAdminPassword = process.env.SEED_ORG_ADMIN_PASSWORD ?? 'Admin@12345'
const employeePassword = process.env.SEED_EMPLOYEE_PASSWORD ?? 'Employee@12345'
const browser = await chromium.launch({ headless: true })
const results = []

async function run(name, fn) {
  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    await fn(page)
    results.push({ name, status: 'passed' })
  } catch (error) {
    results.push({ name, status: 'failed', error: String(error) })
    throw error
  } finally {
    await context.close()
  }
}

try {
  await run('landing_and_theme_toggle', async (page) => {
    await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle' })
    if (!page.url().includes('/auth/login')) {
      throw new Error('Default landing page did not redirect to /auth/login')
    }

    await page.getByRole('button', { name: /toggle color theme/i }).click()
    await page.getByRole('menuitem', { name: /dark/i }).click()
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark')
    await page.reload({ waitUntil: 'networkidle' })

    const theme = await page.evaluate(() => ({
      theme: localStorage.getItem('calrisal-theme'),
      resolved: document.documentElement.dataset.theme,
    }))

    if (theme.theme !== 'dark' || theme.resolved !== 'dark') {
      throw new Error('Theme preference did not persist as dark')
    }
  })

  await run('control_tower_login', async (page) => {
    await page.goto(`${baseUrl}/ct/login`, { waitUntil: 'networkidle' })
    await page.getByLabel('Control Tower email').fill(controlTowerEmail)
    await page.getByLabel('Password').fill(controlTowerPassword)
    await page.getByRole('button', { name: /enter control tower/i }).click()
    await page.waitForURL('**/ct/dashboard')
    await page.goto(`${baseUrl}/ct/organisations`, { waitUntil: 'networkidle' })
    await page.getByText('Organisation directory').first().waitFor()
  })

  await run('org_admin_login', async (page) => {
    await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'networkidle' })
    await page.getByLabel('Email address').fill(orgAdminEmail)
    await page.getByLabel('Password').fill(orgAdminPassword)
    await page.getByRole('button', { name: /^sign in$/i }).click()
    await page.waitForURL('**/org/dashboard')
    await page.goto(`${baseUrl}/org/employees`, { waitUntil: 'networkidle' })
    await page.getByText('Employee directory').first().waitFor()
  })

  await run('employee_login', async (page) => {
    await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'networkidle' })
    await page.getByLabel('Email address').fill('priya.sharma@acmeworkforce.com')
    await page.getByLabel('Password').fill(employeePassword)
    await page.getByRole('button', { name: /^sign in$/i }).click()
    await page.waitForURL('**/me/dashboard')
    await page.goto(`${baseUrl}/me/profile`, { waitUntil: 'networkidle' })
    await page.getByText('Government IDs').first().waitFor()
  })

  console.log(JSON.stringify(results, null, 2))
} finally {
  await browser.close()
}
