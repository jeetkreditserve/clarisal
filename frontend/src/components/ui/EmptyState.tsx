import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  title: string
  description: string
  action?: React.ReactNode
  icon?: LucideIcon
}

export function EmptyState({ title, description, action, icon: Icon }: EmptyStateProps) {
  return (
    <div className="surface-card flex min-h-64 flex-col items-center justify-center rounded-[28px] px-6 py-12 text-center">
      {Icon ? (
        <div className="mb-5 rounded-2xl bg-cyan-50 p-4 text-cyan-800 ring-1 ring-cyan-100">
          <Icon className="h-6 w-6" />
        </div>
      ) : null}
      <h3 className="text-lg font-semibold text-slate-950">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p>
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  )
}
