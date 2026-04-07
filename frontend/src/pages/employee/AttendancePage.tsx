import { useState } from 'react'
import { toast } from 'sonner'

import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useMyAttendanceCalendar,
  useCreateMyAttendanceRegularization,
  useMyAttendanceHistory,
  useMyAttendanceRegularizations,
  useMyAttendanceSummary,
  usePunchIn,
  usePunchOut,
  useWithdrawMyAttendanceRegularization,
} from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'
import { getAttendanceDayStatusTone } from '@/lib/status'

function getRegularizationTone(status: string) {
  if (status === 'APPROVED') return 'success'
  if (status === 'PENDING') return 'warning'
  if (status === 'WITHDRAWN' || status === 'CANCELLED') return 'info'
  return 'danger'
}

const emptyRegularizationForm = {
  attendance_date: new Date().toISOString().slice(0, 10),
  requested_check_in: '',
  requested_check_out: '',
  reason: '',
}

export function AttendancePage() {
  const [currentMonth, setCurrentMonth] = useState(new Date().toISOString().slice(0, 7))
  const { data: summary, isLoading: summaryLoading } = useMyAttendanceSummary()
  const { data: history, isLoading: historyLoading } = useMyAttendanceHistory(currentMonth)
  const { data: calendar, isLoading: calendarLoading } = useMyAttendanceCalendar(currentMonth)
  const { data: regularizations, isLoading: regularizationLoading } = useMyAttendanceRegularizations()
  const punchInMutation = usePunchIn()
  const punchOutMutation = usePunchOut()
  const createRegularizationMutation = useCreateMyAttendanceRegularization()
  const withdrawRegularizationMutation = useWithdrawMyAttendanceRegularization()
  const [form, setForm] = useState(emptyRegularizationForm)

  const handlePunchIn = async () => {
    try {
      await punchInMutation.mutateAsync({})
      toast.success('Checked in successfully.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to check in.'))
    }
  }

  const handlePunchOut = async () => {
    try {
      await punchOutMutation.mutateAsync({})
      toast.success('Checked out successfully.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to check out.'))
    }
  }

  const handleRegularizationSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createRegularizationMutation.mutateAsync({
        attendance_date: form.attendance_date,
        requested_check_in: form.requested_check_in || null,
        requested_check_out: form.requested_check_out || null,
        reason: form.reason,
      })
      toast.success('Attendance regularization submitted.')
      setForm(emptyRegularizationForm)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to submit the regularization request.'))
    }
  }

  const handleWithdraw = async (id: string) => {
    try {
      await withdrawRegularizationMutation.mutateAsync(id)
      toast.success('Attendance regularization withdrawn.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to withdraw the regularization request.'))
    }
  }

  if (summaryLoading || !summary) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonMetricCard key={index} />
          ))}
        </div>
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Attendance"
        title="My attendance"
        description="Mark attendance, review the current month, and submit regularizations when punch data needs correction."
        actions={
          <>
            <button type="button" className="btn-primary" onClick={() => void handlePunchIn()} disabled={punchInMutation.isPending}>
              {punchInMutation.isPending ? 'Checking in...' : 'Check in'}
            </button>
            <button type="button" className="btn-secondary" onClick={() => void handlePunchOut()} disabled={punchOutMutation.isPending}>
              {punchOutMutation.isPending ? 'Checking out...' : 'Check out'}
            </button>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Today</p>
          <div className="mt-3 flex items-center gap-3">
            <p className="text-2xl font-semibold text-[hsl(var(--foreground-strong))]">{summary.today.status}</p>
            <StatusBadge tone={getAttendanceDayStatusTone(summary.today.status)}>{summary.today.status}</StatusBadge>
          </div>
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
            {summary.today.attendance_date}
            {summary.today.metadata?.wfh_status ? ` • WFH ${String(summary.today.metadata.wfh_status)}` : ''}
          </p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Worked minutes</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{summary.today.worked_minutes}</p>
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
            OT {summary.today.overtime_minutes} mins
            {summary.today.metadata?.overtime_status ? ` • ${String(summary.today.metadata.overtime_status)}` : ''}
          </p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Effective shift</p>
          <p className="mt-3 text-xl font-semibold text-[hsl(var(--foreground-strong))]">{summary.shift?.name ?? 'Default policy timing'}</p>
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
            {summary.shift ? `${summary.shift.start_time.slice(0, 5)} to ${summary.shift.end_time.slice(0, 5)}` : `${summary.policy.default_start_time.slice(0, 5)} to ${summary.policy.default_end_time.slice(0, 5)}`}
          </p>
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">Source: {summary.shift_source.replace(/_/g, ' ')}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Overtime policy</p>
          <p className="mt-3 text-xl font-semibold text-[hsl(var(--foreground-strong))]">
            {summary.policy.overtime_approval_required ? 'Approval required' : 'Directly payable'}
          </p>
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
            Threshold {summary.policy.overtime_threshold_minutes} mins • Multiplier {summary.policy.overtime_multiplier}x
          </p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <SectionCard title="Regularize attendance" description="Use this when a check-in or check-out is missing or when the attendance times need correction.">
          <form className="grid gap-4" onSubmit={handleRegularizationSubmit}>
            <AppDatePicker value={form.attendance_date} onValueChange={(value) => setForm((current) => ({ ...current, attendance_date: value }))} placeholder="Attendance date" />
            <div className="grid gap-4 md:grid-cols-2">
              <input className="field-input" type="time" value={form.requested_check_in} onChange={(event) => setForm((current) => ({ ...current, requested_check_in: event.target.value }))} />
              <input className="field-input" type="time" value={form.requested_check_out} onChange={(event) => setForm((current) => ({ ...current, requested_check_out: event.target.value }))} />
            </div>
            <textarea className="field-textarea" value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} placeholder="Reason for the attendance correction" />
            <button type="submit" className="btn-primary" disabled={createRegularizationMutation.isPending}>
              Submit regularization
            </button>
          </form>
        </SectionCard>

        <SectionCard title="My regularizations" description="Withdraw requests while they are still pending. Approved requests update your attendance day automatically.">
          {regularizationLoading ? (
            <SkeletonTable rows={4} />
          ) : regularizations?.length ? (
            <div className="space-y-3">
              {regularizations.map((item) => (
                <div key={item.id} className="surface-muted rounded-[20px] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-[hsl(var(--foreground-strong))]">{item.attendance_date}</p>
                    <StatusBadge tone={getRegularizationTone(item.status)}>{item.status}</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {item.requested_check_in_at ? new Date(item.requested_check_in_at).toLocaleTimeString() : 'No check-in'} •{' '}
                    {item.requested_check_out_at ? new Date(item.requested_check_out_at).toLocaleTimeString() : 'No check-out'}
                  </p>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{item.reason}</p>
                  {item.status === 'PENDING' ? (
                    <button type="button" className="btn-secondary mt-3" onClick={() => void handleWithdraw(item.id)}>
                      Withdraw
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No attendance regularizations yet" description="When you submit attendance corrections, they will appear here with the latest approval status." />
          )}
        </SectionCard>
      </div>

      <SectionCard title="Current month attendance history" description="Review how the attendance engine classified each day in the current month.">
        <div className="mb-4 max-w-sm">
          <input className="field-input" type="month" value={currentMonth} onChange={(event) => setCurrentMonth(event.target.value)} />
        </div>
        {calendarLoading ? null : calendar?.days?.length ? (
          <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <div className="surface-muted rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Present days
              <p className="mt-1 text-xl font-semibold text-[hsl(var(--foreground-strong))]">
                {calendar.days.filter((item) => item.status === 'PRESENT' || item.status === 'ON_DUTY').length}
              </p>
            </div>
            <div className="surface-muted rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              WFH days
              <p className="mt-1 text-xl font-semibold text-[hsl(var(--foreground-strong))]">
                {calendar.days.filter((item) => item.status === 'WFH' || item.wfh_status === 'APPROVED').length}
              </p>
            </div>
            <div className="surface-muted rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Incomplete days
              <p className="mt-1 text-xl font-semibold text-[hsl(var(--foreground-strong))]">
                {calendar.days.filter((item) => item.status === 'INCOMPLETE').length}
              </p>
            </div>
            <div className="surface-muted rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Late marks
              <p className="mt-1 text-xl font-semibold text-[hsl(var(--foreground-strong))]">{calendar.days.filter((item) => item.is_late).length}</p>
            </div>
            <div className="surface-muted rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Overtime minutes
              <p className="mt-1 text-xl font-semibold text-[hsl(var(--foreground-strong))]">
                {calendar.days.reduce((sum, item) => sum + item.overtime_minutes, 0)}
              </p>
            </div>
            <div className="surface-muted rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Pending regularizations
              <p className="mt-1 text-xl font-semibold text-[hsl(var(--foreground-strong))]">{summary.pending_regularizations.length}</p>
            </div>
          </div>
        ) : null}
        {historyLoading ? (
          <SkeletonTable rows={6} />
        ) : history?.length ? (
          <div className="space-y-3">
            {history.map((day) => (
              <div key={day.id} className="surface-muted flex flex-col gap-3 rounded-[22px] px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{day.attendance_date}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    {day.check_in_at ? new Date(day.check_in_at).toLocaleTimeString() : 'No check-in'} • {day.check_out_at ? new Date(day.check_out_at).toLocaleTimeString() : 'No check-out'} • Worked {day.worked_minutes} mins
                  </p>
                  {day.metadata?.wfh_status ? (
                    <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
                      WFH {String(day.metadata.wfh_status)} • Shift source {String(day.metadata.effective_shift_source ?? 'POLICY_DEFAULT')}
                    </p>
                  ) : null}
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge tone={getAttendanceDayStatusTone(day.status)}>{day.status}</StatusBadge>
                  {day.needs_regularization ? <StatusBadge tone="warning">Needs regularization</StatusBadge> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No attendance history yet" description="Attendance history will appear after you start punching in, import attendance, or receive approved attendance regularizations." />
        )}
      </SectionCard>
    </div>
  )
}
