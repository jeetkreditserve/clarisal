import { useState } from 'react'
import { toast } from 'sonner'

import { MonthCalendar } from '@/components/ui/MonthCalendar'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateMyLeaveRequest, useMyCalendar, useMyLeaveOverview, useWithdrawMyLeaveRequest } from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createMutation.mutateAsync(form)
      toast.success('Leave request submitted.')
      setForm(emptyLeaveForm)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to submit leave request.'))
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
              <select className="field-select" value={form.leave_type_id} onChange={(event) => setForm((current) => ({ ...current, leave_type_id: event.target.value }))} required>
                <option value="">Select leave type</option>
                {data.leave_plan.leave_types.filter((type) => type.is_active).map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.name}
                  </option>
                ))}
              </select>
              <div className="grid gap-4 md:grid-cols-2">
                <input className="field-input" type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} required />
                <input className="field-input" type="date" value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} required />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <select className="field-select" value={form.start_session} onChange={(event) => setForm((current) => ({ ...current, start_session: event.target.value }))}>
                  {['FULL_DAY', 'FIRST_HALF', 'SECOND_HALF'].map((session) => (
                    <option key={session} value={session}>
                      {session.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
                <select className="field-select" value={form.end_session} onChange={(event) => setForm((current) => ({ ...current, end_session: event.target.value }))}>
                  {['FULL_DAY', 'FIRST_HALF', 'SECOND_HALF'].map((session) => (
                    <option key={session} value={session}>
                      {session.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>
              <textarea className="field-textarea" placeholder="Reason" value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} />
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
