import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useCreateOnDutyPolicy, useOnDutyPolicy, useOrgOnDutyRequests, useUpdateOnDutyPolicy } from '@/hooks/useOrgAdmin'
import {
  useCreateCtOnDutyPolicy,
  useCtOrgConfiguration,
  useUpdateCtOnDutyPolicy,
} from '@/hooks/useCtOrganisations'
import { createDefaultOnDutyPolicyForm } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'

type OnDutyPolicyForm = ReturnType<typeof createDefaultOnDutyPolicyForm>

export function OnDutyPolicyBuilderPage() {
  const navigate = useNavigate()
  const { id, organisationId } = useParams()
  const isEditing = Boolean(id)
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const { data: orgPolicy, isLoading } = useOnDutyPolicy(id ?? '')
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const { data: requests } = useOrgOnDutyRequests()
  const createMutation = useCreateOnDutyPolicy()
  const updateMutation = useUpdateOnDutyPolicy(id ?? '')
  const createCtMutation = useCreateCtOnDutyPolicy(organisationId ?? '')
  const updateCtMutation = useUpdateCtOnDutyPolicy(organisationId ?? '')
  const [form, setForm] = useState<OnDutyPolicyForm>(createDefaultOnDutyPolicyForm())
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const policy = isCtMode ? configuration?.on_duty_policies.find((item) => item.id === id) : orgPolicy

  useEffect(() => {
    if (policy) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        name: policy.name,
        description: policy.description,
        is_default: policy.is_default,
        is_active: policy.is_active,
        allow_half_day: policy.allow_half_day,
        allow_time_range: policy.allow_time_range,
        requires_attachment: policy.requires_attachment,
        min_notice_days: policy.min_notice_days,
        allow_past_request: policy.allow_past_request,
        allow_future_request: policy.allow_future_request,
      })
    } else if (!isEditing) {
      setForm(createDefaultOnDutyPolicyForm())
    }
  }, [policy, isEditing])

  const relatedRequests = useMemo(
    () => (isCtMode ? [] : (requests ?? []).filter((request) => request.policy === id)),
    [isCtMode, requests, id],
  )

  const savePolicy = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      if (isEditing && id) {
        if (isCtMode && organisationId) {
          await updateCtMutation.mutateAsync({ policyId: id, payload: form })
        } else {
          await updateMutation.mutateAsync(form)
        }
        toast.success('OD policy updated.')
      } else {
        if (isCtMode && organisationId) {
          await createCtMutation.mutateAsync(form)
        } else {
          await createMutation.mutateAsync(form)
        }
        toast.success('OD policy created.')
      }
      navigate(`${basePath}/on-duty-policies`)
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to save on-duty policy.'))
      }
    }
  }

  if (isEditing && (isCtMode ? isCtLoading : isLoading)) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={8} />
      </div>
    )
  }

  return (
    <form className="space-y-6" onSubmit={savePolicy}>
      <PageHeader
        eyebrow={isCtMode ? 'Control Tower • OD configuration' : 'OD configuration'}
        title={isEditing ? 'Edit on-duty policy' : 'Create on-duty policy'}
        description="Set the request modes, evidence rules, and time windows that govern travel, field work, and other OD submissions."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => navigate(`${basePath}/on-duty-policies`)}>
              Back to policies
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={
                createMutation.isPending ||
                updateMutation.isPending ||
                createCtMutation.isPending ||
                updateCtMutation.isPending
              }
            >
              {isEditing ? 'Save changes' : 'Create policy'}
            </button>
          </>
        }
      />

      <SectionCard title="Policy basics" description="Define the core OD policy identity and whether this policy is the default for the organisation.">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="field-label" htmlFor="od-policy-name">
              Policy name
            </label>
            <input
              id="od-policy-name"
              className="field-input"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
            <FieldErrorText message={fieldErrors.name} />
          </div>
          <div>
            <label className="field-label" htmlFor="od-policy-description">
              Description
            </label>
            <textarea
              id="od-policy-description"
              className="field-textarea"
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
        </div>
        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          <AppCheckbox
            checked={form.is_default}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))}
            label="Default OD policy"
            description="Employees will fall back to this policy unless a more specific policy is chosen in future configuration."
          />
          <AppCheckbox
            checked={form.is_active}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_active: checked }))}
            label="Active policy"
            description="Inactive policies remain in history but should no longer be used for fresh OD submissions."
          />
        </div>
      </SectionCard>

      <SectionCard title="Request rules" description="Control which request shapes are allowed and how much evidence or notice is required.">
        <div className="grid gap-4 xl:grid-cols-3">
          <div>
            <label className="field-label" htmlFor="od-min-notice">
              Minimum notice days
            </label>
            <input
              id="od-min-notice"
              type="number"
              min={0}
              className="field-input"
              value={form.min_notice_days}
              onChange={(event) => setForm((current) => ({ ...current, min_notice_days: Number(event.target.value || 0) }))}
            />
            <FieldErrorText message={fieldErrors.min_notice_days} />
          </div>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-3">
          <AppCheckbox
            checked={form.allow_half_day}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, allow_half_day: checked }))}
            label="Allow half-day OD"
          />
          <AppCheckbox
            checked={form.allow_time_range}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, allow_time_range: checked }))}
            label="Allow time-range OD"
          />
          <AppCheckbox
            checked={form.requires_attachment}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, requires_attachment: checked }))}
            label="Require attachment"
          />
          <AppCheckbox
            checked={form.allow_past_request}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, allow_past_request: checked }))}
            label="Allow past-dated requests"
          />
          <AppCheckbox
            checked={form.allow_future_request}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, allow_future_request: checked }))}
            label="Allow future requests"
          />
        </div>
      </SectionCard>

      <SectionCard title="Operational preview" description="Sanity-check how this policy behaves before you turn it loose on employees.">
        <div className="grid gap-4 xl:grid-cols-4">
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Request modes</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {[form.allow_half_day && 'Half day', form.allow_time_range && 'Time range'].filter(Boolean).join(' • ') || 'Full day only'}
            </p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Evidence rule</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {form.requires_attachment ? 'Attachment required' : 'Attachment optional'}
            </p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">OD requests using this policy</p>
            <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{isCtMode ? '--' : relatedRequests.length}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {policy ? formatDateTime(policy.modified_at) : 'New draft'}
            </p>
          </div>
        </div>
      </SectionCard>
    </form>
  )
}
