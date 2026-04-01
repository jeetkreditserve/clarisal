import { useMemo, useState } from 'react'

import { AppDialog } from '@/components/ui/AppDialog'
import { AuditTimeline } from '@/components/ui/AuditTimeline'
import { AppSelect } from '@/components/ui/AppSelect'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useOrgAuditLogs } from '@/hooks/useOrgAdmin'
import { formatDateTime, startCase } from '@/lib/format'
import type { AuditLogEntry } from '@/types/audit'

function buildAuditCsv(entries: AuditLogEntry[]) {
  const rows = [
    ['Timestamp', 'Actor', 'Module', 'Action', 'Target', 'Summary'],
    ...entries.map((entry) => [
      entry.created_at,
      entry.actor_name || entry.actor_email || 'System',
      entry.module,
      entry.action,
      entry.target_label || entry.target_type || '',
      entry.payload_summary || '',
    ]),
  ]

  return rows
    .map((row) => row.map((value) => `"${String(value).split('"').join('""')}"`).join(','))
    .join('\n')
}

export function OrgAuditPage() {
  const [search, setSearch] = useState('')
  const [moduleFilter, setModuleFilter] = useState('')
  const [targetTypeFilter, setTargetTypeFilter] = useState('')
  const [actorFilter, setActorFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null)
  const { data, isLoading } = useOrgAuditLogs({
    search: search || undefined,
    module: moduleFilter || undefined,
    target_type: targetTypeFilter || undefined,
    actor: actorFilter || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
  })

  const entries = useMemo(() => data?.results ?? [], [data])
  const moduleOptions = useMemo(
    () => [
      { value: '', label: 'All modules' },
      ...Array.from(new Set(entries.map((entry) => entry.module))).map((module) => ({
        value: module,
        label: startCase(module),
      })),
    ],
    [entries],
  )
  const targetTypeOptions = useMemo(
    () => [
      { value: '', label: 'All targets' },
      ...Array.from(new Set(entries.map((entry) => entry.target_type).filter(Boolean) as string[])).map((targetType) => ({
        value: targetType,
        label: startCase(targetType),
      })),
    ],
    [entries],
  )

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={8} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Audit"
        title="Audit explorer"
        description="Search, filter, inspect, and export organisation-level activity across configuration, invitations, profile updates, and operational events."
        actions={
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              const blob = new Blob([buildAuditCsv(entries)], { type: 'text/csv;charset=utf-8;' })
              const url = URL.createObjectURL(blob)
              const link = document.createElement('a')
              link.href = url
              link.download = `clarisal-audit-${new Date().toISOString().slice(0, 10)}.csv`
              link.click()
              URL.revokeObjectURL(url)
            }}
          >
            Export current page
          </button>
        }
      />

      <SectionCard title="Filters" description="Search by actor, module, target, or time window to isolate the event you care about.">
        <div className="grid gap-4 xl:grid-cols-3">
          <div>
            <label className="field-label" htmlFor="audit-search">
              Search
            </label>
            <input
              id="audit-search"
              className="field-input"
              placeholder="Search action, actor, or target"
              value={search}
              onChange={(event) => {
                setPage(1)
                setSearch(event.target.value)
              }}
            />
          </div>
          <div>
            <label className="field-label">Module</label>
            <AppSelect
              value={moduleFilter}
              onValueChange={(value) => {
                setPage(1)
                setModuleFilter(value)
              }}
              options={moduleOptions}
            />
          </div>
          <div>
            <label className="field-label">Target type</label>
            <AppSelect
              value={targetTypeFilter}
              onValueChange={(value) => {
                setPage(1)
                setTargetTypeFilter(value)
              }}
              options={targetTypeOptions}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="audit-actor">
              Actor
            </label>
            <input
              id="audit-actor"
              className="field-input"
              placeholder="Filter by actor"
              value={actorFilter}
              onChange={(event) => {
                setPage(1)
                setActorFilter(event.target.value)
              }}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="audit-date-from">
              From date
            </label>
            <input
              id="audit-date-from"
              type="date"
              className="field-input"
              value={dateFrom}
              onChange={(event) => {
                setPage(1)
                setDateFrom(event.target.value)
              }}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="audit-date-to">
              To date
            </label>
            <input
              id="audit-date-to"
              type="date"
              className="field-input"
              value={dateTo}
              onChange={(event) => {
                setPage(1)
                setDateTo(event.target.value)
              }}
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Timeline"
        description="Select an event to inspect the full payload and trace what changed."
        action={
          <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
            <span>{data?.count ?? 0} event(s)</span>
            <button type="button" className="btn-secondary" onClick={() => setPage((current) => Math.max(current - 1, 1))} disabled={!data?.previous}>
              Previous
            </button>
            <button type="button" className="btn-secondary" onClick={() => setPage((current) => current + 1)} disabled={!data?.next}>
              Next
            </button>
          </div>
        }
      >
        <AuditTimeline
          entries={entries}
          activeEntryId={selectedEntry?.id ?? null}
          onEntryClick={setSelectedEntry}
          emptyTitle="No audit events match the current filters."
          emptyDescription="Broaden the current filters or wait for more organisation activity."
        />
      </SectionCard>

      <AppDialog
        open={Boolean(selectedEntry)}
        onOpenChange={(open) => {
          if (!open) setSelectedEntry(null)
        }}
        title={selectedEntry ? startCase(selectedEntry.action.replace(/\./g, ' ')) : 'Audit event'}
        description="Inspect the actor, target, and raw payload captured for this event."
        contentClassName="sm:w-[min(92vw,54rem)]"
      >
        {selectedEntry ? (
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="surface-shell rounded-[18px] px-4 py-3">
                <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Actor</p>
                <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">
                  {selectedEntry.actor_name || selectedEntry.actor_email || 'System action'}
                </p>
              </div>
              <div className="surface-shell rounded-[18px] px-4 py-3">
                <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Timestamp</p>
                <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(selectedEntry.created_at)}</p>
              </div>
              <div className="surface-shell rounded-[18px] px-4 py-3">
                <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Module</p>
                <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{startCase(selectedEntry.module)}</p>
              </div>
              <div className="surface-shell rounded-[18px] px-4 py-3">
                <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Target</p>
                <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{selectedEntry.target_label || 'Not captured'}</p>
              </div>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Payload</p>
              <pre className="mt-2 overflow-x-auto rounded-[18px] bg-[hsl(var(--surface-subtle))] p-4 text-sm text-[hsl(var(--foreground-strong))]">
                {JSON.stringify(selectedEntry.payload, null, 2)}
              </pre>
            </div>
          </div>
        ) : null}
      </AppDialog>
    </div>
  )
}
