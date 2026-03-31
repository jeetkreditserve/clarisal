import { useState } from 'react'
import { Building } from 'lucide-react'
import { toast } from 'sonner'
import {
  useCreateDepartment,
  useDeactivateDepartment,
  useDepartments,
  useUpdateDepartment,
} from '@/hooks/useOrgAdmin'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = { name: '', description: '', parent_department_id: '' }

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
    const payload = {
      ...form,
      parent_department_id: form.parent_department_id || null,
    }
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, payload })
        toast.success('Department updated.')
      } else {
        await createMutation.mutateAsync(payload)
        toast.success('Department created.')
      }
      resetForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save department.'))
    }
  }

  const handleEdit = (department: NonNullable<typeof data>[number]) => {
    setEditingId(department.id)
    setForm({
      name: department.name,
      description: department.description,
      parent_department_id: department.parent_department_id ?? '',
    })
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
      {isLoading && !data ? (
        <SkeletonPageHeader />
      ) : (
        <PageHeader
          eyebrow="Master data"
          title="Departments"
          description="Define the organisation structure employees will belong to."
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title={editingId ? 'Edit department' : 'Add department'} description="Use unique department names and define parent-child structure where needed.">
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
            <div>
              <label className="field-label" htmlFor="department-parent">
                Parent department
              </label>
              <select
                id="department-parent"
                className="field-select"
                value={form.parent_department_id}
                onChange={(event) => setForm((current) => ({ ...current, parent_department_id: event.target.value }))}
              >
                <option value="">No parent department</option>
                {data
                  ?.filter((department) => department.is_active && department.id !== editingId)
                  .map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
              </select>
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
            <label className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
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
            <SkeletonTable rows={5} />
          ) : data && data.length > 0 ? (
            <div className="space-y-3">
              {data.map((department) => (
                <div key={department.id} className="surface-muted flex flex-col gap-4 rounded-[24px] p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <Building className="h-4 w-4 text-[hsl(var(--brand))]" />
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{department.name}</p>
                      <StatusBadge tone={department.is_active ? 'success' : 'warning'}>
                        {department.is_active ? 'Active' : 'Inactive'}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {department.description || 'No description provided.'}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                      Parent {department.parent_department_name || 'Top level'}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Updated {formatDate(department.updated_at)}</p>
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
            <EmptyState
              title="No departments added yet"
              description="Create the first department so employees can be grouped for reporting and assignment."
              icon={Building}
            />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
