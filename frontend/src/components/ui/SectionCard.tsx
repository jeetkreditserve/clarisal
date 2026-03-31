import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface SectionCardProps {
  title: string
  description?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export function SectionCard({ title, description, action, children, className }: SectionCardProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: 'easeOut' }}
      className={cn('surface-card rounded-[30px] p-6', className)}
    >
      <div className="flex flex-col gap-4 border-b border-[hsl(var(--border)_/_0.84)] pb-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="section-title">{title}</h2>
          {description ? <p className="section-copy mt-1">{description}</p> : null}
        </div>
        {action ? <div className="flex items-center gap-3">{action}</div> : null}
      </div>
      <div className="pt-5">{children}</div>
    </motion.section>
  )
}
