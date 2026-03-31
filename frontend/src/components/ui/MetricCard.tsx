import type { LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

type MetricTone = 'primary' | 'success' | 'warning' | 'danger' | 'neutral' | 'info'

const toneClasses: Record<MetricTone, string> = {
  primary: 'bg-[hsl(var(--brand-soft))] text-[hsl(var(--brand))] ring-[hsl(var(--brand)_/_0.18)]',
  info: 'bg-[hsl(var(--info-soft))] text-[hsl(var(--info))] ring-[hsl(var(--info)_/_0.2)]',
  success: 'bg-[hsl(var(--success-soft))] text-[hsl(var(--success))] ring-[hsl(var(--success)_/_0.2)]',
  warning: 'bg-[hsl(var(--warning-soft))] text-[hsl(var(--warning))] ring-[hsl(var(--warning)_/_0.2)]',
  danger: 'bg-[hsl(var(--destructive-soft))] text-[hsl(var(--destructive))] ring-[hsl(var(--destructive)_/_0.2)]',
  neutral: 'bg-[hsl(var(--surface-subtle))] text-[hsl(var(--foreground))] ring-[hsl(var(--border)_/_0.8)]',
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
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
      whileHover={{ y: -2 }}
      className="surface-card rounded-[30px] p-5"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">{title}</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">{value}</p>
        </div>
        {Icon ? (
          <div className={cn('rounded-[20px] p-3 ring-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.16)]', toneClasses[tone])}>
            <Icon className="h-5 w-5" />
          </div>
        ) : null}
      </div>
      {hint ? <p className="mt-3 text-sm leading-6 text-[hsl(var(--muted-foreground))]">{hint}</p> : null}
    </motion.div>
  )
}
