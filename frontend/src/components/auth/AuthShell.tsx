import type { ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { cn } from '@/lib/utils'

interface AuthShellProps {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
  variant?: 'workforce' | 'control-tower' | 'setup'
}

const contentByVariant = {
  workforce: {
    eyebrow: 'Workforce access',
    headline: 'Organisation admins and employees sign in here.',
    body: 'Use this access point for people operations inside the organisations you belong to, or to complete your own employee self-service tasks.',
    chips: ['Org admin', 'Employee self-service'],
    panelTitle: 'Use this login for',
    panelItems: [
      'Managing employees, departments, and office locations inside your organisations.',
      'Completing employee profile, identity, education, and document tasks.',
      'Entering the correct workforce workspace when you belong to multiple organisations.',
    ],
    noteLabel: 'Separate access',
    noteTitle: 'Platform operations use a different login.',
    noteBody: 'If you manage organisation activation, licences, payment confirmation, or Django admin, switch to Control Tower.',
  },
  'control-tower': {
    eyebrow: 'Platform operations',
    headline: 'Control Tower access is reserved for Calrisal operators.',
    body: 'Use this sign-in for tenant provisioning, licence management, organisation activation, and platform-level administration.',
    chips: ['Platform operator', 'Django admin'],
    panelTitle: 'Use this login for',
    panelItems: [
      'Creating and activating organisations after commercial confirmation is complete.',
      'Managing licence allocation, onboarding state, and primary admin invitation flows.',
      'Accessing platform-only controls that must stay separate from workforce accounts.',
    ],
    noteLabel: 'Boundary',
    noteTitle: 'This is not the employee or org-admin portal.',
    noteBody: 'Organisation admins and employees should use the workforce sign-in so tenant routing and data boundaries stay correct.',
  },
  setup: {
    eyebrow: 'Secure setup',
    headline: 'Secure setup and recovery for invited access.',
    body: 'Use these flows to accept an invite, set a password, or recover access through a short-lived secure link.',
    chips: ['Invite acceptance', 'Password reset'],
    panelTitle: 'Security checks',
    panelItems: [
      'Links are time-limited and cannot be reused after completion.',
      'Passwords are set directly in the browser and are never sent over email.',
      'Successful setup returns you to the correct workspace for your access type.',
    ],
    noteLabel: 'If you already have access',
    noteTitle: 'Use the correct login instead of a setup link.',
    noteBody: 'Workforce users should sign in from the default login page, while Calrisal operators should use Control Tower.',
  },
} as const

export function AuthShell({
  title,
  description,
  children,
  footer,
  variant = 'setup',
}: AuthShellProps) {
  const reduceMotion = useReducedMotion()
  const content = contentByVariant[variant]

  return (
    <div className="auth-shell-root relative flex min-h-[100svh] items-center justify-center overflow-hidden px-4 py-4 sm:px-6 sm:py-5">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_0%_0%,hsl(var(--brand)_/_0.18),transparent_28%),radial-gradient(circle_at_100%_0%,hsl(var(--accent)_/_0.14),transparent_24%),radial-gradient(circle_at_100%_100%,hsl(var(--brand)_/_0.1),transparent_22%)]" />
      <motion.div
        aria-hidden
        initial={reduceMotion ? false : { opacity: 0, scale: 0.92 }}
        animate={reduceMotion ? undefined : { opacity: 1, scale: 1 }}
        transition={{ duration: 0.38, ease: 'easeOut' }}
        className="pointer-events-none absolute left-[8%] top-[10%] h-48 w-48 rounded-full bg-[radial-gradient(circle,hsl(var(--brand)_/_0.26),transparent_68%)] blur-3xl"
      />
      <motion.div
        aria-hidden
        initial={reduceMotion ? false : { opacity: 0, scale: 0.92 }}
        animate={reduceMotion ? undefined : { opacity: 1, scale: 1 }}
        transition={{ duration: 0.42, ease: 'easeOut', delay: 0.06 }}
        className="pointer-events-none absolute bottom-[8%] right-[8%] h-56 w-56 rounded-full bg-[radial-gradient(circle,hsl(var(--accent)_/_0.24),transparent_70%)] blur-3xl"
      />

      <div className="absolute right-4 top-4 z-20 sm:right-5 sm:top-5">
        <ThemeToggle />
      </div>

      <div className="auth-shell-frame grid w-full overflow-hidden rounded-[36px] border border-[hsl(var(--border)_/_0.82)] bg-[hsl(var(--surface)_/_0.72)] shadow-[var(--shadow-card)] backdrop-blur-[20px] lg:grid-cols-[minmax(0,0.96fr)_minmax(380px,0.74fr)]">
        <section className="auth-shell-hero auth-hero-surface relative overflow-hidden px-6 py-6 sm:px-8 sm:py-7 lg:px-9 lg:py-8">
          <div className="absolute inset-0 bg-[linear-gradient(145deg,transparent,hsl(var(--brand)_/_0.08))]" />
          <div className="auth-shell-hero-stack relative flex h-full flex-col justify-center gap-6">
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 18 }}
              animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              transition={{ duration: 0.28, ease: 'easeOut' }}
              className="space-y-4"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[hsl(var(--auth-hero-muted))]">Calrisal</p>
              <div className="flex flex-wrap gap-2">
                {content.chips.map((chip) => (
                  <span key={chip} className="auth-hero-chip rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]">
                    {chip}
                  </span>
                ))}
              </div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[hsl(var(--auth-hero-foreground)_/_0.72)]">
                {content.eyebrow}
              </p>
              <h1 className="auth-shell-heading max-w-2xl text-[hsl(var(--auth-hero-foreground))]">
                {content.headline}
              </h1>
              <p className="auth-shell-copy max-w-xl text-[hsl(var(--auth-hero-muted))]">
                {content.body}
              </p>
            </motion.div>

            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 18 }}
              animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              transition={{ duration: 0.24, delay: 0.08, ease: 'easeOut' }}
              className="auth-hero-panel auth-shell-support rounded-[28px] p-5"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[hsl(var(--auth-hero-foreground)_/_0.7)]">
                {content.panelTitle}
              </p>
              <ul className="auth-shell-list mt-4">
                {content.panelItems.map((item) => (
                  <li key={item} className="auth-shell-list-item text-sm leading-6 text-[hsl(var(--auth-hero-muted))]">
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>

            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 16 }}
              animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              transition={{ duration: 0.24, delay: 0.12, ease: 'easeOut' }}
              className="auth-shell-hero-secondary auth-hero-panel-soft rounded-[26px] p-4"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[hsl(var(--auth-hero-foreground)_/_0.7)]">
                {content.noteLabel}
              </p>
              <p className="mt-2 text-sm font-semibold text-[hsl(var(--auth-hero-foreground))]">
                {content.noteTitle}
              </p>
              <p className="mt-2 text-sm leading-6 text-[hsl(var(--auth-hero-muted))]">
                {content.noteBody}
              </p>
            </motion.div>
          </div>
        </section>

        <section className="auth-shell-content relative px-6 py-6 sm:px-8 sm:py-7 lg:px-9 lg:py-8">
          <div className="mx-auto flex h-full w-full max-w-[26rem] flex-col justify-center">
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 18 }}
              animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              transition={{ duration: 0.24, ease: 'easeOut' }}
              className="mb-6"
            >
              <p className="eyebrow">Secure access</p>
              <h2 className="mt-3 text-balance text-[1.95rem] font-semibold tracking-tight text-[hsl(var(--foreground-strong))] sm:text-[2.2rem]">
                {title}
              </h2>
              <p className="mt-3 text-sm leading-7 text-[hsl(var(--muted-foreground))]">{description}</p>
            </motion.div>

            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={title}
                initial={reduceMotion ? false : { opacity: 0, y: 16 }}
                animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, y: -8 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
              >
                {children}
              </motion.div>
            </AnimatePresence>

            {footer ? <div className={cn('mt-5 text-sm text-[hsl(var(--muted-foreground))]')}>{footer}</div> : null}
          </div>
        </section>
      </div>
    </div>
  )
}
