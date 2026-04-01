import { Activity } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { formatDateTime, startCase } from '@/lib/format'
import type { AuditLogEntry } from '@/types/audit'

interface AuditTimelineProps {
  entries?: AuditLogEntry[]
  emptyTitle?: string
  emptyDescription?: string
}

function describePayload(payload: Record<string, unknown>) {
  return Object.entries(payload)
    .slice(0, 3)
    .map(([key, value]) => `${startCase(key)}: ${String(value)}`)
    .join(' • ')
}

export function AuditTimeline({
  entries,
  emptyTitle = 'No audit activity yet',
  emptyDescription = 'Audit events will appear here as users take actions in this workspace.',
}: AuditTimelineProps) {
  if (!entries || entries.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} icon={Activity} />
  }

  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <div key={entry.id} className="surface-muted rounded-[20px] px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-medium text-[hsl(var(--foreground-strong))]">{startCase(entry.action.replace(/\./g, ' '))}</p>
            <p className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">{formatDateTime(entry.created_at)}</p>
          </div>
          <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
            {entry.actor_email || 'System action'}
            {entry.target_type ? ` • ${startCase(entry.target_type)}` : ''}
          </p>
          {Object.keys(entry.payload || {}).length > 0 ? (
            <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{describePayload(entry.payload)}</p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
