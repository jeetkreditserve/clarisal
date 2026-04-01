import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDateTimePicker } from '@/components/ui/AppDateTimePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import {
  useCreateNotice,
  useDepartments,
  useEmployees,
  useLocations,
  useNotice,
  usePublishNotice,
  useUpdateNotice,
} from '@/hooks/useOrgAdmin'
import {
  createDefaultNoticeForm,
  NOTICE_AUDIENCE_TYPE_OPTIONS,
  NOTICE_CATEGORY_OPTIONS,
  NOTICE_STATUS_OPTIONS,
} from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { formatDateTime, startCase } from '@/lib/format'

type NoticeForm = ReturnType<typeof createDefaultNoticeForm>

export function NoticeEditorPage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEditing = Boolean(id)
  const { data: notice, isLoading } = useNotice(id ?? '')
  const { data: departments } = useDepartments(true)
  const { data: locations } = useLocations(true)
  const { data: employees } = useEmployees({ page: 1 })
  const createMutation = useCreateNotice()
  const updateMutation = useUpdateNotice(id ?? '')
  const publishMutation = usePublishNotice()
  const [form, setForm] = useState<NoticeForm>(createDefaultNoticeForm())
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (notice) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        title: notice.title,
        body: notice.body,
        category: notice.category,
        audience_type: notice.audience_type,
        status: notice.status,
        is_sticky: notice.is_sticky,
        scheduled_for: notice.scheduled_for,
        expires_at: notice.expires_at,
        department_ids: notice.department_ids,
        office_location_ids: notice.office_location_ids,
        employee_ids: notice.employee_ids,
      })
    } else if (!isEditing) {
      setForm(createDefaultNoticeForm())
    }
  }, [notice, isEditing])

  const audienceOptions = useMemo(
    () => NOTICE_AUDIENCE_TYPE_OPTIONS.map((value) => ({ value, label: startCase(value) })),
    [],
  )
  const categoryOptions = useMemo(
    () => NOTICE_CATEGORY_OPTIONS.map((value) => ({ value, label: startCase(value) })),
    [],
  )
  const statusOptions = useMemo(
    () => NOTICE_STATUS_OPTIONS.map((value) => ({ value, label: startCase(value) })),
    [],
  )

  const saveNotice = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      if (isEditing && id) {
        await updateMutation.mutateAsync(form)
        toast.success('Notice updated.')
      } else {
        await createMutation.mutateAsync(form)
        toast.success('Notice created.')
      }
      navigate('/org/notices')
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to save notice.'))
      }
    }
  }

  if (isEditing && isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={8} />
      </div>
    )
  }

  return (
    <form className="space-y-6" onSubmit={saveNotice}>
      <PageHeader
        eyebrow="Notices"
        title={isEditing ? 'Edit notice' : 'Compose notice'}
        description="Build notices as a real announcement center with category, sticky treatment, scheduling, expiry, and targeted audiences."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => navigate('/org/notices')}>
              Back to notices
            </button>
            {isEditing && notice?.status !== 'PUBLISHED' ? (
              <button
                type="button"
                className="btn-secondary"
                disabled={publishMutation.isPending}
                onClick={async () => {
                  if (!id) return
                  await publishMutation.mutateAsync(id)
                  toast.success('Notice published.')
                  navigate('/org/notices')
                }}
              >
                Publish now
              </button>
            ) : null}
            <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
              {isEditing ? 'Save changes' : 'Create notice'}
            </button>
          </>
        }
      />

      <SectionCard title="Notice basics" description="Set the announcement category, audience, and publishing state before you move into targeting and timing.">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="field-label">Title</label>
            <input
              className="field-input"
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              required
            />
            <FieldErrorText message={fieldErrors.title} />
          </div>
          <div>
            <label className="field-label">Category</label>
            <AppSelect value={form.category} onValueChange={(value) => setForm((current) => ({ ...current, category: value }))} options={categoryOptions} />
            <FieldErrorText message={fieldErrors.category} />
          </div>
          <div>
            <label className="field-label">Audience</label>
            <AppSelect
              value={form.audience_type}
              onValueChange={(value) =>
                setForm((current) => ({
                  ...current,
                  audience_type: value,
                  department_ids: value === 'DEPARTMENTS' ? current.department_ids : [],
                  office_location_ids: value === 'OFFICE_LOCATIONS' ? current.office_location_ids : [],
                  employee_ids: value === 'SPECIFIC_EMPLOYEES' ? current.employee_ids : [],
                }))
              }
              options={audienceOptions}
            />
            <FieldErrorText message={fieldErrors.audience_type} />
          </div>
          <div>
            <label className="field-label">Status</label>
            <AppSelect value={form.status} onValueChange={(value) => setForm((current) => ({ ...current, status: value }))} options={statusOptions} />
            <FieldErrorText message={fieldErrors.status} />
          </div>
          <div className="lg:col-span-2">
            <label className="field-label">Body</label>
            <textarea
              className="field-textarea min-h-[12rem]"
              value={form.body}
              onChange={(event) => setForm((current) => ({ ...current, body: event.target.value }))}
              required
            />
            <FieldErrorText message={fieldErrors.body} />
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          <AppCheckbox
            checked={form.is_sticky}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_sticky: checked }))}
            label="Sticky notice"
            description="Sticky notices stay visually pinned higher in employee notice feeds."
          />
        </div>
      </SectionCard>

      <SectionCard title="Timing and targeting" description="Schedule, expire, and target notices precisely so employees only see what is relevant to them.">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="field-label">Scheduled publish</label>
            <AppDateTimePicker value={form.scheduled_for} onValueChange={(value) => setForm((current) => ({ ...current, scheduled_for: value }))} placeholder="Schedule publish time" />
            <FieldErrorText message={fieldErrors.scheduled_for} />
          </div>
          <div>
            <label className="field-label">Expiry time</label>
            <AppDateTimePicker value={form.expires_at} onValueChange={(value) => setForm((current) => ({ ...current, expires_at: value }))} placeholder="Optional expiry time" />
            <FieldErrorText message={fieldErrors.expires_at} />
          </div>
        </div>

        {form.audience_type === 'DEPARTMENTS' ? (
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            {(departments ?? []).map((department) => (
              <AppCheckbox
                key={department.id}
                checked={form.department_ids.includes(department.id)}
                onCheckedChange={(checked) =>
                  setForm((current) => ({
                    ...current,
                    department_ids: checked
                      ? [...current.department_ids, department.id]
                      : current.department_ids.filter((value) => value !== department.id),
                  }))
                }
                label={department.name}
                description={department.description || undefined}
              />
            ))}
            <FieldErrorText message={fieldErrors.department_ids} />
          </div>
        ) : null}

        {form.audience_type === 'OFFICE_LOCATIONS' ? (
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            {(locations ?? []).map((location) => (
              <AppCheckbox
                key={location.id}
                checked={form.office_location_ids.includes(location.id)}
                onCheckedChange={(checked) =>
                  setForm((current) => ({
                    ...current,
                    office_location_ids: checked
                      ? [...current.office_location_ids, location.id]
                      : current.office_location_ids.filter((value) => value !== location.id),
                  }))
                }
                label={location.name}
                description={location.city && location.country ? `${location.city}, ${location.country}` : undefined}
              />
            ))}
            <FieldErrorText message={fieldErrors.office_location_ids} />
          </div>
        ) : null}

        {form.audience_type === 'SPECIFIC_EMPLOYEES' ? (
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            {(employees?.results ?? []).map((employee) => (
              <AppCheckbox
                key={employee.id}
                checked={form.employee_ids.includes(employee.id)}
                onCheckedChange={(checked) =>
                  setForm((current) => ({
                    ...current,
                    employee_ids: checked
                      ? [...current.employee_ids, employee.id]
                      : current.employee_ids.filter((value) => value !== employee.id),
                  }))
                }
                label={employee.full_name}
                description={employee.designation || undefined}
              />
            ))}
            <FieldErrorText message={fieldErrors.employee_ids} />
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Publishing preview" description="Review the visibility and timeline posture before you send this notice into the employee experience.">
        <div className="grid gap-4 xl:grid-cols-4">
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Audience</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">{startCase(form.audience_type)}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Status</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">{startCase(form.status)}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Sticky</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">{form.is_sticky ? 'Pinned' : 'Standard'}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {notice ? formatDateTime(notice.modified_at) : 'New draft'}
            </p>
          </div>
        </div>
      </SectionCard>
    </form>
  )
}
