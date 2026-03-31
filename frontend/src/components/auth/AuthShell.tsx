import type { ReactNode } from 'react'
import { ShieldCheck, Sparkles, Users } from 'lucide-react'

interface AuthShellProps {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}

export function AuthShell({ title, description, children, footer }: AuthShellProps) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-8 sm:px-6">
      <div className="surface-card grid w-full max-w-6xl overflow-hidden rounded-[36px] lg:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)]">
        <section className="relative overflow-hidden bg-[linear-gradient(160deg,#081423_0%,#0d2234_48%,#11415d_100%)] px-8 py-10 text-white sm:px-10 lg:px-12">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(103,232,249,0.2),transparent_24%),radial-gradient(circle_at_bottom_left,rgba(125,211,252,0.14),transparent_28%)]" />
          <div className="relative flex h-full flex-col justify-between gap-10">
            <div className="space-y-8">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200">Calrisal</p>
                <h1 className="mt-4 max-w-lg text-4xl font-semibold tracking-tight">Employee and payroll operations with deliberate control.</h1>
                <p className="mt-4 max-w-xl text-sm leading-7 text-slate-300">
                  Built for multi-organisation onboarding, controlled licence allocation, employee self-service,
                  and a clean path into payroll expansion.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                {[
                  { icon: ShieldCheck, label: 'Session security' },
                  { icon: Users, label: 'Role-based access' },
                  { icon: Sparkles, label: 'Premium onboarding UX' },
                ].map(({ icon: Icon, label }) => (
                  <div key={label} className="rounded-[24px] border border-white/10 bg-white/7 p-4 backdrop-blur-sm">
                    <Icon className="h-5 w-5 text-cyan-200" />
                    <p className="mt-4 text-sm font-medium text-slate-100">{label}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-[28px] border border-cyan-200/10 bg-white/6 p-5 text-sm leading-6 text-slate-300">
              Control Tower handles billing activation and tenant readiness. Organisation Admins manage structure and
              workforce records. Employees complete their own verified profile.
            </div>
          </div>
        </section>

        <section className="bg-[linear-gradient(180deg,rgba(248,250,252,0.94),rgba(255,255,255,0.98))] px-6 py-8 sm:px-10 sm:py-10">
          <div className="mx-auto flex h-full w-full max-w-md flex-col justify-center">
            <div className="mb-8">
              <p className="eyebrow">Secure access</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-500">{description}</p>
            </div>
            {children}
            {footer ? <div className="mt-6 text-sm text-slate-500">{footer}</div> : null}
          </div>
        </section>
      </div>
    </div>
  )
}
