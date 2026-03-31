import type { ReactNode } from 'react'
import { motion } from 'motion/react'

interface PageHeaderProps {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
      className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"
    >
      <div className="space-y-2">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <div>
          <h1 className="text-balance text-3xl font-semibold tracking-tight text-[hsl(var(--foreground-strong))] md:text-[2.1rem]">{title}</h1>
          {description ? <p className="mt-2 max-w-3xl text-sm leading-7 text-[hsl(var(--muted-foreground))]">{description}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </motion.div>
  )
}
