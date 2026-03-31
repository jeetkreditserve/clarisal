import type { LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'

interface EmptyStateProps {
  title: string
  description: string
  action?: React.ReactNode
  icon?: LucideIcon
}

export function EmptyState({ title, description, action, icon: Icon }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
      className="empty-state-shell"
    >
      {Icon ? (
        <div className="mb-5 rounded-[24px] bg-[hsl(var(--brand-soft))] p-4 text-[hsl(var(--brand))] ring-1 ring-[hsla(var(--brand),0.14)]">
          <Icon className="h-6 w-6" />
        </div>
      ) : null}
      <h3 className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-[hsl(var(--muted-foreground))]">{description}</p>
      {action ? <div className="mt-6">{action}</div> : null}
    </motion.div>
  )
}
