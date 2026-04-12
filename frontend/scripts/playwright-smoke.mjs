import { chromium } from 'playwright'

function requireEnv(name, message) {
  const value = process.env[name]
  if (!value) {
    throw new Error(message ?? `${name} must be set before running the smoke script.`)
  }
  return value
}

const baseUrl = process.env.APP_BASE_URL ?? 'http://127.0.0.1:8080'
const controlTowerEmail = process.env.CONTROL_TOWER_EMAIL ?? 'admin@clarisal.com'
const controlTowerPassword = requireEnv('CONTROL_TOWER_PASSWORD', 'CONTROL_TOWER_PASSWORD must be set before running the smoke script.')
const orgAdminEmail = process.env.SEED_ORG_ADMIN_EMAIL ?? 'admin@acmeworkforce.com'
const orgAdminPassword = requireEnv('SEED_ORG_ADMIN_PASSWORD', 'SEED_ORG_ADMIN_PASSWORD must be set before running the smoke script.')
const employeeEmail = process.env.SEED_PRIMARY_EMPLOYEE_EMAIL ?? 'rohan.mehta@acmeworkforce.com'
const employeePassword = requireEnv('SEED_EMPLOYEE_PASSWORD', 'SEED_EMPLOYEE_PASSWORD must be set before running the smoke script.')
const browser = await chromium.launch({ headless: true })
const results = []
const authViewportMatrix = [
  { width: 1440, height: 900 },
  { width: 1366, height: 768 },
  { width: 1280, height: 720 },
]

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

async function assertAuthPageFits(page, path, viewport) {
  await page.setViewportSize(viewport)
  await page.goto(`${baseUrl}${path}`, { waitUntil: 'networkidle' })

  const metrics = await page.evaluate(() => {
    const frame = document.querySelector('.auth-shell-frame')
    const submit = document.querySelector('button[type="submit"]')

    if (!frame) {
      throw new Error('Auth shell frame not found')
    }

    if (!submit) {
      throw new Error('Auth submit button not found')
    }

    const frameRect = frame.getBoundingClientRect()
    const submitRect = submit.getBoundingClientRect()
    const nestedScrollers = [...document.querySelectorAll('*')]
      .filter((element) => {
        const style = getComputedStyle(element)
        return ['auto', 'scroll'].includes(style.overflowY) && element.scrollHeight > element.clientHeight + 1
      })
      .map((element) => {
        const className = typeof element.className === 'string' ? element.className.trim() : ''
        return element.tagName.toLowerCase() + (className ? `.${className.replace(/\s+/g, '.')}` : '')
      })

    return {
      innerHeight: window.innerHeight,
      scrollHeight: document.documentElement.scrollHeight,
      frameTop: frameRect.top,
      frameBottom: frameRect.bottom,
      submitBottom: submitRect.bottom,
      nestedScrollers,
    }
  })

  if (metrics.scrollHeight > metrics.innerHeight + 1) {
    throw new Error(`Viewport overflow for ${path} at ${viewport.width}x${viewport.height}: ${JSON.stringify(metrics)}`)
  }

  if (metrics.frameTop < -1 || metrics.frameBottom > metrics.innerHeight + 1) {
    throw new Error(`Auth frame escaped viewport for ${path} at ${viewport.width}x${viewport.height}: ${JSON.stringify(metrics)}`)
  }

  if (metrics.submitBottom > metrics.innerHeight + 1) {
    throw new Error(`Submit button fell below viewport for ${path} at ${viewport.width}x${viewport.height}: ${JSON.stringify(metrics)}`)
  }

  if (metrics.nestedScrollers.length > 0) {
    throw new Error(`Nested scrollers found for ${path} at ${viewport.width}x${viewport.height}: ${metrics.nestedScrollers.join(', ')}`)
  }
}

try {
  await run('auth_login_no_scroll', async (page) => {
    await page.addInitScript(() => {
      localStorage.setItem('clarisal-theme', 'light')
    })

    for (const viewport of authViewportMatrix) {
      await assertAuthPageFits(page, '/auth/login', viewport)
      await assertAuthPageFits(page, '/ct/login', viewport)
    }
  })

  await run('light_theme_auth_surface', async (page) => {
    await page.addInitScript(() => {
      localStorage.setItem('clarisal-theme', 'light')
    })
    await page.goto(`${baseUrl}/ct/login`, { waitUntil: 'networkidle' })

    const styles = await page.evaluate(() => {
      const hero = document.querySelector('section.auth-hero-surface')
      const body = document.body

      if (!hero) {
        throw new Error('Auth hero surface not found')
      }

      return {
        theme: document.documentElement.dataset.theme,
        bodyBackground: getComputedStyle(body).backgroundImage,
        heroBackground: getComputedStyle(hero).backgroundImage,
        heroColor: getComputedStyle(hero).color,
      }
    })

    if (styles.theme !== 'light') {
      throw new Error(`Expected light theme, received ${styles.theme}`)
    }

    if (styles.bodyBackground === 'none' || styles.heroBackground === 'none') {
      throw new Error(`Expected gradient backgrounds in light theme, received ${JSON.stringify(styles)}`)
    }
  })

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
      theme: localStorage.getItem('clarisal-theme'),
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
    await page.getByRole('heading', { name: 'Organisations' }).waitFor()
  })

  await run('org_admin_login', async (page) => {
    await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'networkidle' })
    await page.getByLabel('Email address').fill(orgAdminEmail)
    await page.getByLabel('Password').fill(orgAdminPassword)
    await page.getByRole('button', { name: /^sign in$/i }).click()
    await page.waitForFunction(() => window.location.pathname.startsWith('/org/'))

    if (page.url().includes('/org/setup')) {
      await page.getByRole('heading', { name: /set up this organisation workspace/i }).waitFor()
    } else {
      await page.waitForURL('**/org/dashboard')
      await page.goto(`${baseUrl}/org/employees`, { waitUntil: 'networkidle' })
      await page.getByText('Employee directory').first().waitFor()
    }
  })

  await run('employee_login', async (page) => {
    await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'networkidle' })
    await page.getByLabel('Email address').fill(employeeEmail)
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
