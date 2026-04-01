import { useState } from 'react'
import { toast } from 'sonner'

import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDialog } from '@/components/ui/AppDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateNotice, useDepartments, useNotices, usePublishNotice, useUpdateNotice } from '@/hooks/useOrgAdmin'
import { createDefaultNoticeForm, NOTICE_AUDIENCE_TYPE_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { startCase } from '@/lib/format'

export function NoticesPage() {
  const { data, isLoading } = useNotices()
  const { data: departments } = useDepartments()
  const createMutation = useCreateNotice()
  const publishMutation = usePublishNotice()
  const [editingId, setEditingId] = useState<string | null>(null)
  const updateMutation = useUpdateNotice(editingId ?? '')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form, setForm] = useState(createDefaultNoticeForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const audienceTypeOptions = NOTICE_AUDIENCE_TYPE_OPTIONS.map((type) => ({
    value: type,
    label: startCase(type),
  }))

  const resetForm = () => {
    setEditingId(null)
    setForm(createDefaultNoticeForm())
    setFieldErrors({})
    setIsModalOpen(false)
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      if (editingId) {
        await updateMutation.mutateAsync(form)
        toast.success('Notice updated.')
      } else {
        await createMutation.mutateAsync(form)
        toast.success('Notice created.')
      }
      resetForm()
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to save notice.'))
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
      <PageHeader
        eyebrow="Notices"
        title="Internal notices"
        description="Publish important organisation-wide updates, targeted announcements, and scheduled messages for employees."
        actions={
          <button type="button" className="btn-primary" onClick={() => setIsModalOpen(true)}>
            Add notice
          </button>
        }
      />

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
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setEditingId(notice.id)
                      setForm({
                        title: notice.title,
                        body: notice.body,
                        audience_type: notice.audience_type,
                        department_ids: notice.department_ids ?? [],
                        employee_ids: notice.employee_ids ?? [],
                        office_location_ids: notice.office_location_ids ?? [],
                        status: notice.status,
                      })
                      setIsModalOpen(true)
                    }}
                  >
                    Edit
                  </button>
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

      <AppDialog
        open={isModalOpen}
        onOpenChange={(open) => {
          setIsModalOpen(open)
          if (!open) resetForm()
        }}
        title={editingId ? 'Edit notice' : 'Create notice'}
        description="Notices can target all employees or narrower audiences such as departments."
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={resetForm}>
              Cancel
            </button>
            <button type="submit" form="notice-form" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingId ? 'Save changes' : 'Save notice'}
            </button>
          </div>
        }
      >
        <form id="notice-form" onSubmit={handleSubmit} className="grid gap-4">
          <div>
            <input className="field-input" placeholder="Title" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} required />
            <FieldErrorText message={fieldErrors.title} />
          </div>
          <div>
            <textarea className="field-textarea" placeholder="Body" value={form.body} onChange={(event) => setForm((current) => ({ ...current, body: event.target.value }))} required />
            <FieldErrorText message={fieldErrors.body} />
          </div>
          <div>
            <AppSelect
              value={form.audience_type}
              onValueChange={(value) => setForm((current) => ({ ...current, audience_type: value }))}
              options={audienceTypeOptions}
            />
            <FieldErrorText message={fieldErrors.audience_type} />
          </div>
          {form.audience_type === 'DEPARTMENTS' ? (
            <div className="grid gap-2">
              {departments?.filter((department) => department.is_active).map((department) => (
                <AppCheckbox
                  key={department.id}
                  id={`notice-department-${department.id}`}
                  checked={form.department_ids.includes(department.id)}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      department_ids: checked
                        ? [...current.department_ids, department.id]
                        : current.department_ids.filter((id) => id !== department.id),
                    }))
                  }
                  label={department.name}
                />
              ))}
            </div>
          ) : null}
        </form>
      </AppDialog>
    </div>
  )
}
