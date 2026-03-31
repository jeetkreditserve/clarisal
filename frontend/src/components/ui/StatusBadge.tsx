import { cn } from '@/lib/utils'

type StatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

const toneClasses: Record<StatusTone, string> = {
  neutral: 'bg-slate-100 text-slate-700 border-slate-200',
  info: 'bg-sky-100 text-sky-800 border-sky-200',
  success: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  warning: 'bg-amber-100 text-amber-900 border-amber-200',
  danger: 'bg-rose-100 text-rose-800 border-rose-200',
}

interface StatusBadgeProps {
  children: React.ReactNode
  tone?: StatusTone
  className?: string
}

export function StatusBadge({ children, tone = 'neutral', className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold tracking-wide',
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  )
}
