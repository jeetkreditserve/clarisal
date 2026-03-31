import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

type MetricTone = 'primary' | 'success' | 'warning' | 'danger' | 'neutral' | 'info'

const toneClasses: Record<MetricTone, string> = {
  primary: 'bg-cyan-100 text-cyan-900 ring-cyan-200',
  info: 'bg-sky-100 text-sky-900 ring-sky-200',
  success: 'bg-emerald-100 text-emerald-900 ring-emerald-200',
  warning: 'bg-amber-100 text-amber-900 ring-amber-200',
  danger: 'bg-rose-100 text-rose-900 ring-rose-200',
  neutral: 'bg-slate-100 text-slate-800 ring-slate-200',
}

interface MetricCardProps {
  title: string
  value: string | number
  hint?: string
  tone?: MetricTone
  icon?: LucideIcon
}

export function MetricCard({ title, value, hint, tone = 'primary', icon: Icon }: MetricCardProps) {
  return (
    <div className="surface-card rounded-[28px] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
        </div>
        {Icon ? (
          <div className={cn('rounded-2xl p-3 ring-1', toneClasses[tone])}>
            <Icon className="h-5 w-5" />
          </div>
        ) : null}
      </div>
      {hint ? <p className="mt-3 text-sm text-slate-500">{hint}</p> : null}
    </div>
  )
}
