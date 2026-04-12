import { useState } from 'react'

import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useMyTeamAttendance } from '@/hooks/useEmployeeSelf'
import { getAttendanceDayStatusTone } from '@/lib/status'
import type { AttendanceDayRecord } from '@/types/hr'

type TeamAttendanceFilter = 'ALL' | 'ATTENTION'

function buildTeamAttendanceCsv(rows: AttendanceDayRecord[]) {
  const lines = [
    ['Employee', 'Code', 'Date', 'Status', 'Check in', 'Check out', 'Needs regularization'],
    ...rows.map((row) => [
      row.employee_name,
      row.employee_code ?? '',
      row.attendance_date,
      row.status,
      row.check_in_at ?? '',
      row.check_out_at ?? '',
      row.needs_regularization ? 'Yes' : 'No',
    ]),
  ]
  return lines.map((line) => line.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n')
}

export function MyTeamAttendancePage() {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10))
  const [filter, setFilter] = useState<TeamAttendanceFilter>('ALL')
  const { data, isLoading } = useMyTeamAttendance(selectedDate)

  const filteredRows = (data ?? []).filter((row) => {
    if (filter === 'ATTENTION') {
      return row.needs_regularization || row.status === 'ABSENT' || row.status === 'INCOMPLETE'
    }
    return true
  })

  const handleExportCsv = () => {
    const blob = new Blob([buildTeamAttendanceCsv(filteredRows)], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `my-team-attendance-${selectedDate}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Manager self-service"
        title="Team attendance"
        description="Inspect the current day, isolate rows that need attention, and export the filtered attendance snapshot to CSV."
        actions={
          <button type="button" className="btn-secondary" onClick={handleExportCsv}>
            Export CSV
          </button>
        }
      />

      <SectionCard title="Attendance filters" description="Pick a date and narrow to the rows that need manager follow-up.">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="w-full max-w-xs">
            <AppDatePicker value={selectedDate} onValueChange={setSelectedDate} placeholder="Attendance date" />
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={filter === 'ALL' ? 'btn-primary' : 'btn-secondary'}
              onClick={() => setFilter('ALL')}
            >
              All statuses
            </button>
            <button
              type="button"
              className={filter === 'ATTENTION' ? 'btn-primary' : 'btn-secondary'}
              onClick={() => setFilter('ATTENTION')}
            >
              Needs attention
            </button>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Attendance snapshot" description="Team rows refresh when the date changes. Attention mode focuses on absent or incomplete attendance that usually needs follow-up.">
        {filteredRows.length ? (
          <div className="space-y-3">
            {filteredRows.map((row) => (
              <div key={row.id} className="surface-muted flex flex-col gap-3 rounded-[22px] px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{row.employee_name}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    {row.employee_code || 'Unassigned code'} • {row.check_in_at ? new Date(row.check_in_at).toLocaleTimeString() : 'No check-in'} •{' '}
                    {row.check_out_at ? new Date(row.check_out_at).toLocaleTimeString() : 'No check-out'}
                  </p>
                  {row.note ? <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{row.note}</p> : null}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={getAttendanceDayStatusTone(row.status)}>{row.status}</StatusBadge>
                  {row.needs_regularization ? <StatusBadge tone="warning">Needs regularization</StatusBadge> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No attendance rows for the current filter"
            description="Try another date or switch back to the full list if you want to inspect all direct reports."
          />
        )}
      </SectionCard>
    </div>
  )
}
