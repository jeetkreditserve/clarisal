import type { ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ArrowUpRight, Layers3, ShieldCheck, Sparkles, UsersRound } from 'lucide-react'
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
    headline: 'Run people operations with calm precision and premium clarity.',
    body: 'Organisation admins and employees enter through one elegant workspace. Setup, self-service, and document flows stay fast, legible, and secure.',
    metrics: [
      { label: 'Profile completion', value: '92%', icon: Sparkles },
      { label: 'Document verification', value: 'Live', icon: ShieldCheck },
      { label: 'Employee portals', value: 'Multi-org', icon: UsersRound },
    ],
  },
  'control-tower': {
    eyebrow: 'Platform operations',
    headline: 'Control Tower is the command surface for tenant activation and platform oversight.',
    body: 'Track licences, payment readiness, onboarding state, and admin access without losing the clean enterprise feel of the product shell.',
    metrics: [
      { label: 'Org activation', value: 'Stateful', icon: Layers3 },
      { label: 'Licence control', value: 'Tracked', icon: ShieldCheck },
      { label: 'Admin onboarding', value: 'Secure', icon: ArrowUpRight },
    ],
  },
  setup: {
    eyebrow: 'Secure setup',
    headline: 'High-trust identity setup, refined for onboarding and recovery journeys.',
    body: 'Invites, password setup, and reset flows should feel premium, intentional, and unmistakably secure.',
    metrics: [
      { label: 'Access links', value: 'Expiring', icon: ShieldCheck },
      { label: 'Recovery flow', value: 'Guided', icon: Sparkles },
      { label: 'Session handoff', value: 'Seamless', icon: ArrowUpRight },
    ],
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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-6 sm:px-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_0%_0%,hsla(var(--brand),0.18),transparent_28%),radial-gradient(circle_at_100%_0%,hsla(var(--accent),0.14),transparent_24%),radial-gradient(circle_at_100%_100%,hsla(var(--brand),0.1),transparent_22%)]" />
      <motion.div
        aria-hidden
        initial={reduceMotion ? false : { opacity: 0, scale: 0.92 }}
        animate={reduceMotion ? undefined : { opacity: 1, scale: 1 }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
        className="pointer-events-none absolute left-[8%] top-[10%] h-56 w-56 rounded-full bg-[radial-gradient(circle,hsla(var(--brand),0.28),transparent_68%)] blur-3xl"
      />
      <motion.div
        aria-hidden
        initial={reduceMotion ? false : { opacity: 0, scale: 0.92 }}
        animate={reduceMotion ? undefined : { opacity: 1, scale: 1 }}
        transition={{ duration: 0.55, ease: 'easeOut', delay: 0.08 }}
        className="pointer-events-none absolute bottom-[8%] right-[8%] h-64 w-64 rounded-full bg-[radial-gradient(circle,hsla(var(--accent),0.26),transparent_70%)] blur-3xl"
      />

      <div className="absolute right-5 top-5 z-20">
        <ThemeToggle />
      </div>

      <div className="grid w-full max-w-7xl overflow-hidden rounded-[40px] border border-[hsla(var(--border),0.82)] bg-[hsla(var(--surface),0.72)] shadow-[var(--shadow-card)] backdrop-blur-[20px] lg:grid-cols-[minmax(0,1.08fr)_minmax(430px,0.92fr)]">
        <section className="sidebar-surface relative overflow-hidden px-8 py-10 sm:px-10 lg:px-12">
          <div className="absolute inset-0 bg-[linear-gradient(145deg,transparent,hsla(var(--brand),0.08))]" />
          <div className="relative flex h-full flex-col justify-between gap-10">
            <div className="space-y-8">
              <motion.div
                initial={reduceMotion ? false : { opacity: 0, y: 20 }}
                animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                transition={{ duration: 0.36, ease: 'easeOut' }}
              >
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[hsl(var(--sidebar-muted))]">Calrisal</p>
                <p className="mt-4 text-xs font-semibold uppercase tracking-[0.26em] text-[hsla(var(--sidebar-foreground),0.72)]">
                  {content.eyebrow}
                </p>
                <h1 className="mt-4 max-w-xl text-balance text-4xl font-semibold tracking-tight text-[hsl(var(--sidebar-foreground))] sm:text-[3.15rem]">
                  {content.headline}
                </h1>
                <p className="mt-5 max-w-2xl text-sm leading-7 text-[hsl(var(--sidebar-muted))]">
                  {content.body}
                </p>
              </motion.div>

              <div className="grid gap-4 md:grid-cols-3">
                {content.metrics.map(({ label, value, icon: Icon }, index) => (
                  <motion.div
                    key={label}
                    initial={reduceMotion ? false : { opacity: 0, y: 24 }}
                    animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                    transition={{ duration: 0.28, delay: 0.08 + index * 0.06, ease: 'easeOut' }}
                    className="rounded-[28px] border border-white/10 bg-white/6 p-4 backdrop-blur-md"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="rounded-2xl bg-white/10 p-3 text-[hsl(var(--sidebar-foreground))]">
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="font-mono text-xs uppercase tracking-[0.18em] text-[hsl(var(--sidebar-muted))]">
                        {value}
                      </span>
                    </div>
                    <p className="mt-4 text-sm font-medium text-[hsl(var(--sidebar-foreground))]">{label}</p>
                  </motion.div>
                ))}
              </div>

              <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
                <motion.div
                  initial={reduceMotion ? false : { opacity: 0, y: 24 }}
                  animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                  transition={{ duration: 0.34, delay: 0.26, ease: 'easeOut' }}
                  className="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.04))] p-5 backdrop-blur-md"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-[hsl(var(--sidebar-foreground))]">Platform preview</p>
                    <span className="status-pill border-white/10 bg-white/10 text-[hsl(var(--sidebar-foreground))]">Live context</span>
                  </div>
                  <div className="mt-5 grid gap-3">
                    <div className="rounded-[24px] border border-white/10 bg-white/8 p-4">
                      <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-[hsl(var(--sidebar-muted))]">
                        <span>Activation state</span>
                        <span>Paid</span>
                      </div>
                      <div className="mt-3 h-2 rounded-full bg-white/10">
                        <motion.div
                          initial={reduceMotion ? false : { width: 0 }}
                          animate={reduceMotion ? undefined : { width: '74%' }}
                          transition={{ duration: 0.7, delay: 0.45, ease: 'easeOut' }}
                          className="h-2 rounded-full bg-[linear-gradient(90deg,#60A5FA,#F59E0B)]"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      {['Lifecycle', 'Documents', 'Licences', 'Identity'].map((item, index) => (
                        <motion.div
                          key={item}
                          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                          animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                          transition={{ duration: 0.22, delay: 0.38 + index * 0.04, ease: 'easeOut' }}
                          className="rounded-[22px] border border-white/10 bg-black/10 px-3 py-4"
                        >
                          <p className="text-xs uppercase tracking-[0.18em] text-[hsl(var(--sidebar-muted))]">{item}</p>
                          <p className="mt-2 text-sm font-semibold text-[hsl(var(--sidebar-foreground))]">
                            {index % 2 === 0 ? 'Structured' : 'Verified'}
                          </p>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                </motion.div>

                <motion.div
                  initial={reduceMotion ? false : { opacity: 0, x: 24 }}
                  animate={reduceMotion ? undefined : { opacity: 1, x: 0 }}
                  transition={{ duration: 0.38, delay: 0.18, ease: 'easeOut' }}
                  className="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 backdrop-blur-md"
                >
                  <p className="text-sm font-semibold text-[hsl(var(--sidebar-foreground))]">Design principles</p>
                  <div className="mt-5 space-y-4">
                    {[
                      'Trust-forward hierarchy with clear commercial and operational status.',
                      'Data-dense layouts that still preserve calm whitespace and scan rhythm.',
                      'Motion used deliberately for orientation, not spectacle, outside auth.',
                    ].map((item) => (
                      <div key={item} className="flex gap-3">
                        <span className="mt-1 h-2.5 w-2.5 rounded-full bg-[hsl(var(--accent))]" />
                        <p className="text-sm leading-6 text-[hsl(var(--sidebar-muted))]">{item}</p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </div>
            </div>

            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 18 }}
              animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              transition={{ duration: 0.34, delay: 0.4, ease: 'easeOut' }}
              className="rounded-[30px] border border-white/10 bg-white/6 p-5 text-sm leading-6 text-[hsl(var(--sidebar-muted))]"
            >
              Control Tower activates tenants. Organisation admins structure the workforce. Employees complete verified self-service. One product language spans the whole platform.
            </motion.div>
          </div>
        </section>

        <section className="relative px-6 py-8 sm:px-10 sm:py-10">
          <div className="mx-auto flex h-full w-full max-w-md flex-col justify-center">
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 18 }}
              animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
              transition={{ duration: 0.28, ease: 'easeOut' }}
              className="mb-8"
            >
              <p className="eyebrow">Secure access</p>
              <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight text-[hsl(var(--foreground-strong))] sm:text-[2.2rem]">
                {title}
              </h2>
              <p className="mt-3 text-sm leading-7 text-[hsl(var(--muted-foreground))]">{description}</p>
            </motion.div>

            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={title}
                initial={reduceMotion ? false : { opacity: 0, y: 18 }}
                animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, y: -10 }}
                transition={{ duration: 0.22, ease: 'easeOut' }}
              >
                {children}
              </motion.div>
            </AnimatePresence>

            {footer ? <div className={cn('mt-6 text-sm text-[hsl(var(--muted-foreground))]')}>{footer}</div> : null}
          </div>
        </section>
      </div>
    </div>
  )
}
