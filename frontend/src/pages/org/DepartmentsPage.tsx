import { useMemo, useState } from 'react'
import { Building } from 'lucide-react'
import { toast } from 'sonner'

import {
  useCreateDepartment,
  useDeactivateDepartment,
  useDepartments,
  useUpdateDepartment,
} from '@/hooks/useOrgAdmin'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { AppDialog } from '@/components/ui/AppDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'
import type { Department } from '@/types/hr'

const emptyForm = { name: '', description: '', parent_department_id: '' }

function DepartmentHierarchyDiagram({ departments }: { departments: Department[] }) {
  const activeDepartments = departments.filter((department) => department.is_active)
  const byParent = useMemo(() => {
    const map = new Map<string | null, Department[]>()
    activeDepartments.forEach((department) => {
      const key = department.parent_department_id ?? null
      map.set(key, [...(map.get(key) ?? []), department])
    })
    return map
  }, [activeDepartments])

  const renderBranch = (parentId: string | null, depth = 0) => {
    const children = byParent.get(parentId) ?? []
    if (!children.length) return null

    return (
      <div className={depth === 0 ? 'grid gap-3' : 'mt-3 border-l border-[hsl(var(--border)_/_0.8)] pl-4'}>
        {children.map((department) => (
          <div key={department.id} className="space-y-2">
            <div className="surface-shell rounded-[18px] px-4 py-3">
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">{department.name}</p>
              <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                {department.description || 'No description provided.'}
              </p>
            </div>
            {renderBranch(department.id, depth + 1)}
          </div>
        ))}
      </div>
    )
  }

  if (!activeDepartments.length) {
    return (
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Add departments to generate the hierarchy diagram.
      </p>
    )
  }

  return <div className="overflow-x-auto pb-1">{renderBranch(null)}</div>
}

export function DepartmentsPage() {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)

  const { data, isLoading } = useDepartments(includeInactive)
  const createMutation = useCreateDepartment()
  const updateMutation = useUpdateDepartment()
  const deactivateMutation = useDeactivateDepartment()
  const departmentOptions = [
    { value: '', label: 'No parent department' },
    ...(data
      ?.filter((department) => department.is_active && department.id !== editingId)
      .map((department) => ({
        value: department.id,
        label: department.name,
      })) ?? []),
  ]

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
    setIsModalOpen(false)
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
    setIsModalOpen(true)
  }

  const handleDeactivate = async (id: string) => {
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
          description="Define the organisation structure, maintain parent-child relationships, and review the hierarchy in a read-only diagram."
          actions={
            <button type="button" className="btn-primary" onClick={() => setIsModalOpen(true)}>
              Add department
            </button>
          }
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard
          title="Department directory"
          description="Inactive departments remain in history but cannot receive active employees."
          action={
            <AppCheckbox
              id="departments-include-inactive"
              checked={includeInactive}
              onCheckedChange={setIncludeInactive}
              label="Show inactive"
            />
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
                      Parent {department.parent_department_name || 'Top level'} • Modified {formatDate(department.modified_at)}
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <button type="button" onClick={() => handleEdit(department)} className="btn-secondary">
                      Edit
                    </button>
                    {department.is_active ? (
                      <ConfirmDialog
                        trigger={
                          <button type="button" className="btn-danger">
                            Deactivate
                          </button>
                        }
                        title="Deactivate department?"
                        description="Inactive departments stay in history but can no longer receive active employees."
                        confirmLabel="Deactivate"
                        onConfirm={() => handleDeactivate(department.id)}
                      />
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

        <SectionCard
          title="Hierarchy diagram"
          description="This view-only structure helps org admins review how departments nest inside the organisation."
        >
          <DepartmentHierarchyDiagram departments={data ?? []} />
        </SectionCard>
      </div>

      <AppDialog
        open={isModalOpen}
        onOpenChange={(open) => {
          setIsModalOpen(open)
          if (!open) {
            resetForm()
          }
        }}
        title={editingId ? 'Edit department' : 'Add department'}
        description="Create and update departments from the same modal-based flow."
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" onClick={resetForm} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" form="department-form" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingId ? 'Save changes' : 'Create department'}
            </button>
          </div>
        }
      >
        <form id="department-form" onSubmit={handleSubmit} className="grid gap-4">
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
            <AppSelect
              id="department-parent"
              value={form.parent_department_id}
              onValueChange={(value) =>
                setForm((current) => ({ ...current, parent_department_id: value }))
              }
              options={departmentOptions}
              placeholder="No parent department"
            />
          </div>
        </form>
      </AppDialog>
    </div>
  )
}
