import { cn } from '@/lib/utils'

type StatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

const toneClasses: Record<StatusTone, string> = {
  neutral: 'bg-[hsl(var(--surface-subtle))] text-[hsl(var(--muted-foreground-strong))] border-[hsl(var(--border)_/_0.92)]',
  info: 'bg-[hsl(var(--info-soft))] text-[hsl(var(--info))] border-[hsl(var(--info)_/_0.2)]',
  success: 'bg-[hsl(var(--success-soft))] text-[hsl(var(--success))] border-[hsl(var(--success)_/_0.2)]',
  warning: 'bg-[hsl(var(--warning-soft))] text-[hsl(var(--warning))] border-[hsl(var(--warning)_/_0.2)]',
  danger: 'bg-[hsl(var(--destructive-soft))] text-[hsl(var(--destructive))] border-[hsl(var(--destructive)_/_0.2)]',
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
        'status-pill',
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  )
}
