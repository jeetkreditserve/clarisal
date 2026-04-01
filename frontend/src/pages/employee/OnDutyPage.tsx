import { useState } from 'react'
import { toast } from 'sonner'

import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateMyOnDutyRequest, useMyOnDutyPolicies, useMyOnDutyRequests, useWithdrawMyOnDutyRequest } from '@/hooks/useEmployeeSelf'
import { OD_DURATION_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { getLeaveStatusTone } from '@/lib/status'

const emptyForm = {
  policy_id: '',
  start_date: '',
  end_date: '',
  duration_type: 'FULL_DAY',
  start_time: '',
  end_time: '',
  purpose: '',
  destination: '',
}

export function OnDutyPage() {
  const { data: policies, isLoading: policiesLoading } = useMyOnDutyPolicies()
  const { data: requests, isLoading: requestsLoading } = useMyOnDutyRequests()
  const createMutation = useCreateMyOnDutyRequest()
  const withdrawMutation = useWithdrawMyOnDutyRequest()
  const [form, setForm] = useState(emptyForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      await createMutation.mutateAsync({
        ...form,
        policy_id: form.policy_id || null,
        start_time: form.start_time || null,
        end_time: form.end_time || null,
      })
      toast.success('On-duty request submitted.')
      setForm(emptyForm)
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to submit on-duty request.'))
      }
    }
  }

  if (policiesLoading || requestsLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="On duty" title="OD management" description="Submit full-day, half-day, or time-range on-duty requests and track their approval state." />

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <SectionCard title="Request on duty" description="Use on-duty for work travel, field visits, client meetings, or other approved business duty.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div>
              <select className="field-select" value={form.policy_id} onChange={(event) => setForm((current) => ({ ...current, policy_id: event.target.value }))}>
                <option value="">Default policy</option>
                {policies?.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.name}
                  </option>
                ))}
              </select>
              <FieldErrorText message={fieldErrors.policy_id} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <input className="field-input" type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} required />
                <FieldErrorText message={fieldErrors.start_date} />
              </div>
              <div>
                <input className="field-input" type="date" value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} required />
                <FieldErrorText message={fieldErrors.end_date} />
              </div>
            </div>
            <div>
              <select className="field-select" value={form.duration_type} onChange={(event) => setForm((current) => ({ ...current, duration_type: event.target.value }))}>
                {OD_DURATION_OPTIONS.map((type) => (
                  <option key={type} value={type}>
                    {type.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
              <FieldErrorText message={fieldErrors.duration_type} />
            </div>
            {form.duration_type === 'TIME_RANGE' ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <input className="field-input" type="time" value={form.start_time} onChange={(event) => setForm((current) => ({ ...current, start_time: event.target.value }))} />
                  <FieldErrorText message={fieldErrors.start_time} />
                </div>
                <div>
                  <input className="field-input" type="time" value={form.end_time} onChange={(event) => setForm((current) => ({ ...current, end_time: event.target.value }))} />
                  <FieldErrorText message={fieldErrors.end_time} />
                </div>
              </div>
            ) : null}
            <div>
              <textarea className="field-textarea" placeholder="Purpose" value={form.purpose} onChange={(event) => setForm((current) => ({ ...current, purpose: event.target.value }))} required />
              <FieldErrorText message={fieldErrors.purpose} />
            </div>
            <div>
              <input className="field-input" placeholder="Destination or context" value={form.destination} onChange={(event) => setForm((current) => ({ ...current, destination: event.target.value }))} />
              <FieldErrorText message={fieldErrors.destination} />
            </div>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              Submit OD request
            </button>
          </form>
        </SectionCard>

        <SectionCard title="My on-duty requests" description="Withdraw pending or approved requests when travel or field work plans change.">
          <div className="space-y-3">
            {requests?.map((request) => (
              <div key={request.id} className="surface-muted flex flex-col gap-3 rounded-[22px] px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{request.policy_name}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    {request.start_date} to {request.end_date} • {request.duration_type.replace(/_/g, ' ')}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge tone={getLeaveStatusTone(request.status)}>{request.status}</StatusBadge>
                  {(request.status === 'PENDING' || request.status === 'APPROVED') ? (
                    <button className="btn-secondary" onClick={() => void withdrawMutation.mutateAsync(request.id)}>
                      Withdraw
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
