import { Activity } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { formatDateTime, startCase } from '@/lib/format'
import type { AuditLogEntry } from '@/types/audit'

interface AuditTimelineProps {
  entries?: AuditLogEntry[]
  emptyTitle?: string
  emptyDescription?: string
  onEntryClick?: (entry: AuditLogEntry) => void
  activeEntryId?: string | null
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
  onEntryClick,
  activeEntryId,
}: AuditTimelineProps) {
  if (!entries || entries.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} icon={Activity} />
  }

  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <button
          key={entry.id}
          type="button"
          onClick={() => onEntryClick?.(entry)}
          className={`surface-muted w-full rounded-[20px] px-4 py-4 text-left ${
            activeEntryId === entry.id ? 'ring-2 ring-[hsl(var(--brand)/0.35)]' : ''
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-medium text-[hsl(var(--foreground-strong))]">{startCase(entry.action.replace(/\./g, ' '))}</p>
            <p className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">{formatDateTime(entry.created_at)}</p>
          </div>
          <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
            {entry.actor_name || entry.actor_email || 'System action'}
            {entry.target_label ? ` • ${entry.target_label}` : entry.target_type ? ` • ${startCase(entry.target_type)}` : ''}
          </p>
          {(entry.payload_summary || Object.keys(entry.payload || {}).length > 0) ? (
            <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
              {entry.payload_summary || describePayload(entry.payload)}
            </p>
          ) : null}
        </button>
      ))}
    </div>
  )
}
