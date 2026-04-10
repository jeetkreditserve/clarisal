import { TrendingUp, ArrowRightLeft } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate, startCase } from '@/lib/format'
import type { CareerTimelineEntry } from '@/lib/api/org-admin'

interface CareerTimelineProps {
  entries?: CareerTimelineEntry[]
  emptyTitle?: string
  emptyDescription?: string
}

function getStatusTone(status: string): 'neutral' | 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'EFFECTIVE': return 'success'
    case 'APPROVED': return 'success'
    case 'PENDING': return 'warning'
    case 'REJECTED': return 'danger'
    case 'CANCELLED': return 'neutral'
    case 'DRAFT': return 'neutral'
    default: return 'neutral'
  }
}

function EventCard({ entry }: { entry: CareerTimelineEntry }) {
  const isPromotion = entry.type === 'PROMOTION'
  const Icon = isPromotion ? TrendingUp : ArrowRightLeft
  const iconColor = isPromotion ? 'text-blue-600' : 'text-purple-600'

  return (
    <div className="surface-muted rounded-[20px] px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${iconColor}`} />
          <span className="font-medium text-[hsl(var(--foreground-strong))]">
            {isPromotion ? 'Promotion' : 'Transfer'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={getStatusTone(entry.status)}>{startCase(entry.status)}</StatusBadge>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            {formatDate(entry.date)}
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-1">
        {isPromotion ? (
          <>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              <span className="text-[hsl(var(--foreground-subtle))]">Designation: </span>
              {(entry.from_designation || '—')} → {(entry.to_designation || '—')}
            </p>
            {entry.has_compensation_change && (
              <p className="text-sm font-medium text-[hsl(var(--success))]">
                Compensation revision included
              </p>
            )}
          </>
        ) : (
          <>
            {entry.from_department && entry.to_department && (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                <span className="text-[hsl(var(--foreground-subtle))]">Department: </span>
                {entry.from_department} → {entry.to_department}
              </p>
            )}
            {entry.from_location && entry.to_location && (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                <span className="text-[hsl(var(--foreground-subtle))]">Location: </span>
                {entry.from_location} → {entry.to_location}
              </p>
            )}
            {entry.from_designation && entry.to_designation && (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                <span className="text-[hsl(var(--foreground-subtle))]">Designation: </span>
                {entry.from_designation} → {entry.to_designation}
              </p>
            )}
          </>
        )}
        {entry.reason && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            <span className="text-[hsl(var(--foreground-subtle))]">Reason: </span>
            {entry.reason}
          </p>
        )}
        {entry.approved_by && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            <span className="text-[hsl(var(--foreground-subtle))]">Approved by: </span>
            {entry.approved_by}
          </p>
        )}
      </div>
    </div>
  )
}

export function CareerTimeline({
  entries,
  emptyTitle = 'No career events recorded',
  emptyDescription = 'Promotions and transfers will appear here as they happen.',
}: CareerTimelineProps) {
  if (!entries || entries.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <EventCard key={entry.id} entry={entry} />
      ))}
    </div>
  )
}
