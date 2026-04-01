import { useState } from 'react'
import { GraduationCap } from 'lucide-react'
import { toast } from 'sonner'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import {
  useCreateEducation,
  useDeleteEducation,
  useEducation,
  useUpdateEducation,
} from '@/hooks/useEmployeeSelf'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { formatDate } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = {
  degree: '',
  institution: '',
  field_of_study: '',
  start_year: '',
  end_year: '',
  grade: '',
  is_current: false,
}

export function EducationPage() {
  const { data, isLoading } = useEducation()
  const createMutation = useCreateEducation()
  const updateMutation = useUpdateEducation()
  const deleteMutation = useDeleteEducation()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      degree: form.degree,
      institution: form.institution,
      field_of_study: form.field_of_study,
      start_year: form.start_year ? Number(form.start_year) : null,
      end_year: form.end_year ? Number(form.end_year) : null,
      grade: form.grade,
      is_current: form.is_current,
    }
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, payload })
        toast.success('Education record updated.')
      } else {
        await createMutation.mutateAsync(payload)
        toast.success('Education record added.')
      }
      setEditingId(null)
      setForm(emptyForm)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save education record.'))
    }
  }

  const handleEdit = (recordId: string) => {
    const record = data?.find((item) => item.id === recordId)
    if (!record) return
    setEditingId(record.id)
    setForm({
      degree: record.degree,
      institution: record.institution,
      field_of_study: record.field_of_study,
      start_year: record.start_year ? String(record.start_year) : '',
      end_year: record.end_year ? String(record.end_year) : '',
      grade: record.grade,
      is_current: record.is_current,
    })
  }

  const handleDelete = async (recordId: string) => {
    if (!window.confirm('Delete this education record?')) return
    try {
      await deleteMutation.mutateAsync(recordId)
      toast.success('Education record removed.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to delete education record.'))
    }
  }

  return (
    <div className="space-y-6">
      {isLoading && !data ? (
        <SkeletonPageHeader />
      ) : (
        <PageHeader eyebrow="Education" title="Education details" description="Maintain your academic history and supporting context for HR records." />
      )}

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title={editingId ? 'Edit education record' : 'Add education record'} description="Add each degree, certification, or active course separately.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            {[
              ['degree', 'Degree'],
              ['institution', 'Institution'],
              ['field_of_study', 'Field of study'],
              ['start_year', 'Start year'],
              ['end_year', 'End year'],
              ['grade', 'Grade'],
            ].map(([field, label]) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {label}
                </label>
                <input
                  id={field}
                  className="field-input"
                  value={form[field as keyof typeof form] as string}
                  onChange={(event) => setForm((current) => ({ ...current, [field]: event.target.value }))}
                  required={field === 'degree' || field === 'institution'}
                />
              </div>
            ))}
            <AppCheckbox
              checked={form.is_current}
              onCheckedChange={(checked) => setForm((current) => ({ ...current, is_current: checked }))}
              label="Currently pursuing"
            />
            <div className="flex flex-wrap gap-3">
              {editingId ? (
                <button
                  type="button"
                  onClick={() => {
                    setEditingId(null)
                    setForm(emptyForm)
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              ) : null}
              <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                {editingId ? 'Save record' : 'Add record'}
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard title="Education history" description="Existing records associated with your employee profile.">
          {isLoading ? (
            <SkeletonTable rows={4} />
          ) : data && data.length > 0 ? (
            <div className="space-y-3">
              {data.map((record) => (
                <div key={record.id} className="surface-muted flex flex-col gap-4 rounded-[24px] p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <GraduationCap className="h-4 w-4 text-[hsl(var(--brand))]" />
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{record.degree}</p>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{record.institution}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      {record.field_of_study || 'General'} • {record.start_year || 'N/A'} - {record.is_current ? 'Present' : record.end_year || 'N/A'}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Updated {formatDate(record.updated_at)}</p>
                  </div>
                  <div className="flex gap-3">
                    <button type="button" onClick={() => handleEdit(record.id)} className="btn-secondary">
                      Edit
                    </button>
                    <button type="button" onClick={() => handleDelete(record.id)} className="btn-danger">
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No education records added yet"
              description="Add your first degree, certification, or current course so HR has the right academic context."
              icon={GraduationCap}
            />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
