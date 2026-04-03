import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { MonthCalendar } from '@/components/ui/MonthCalendar'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateMyLeaveRequest, useMyCalendar, useMyLeaveOverview, useWithdrawMyLeaveRequest } from '@/hooks/useEmployeeSelf'
import { DAY_SESSION_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { getLeaveStatusTone } from '@/lib/status'

const emptyLeaveForm = {
  leave_type_id: '',
  start_date: '',
  end_date: '',
  start_session: 'FULL_DAY',
  end_session: 'FULL_DAY',
  reason: '',
}

export function LeavePage() {
  const { data, isLoading } = useMyLeaveOverview()
  const { data: calendar } = useMyCalendar()
  const createMutation = useCreateMyLeaveRequest()
  const withdrawMutation = useWithdrawMyLeaveRequest()
  const [form, setForm] = useState(emptyLeaveForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const selectedBalance = data?.balances.find((balance) => balance.leave_type_id === form.leave_type_id) ?? null
  const requestedUnits = useMemo(() => {
    if (!form.start_date || !form.end_date) return 0

    const start = new Date(form.start_date)
    const end = new Date(form.end_date)
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return 0

    const dayCount = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1
    let units = dayCount
    if (form.start_session !== 'FULL_DAY') units -= 0.5
    if (form.end_session !== 'FULL_DAY' && form.end_date !== form.start_date) units -= 0.5
    if (form.end_date === form.start_date && form.start_session !== 'FULL_DAY' && form.end_session !== 'FULL_DAY') {
      units = 0.5
    }

    return Math.max(units, 0)
  }, [form.end_date, form.end_session, form.start_date, form.start_session])
  const currentBalance = Number(selectedBalance?.available ?? 0)
  const remainingBalance = currentBalance - requestedUnits

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      await createMutation.mutateAsync(form)
      toast.success('Leave request submitted.')
      setForm(emptyLeaveForm)
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to submit leave request.'))
      }
    }
  }

  const handleWithdraw = async (requestId: string) => {
    try {
      await withdrawMutation.mutateAsync(requestId)
      toast.success('Leave request withdrawn.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to withdraw leave request.'))
    }
  }

  if (isLoading || !data) {
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
      <PageHeader eyebrow="Leave" title="Leave management" description="Review balances, submit new requests, and track approvals on your leave calendar." />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {data.balances.map((balance) => (
          <div key={balance.leave_type_id} className="surface-card rounded-[28px] p-5">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">{balance.leave_type_name}</p>
            <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{balance.available}</p>
            <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
              Credited {balance.credited} • Pending {balance.pending}
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Request leave" description="Your leave policy controls balances, half-day support, and future or past request rules.">
          {data.leave_plan ? (
            <form onSubmit={handleSubmit} className="grid gap-4">
              <div>
                <AppSelect
                  value={form.leave_type_id}
                  onValueChange={(value) => setForm((current) => ({ ...current, leave_type_id: value }))}
                  options={data.leave_plan.leave_types
                    .filter((type) => type.is_active)
                    .map((type) => ({ value: type.id, label: type.name }))}
                  placeholder="Select leave type"
                />
                <FieldErrorText message={fieldErrors.leave_type_id} />
              </div>
              {selectedBalance && requestedUnits > 0 ? (
                <div className="rounded-[20px] border border-[hsl(var(--info)_/_0.22)] bg-[hsl(var(--info)_/_0.1)] px-4 py-4 text-sm">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-[hsl(var(--muted-foreground))]">Requested days</span>
                    <span className="font-semibold text-[hsl(var(--foreground-strong))]">{requestedUnits.toFixed(2)}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-4">
                    <span className="text-[hsl(var(--muted-foreground))]">Current balance</span>
                    <span className="font-semibold text-[hsl(var(--foreground-strong))]">{currentBalance.toFixed(2)}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-4">
                    <span className="text-[hsl(var(--muted-foreground))]">Remaining after request</span>
                    <span className={remainingBalance < 0 ? 'font-semibold text-[hsl(var(--danger))]' : 'font-semibold text-[hsl(var(--success))]'}>
                      {remainingBalance.toFixed(2)}
                    </span>
                  </div>
                  {remainingBalance < 0 ? (
                    <p className="mt-3 text-xs text-[hsl(var(--danger))]">
                      This request exceeds the current balance and may be converted to LOP depending on your leave rules.
                    </p>
                  ) : null}
                </div>
              ) : null}
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <AppDatePicker
                    value={form.start_date}
                    onValueChange={(value) => setForm((current) => ({ ...current, start_date: value }))}
                    placeholder="Select start date"
                  />
                  <FieldErrorText message={fieldErrors.start_date} />
                </div>
                <div>
                  <AppDatePicker
                    value={form.end_date}
                    onValueChange={(value) => setForm((current) => ({ ...current, end_date: value }))}
                    placeholder="Select end date"
                  />
                  <FieldErrorText message={fieldErrors.end_date} />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <AppSelect
                  value={form.start_session}
                  onValueChange={(value) => setForm((current) => ({ ...current, start_session: value }))}
                  options={DAY_SESSION_OPTIONS.map((session) => ({
                    value: session,
                    label: session.replace(/_/g, ' '),
                  }))}
                  placeholder="Select start session"
                />
                <AppSelect
                  value={form.end_session}
                  onValueChange={(value) => setForm((current) => ({ ...current, end_session: value }))}
                  options={DAY_SESSION_OPTIONS.map((session) => ({
                    value: session,
                    label: session.replace(/_/g, ' '),
                  }))}
                  placeholder="Select end session"
                />
              </div>
              <div>
                <textarea className="field-textarea" placeholder="Reason" value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} />
                <FieldErrorText message={fieldErrors.reason} />
              </div>
              <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                Submit leave request
              </button>
            </form>
          ) : (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">No leave plan is assigned to your employee record yet.</p>
          )}
        </SectionCard>

        <SectionCard title="Leave calendar" description="Calendar shows approved and pending leave, on-duty entries, and published holidays.">
          {calendar ? <MonthCalendar month={calendar} /> : null}
        </SectionCard>
      </div>

      <SectionCard title="My leave requests" description="Withdraw pending or approved leave requests if plans change.">
        <div className="space-y-3">
          {data.requests.map((request) => (
            <div key={request.id} className="surface-muted flex flex-col gap-3 rounded-[22px] px-4 py-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">{request.leave_type_name}</p>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  {request.start_date} to {request.end_date} • {request.total_units} day(s)
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge tone={getLeaveStatusTone(request.status)}>{request.status}</StatusBadge>
                {(request.status === 'PENDING' || request.status === 'APPROVED') ? (
                  <button className="btn-secondary" onClick={() => void handleWithdraw(request.id)}>
                    Withdraw
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
