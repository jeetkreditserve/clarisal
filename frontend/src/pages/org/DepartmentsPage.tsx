import { useState } from 'react'
import { Building } from 'lucide-react'
import { toast } from 'sonner'
import {
  useCreateDepartment,
  useDeactivateDepartment,
  useDepartments,
  useUpdateDepartment,
} from '@/hooks/useOrgAdmin'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = { name: '', description: '' }

export function DepartmentsPage() {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)

  const { data, isLoading } = useDepartments(includeInactive)
  const createMutation = useCreateDepartment()
  const updateMutation = useUpdateDepartment()
  const deactivateMutation = useDeactivateDepartment()

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, payload: form })
        toast.success('Department updated.')
      } else {
        await createMutation.mutateAsync(form)
        toast.success('Department created.')
      }
      resetForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save department.'))
    }
  }

  const handleEdit = (department: NonNullable<typeof data>[number]) => {
    setEditingId(department.id)
    setForm({ name: department.name, description: department.description })
  }

  const handleDeactivate = async (id: string) => {
    if (!window.confirm('Deactivate this department?')) return
    try {
      await deactivateMutation.mutateAsync(id)
      toast.success('Department deactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to deactivate department.'))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Master data"
        title="Departments"
        description="Define the organisation structure employees will belong to."
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title={editingId ? 'Edit department' : 'Add department'} description="Use unique department names for reporting and assignment.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="department-name">
                Department name
              </label>
              <input
                id="department-name"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                className="field-input"
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="department-description">
                Description
              </label>
              <textarea
                id="department-description"
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                className="field-textarea"
              />
            </div>
            <div className="flex flex-wrap gap-3">
              {editingId ? <button type="button" onClick={resetForm} className="btn-secondary">Cancel</button> : null}
              <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                {editingId ? 'Save changes' : 'Create department'}
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard
          title="Department directory"
          description="Inactive departments remain in history but cannot receive active employees."
          action={
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => setIncludeInactive(event.target.checked)}
              />
              Show inactive
            </label>
          }
        >
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-16" />
              ))}
            </div>
          ) : data && data.length > 0 ? (
            <div className="space-y-3">
              {data.map((department) => (
                <div key={department.id} className="flex flex-col gap-4 rounded-[24px] border border-slate-200 bg-slate-50 p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <Building className="h-4 w-4 text-cyan-700" />
                      <p className="font-semibold text-slate-950">{department.name}</p>
                      <StatusBadge tone={department.is_active ? 'success' : 'warning'}>
                        {department.is_active ? 'Active' : 'Inactive'}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{department.description || 'No description provided.'}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-slate-500">Updated {formatDate(department.updated_at)}</p>
                  </div>
                  <div className="flex gap-3">
                    <button type="button" onClick={() => handleEdit(department)} className="btn-secondary">
                      Edit
                    </button>
                    {department.is_active ? (
                      <button type="button" onClick={() => handleDeactivate(department.id)} className="btn-danger">
                        Deactivate
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No departments added yet.</p>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
