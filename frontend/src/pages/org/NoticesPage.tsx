import { useState } from 'react'
import { toast } from 'sonner'

import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateNotice, useDepartments, useNotices, usePublishNotice } from '@/hooks/useOrgAdmin'
import { createDefaultNoticeForm, NOTICE_AUDIENCE_TYPE_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'

export function NoticesPage() {
  const { data, isLoading } = useNotices()
  const { data: departments } = useDepartments()
  const createMutation = useCreateNotice()
  const publishMutation = usePublishNotice()
  const [form, setForm] = useState(createDefaultNoticeForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      await createMutation.mutateAsync(form)
      toast.success('Notice created.')
      setForm(createDefaultNoticeForm())
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to create notice.'))
      }
    }
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
      <PageHeader eyebrow="Notices" title="Internal notices" description="Publish important organisation-wide updates, targeted announcements, and scheduled messages for employees." />

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <SectionCard title="Create notice" description="Notices can target all employees or narrower audiences such as departments.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div>
              <input className="field-input" placeholder="Title" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} required />
              <FieldErrorText message={fieldErrors.title} />
            </div>
            <div>
              <textarea className="field-textarea" placeholder="Body" value={form.body} onChange={(event) => setForm((current) => ({ ...current, body: event.target.value }))} required />
              <FieldErrorText message={fieldErrors.body} />
            </div>
            <div>
              <select className="field-select" value={form.audience_type} onChange={(event) => setForm((current) => ({ ...current, audience_type: event.target.value }))}>
              {NOTICE_AUDIENCE_TYPE_OPTIONS.map((type) => (
                <option key={type} value={type}>
                  {type.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
              <FieldErrorText message={fieldErrors.audience_type} />
            </div>
            {form.audience_type === 'DEPARTMENTS' ? (
              <div className="grid gap-2">
                {departments?.filter((department) => department.is_active).map((department) => (
                  <label key={department.id} className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                    <input
                      type="checkbox"
                      checked={form.department_ids.includes(department.id)}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          department_ids: event.target.checked
                            ? [...current.department_ids, department.id]
                            : current.department_ids.filter((id) => id !== department.id),
                        }))
                      }
                    />
                    {department.name}
                  </label>
                ))}
              </div>
            ) : null}
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              Save notice
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Noticeboard" description="Draft and published notices are visible here, with publishing handled explicitly.">
          <div className="space-y-4">
            {data?.map((notice) => (
              <div key={notice.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{notice.title}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{notice.body}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge tone={notice.status === 'PUBLISHED' ? 'success' : 'warning'}>{notice.status}</StatusBadge>
                    {notice.status !== 'PUBLISHED' ? (
                      <button className="btn-secondary" onClick={() => void publishMutation.mutateAsync(notice.id)}>
                        Publish
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
