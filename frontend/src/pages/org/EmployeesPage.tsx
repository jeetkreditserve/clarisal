import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, UserPlus } from 'lucide-react'
import { toast } from 'sonner'

import { AppDialog } from '@/components/ui/AppDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useDepartments,
  useDesignations,
  useEmployees,
  useInviteEmployee,
  useLocations,
  useOnboardingDocumentTypes,
} from '@/hooks/useOrgAdmin'
import { EMPLOYEE_STATUS_OPTIONS, EMPLOYMENT_TYPE_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { formatDate, startCase } from '@/lib/format'
import { getEmployeeStatusTone } from '@/lib/status'
import type { EmployeeStatus, EmploymentType } from '@/types/hr'

const inviteDefaults = {
  company_email: '',
  first_name: '',
  last_name: '',
  designation: '',
  employment_type: 'FULL_TIME' as EmploymentType,
  date_of_joining: '',
  department_id: '',
  office_location_id: '',
}

const EMPLOYMENT_TYPE_SELECT_OPTIONS = EMPLOYMENT_TYPE_OPTIONS.map((type) => ({
  value: type,
  label: startCase(type),
}))

const EMPLOYEE_STATUS_SELECT_OPTIONS = EMPLOYEE_STATUS_OPTIONS.map((employeeStatus) => ({
  value: employeeStatus,
  label: employeeStatus ? startCase(employeeStatus) : 'All statuses',
}))

export function EmployeesPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<EmployeeStatus | ''>('')
  const [page, setPage] = useState(1)
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false)
  const [inviteForm, setInviteForm] = useState(inviteDefaults)
  const [selectedDocumentTypeIds, setSelectedDocumentTypeIds] = useState<string[]>([])
  const [inviteFieldErrors, setInviteFieldErrors] = useState<Record<string, string>>({})

  const { data, isLoading } = useEmployees({
    search: search || undefined,
    status: status || undefined,
    page,
  })
  const { data: departments } = useDepartments()
  const { data: locations } = useLocations()
  const { data: designations } = useDesignations()
  const { data: documentTypes } = useOnboardingDocumentTypes()
  const inviteMutation = useInviteEmployee()

  const handleInvite = async (event: React.FormEvent) => {
    event.preventDefault()
    setInviteFieldErrors({})
    try {
      await inviteMutation.mutateAsync({
        ...inviteForm,
        date_of_joining: inviteForm.date_of_joining || null,
        department_id: inviteForm.department_id || null,
        office_location_id: inviteForm.office_location_id || null,
        required_document_type_ids: selectedDocumentTypeIds,
      })
      toast.success('Employee invited.')
      setInviteForm(inviteDefaults)
      setSelectedDocumentTypeIds([])
      setIsInviteModalOpen(false)
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setInviteFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to invite employee.'))
      }
    }
  }

  return (
    <div className="space-y-6">
      {isLoading && !data ? (
        <SkeletonPageHeader />
      ) : (
        <PageHeader
          eyebrow="Workforce"
          title="Employees"
          description="Invite employees, define onboarding documents, and manage lifecycle progression from invite to active join."
          actions={
            <button onClick={() => setIsInviteModalOpen(true)} className="btn-primary">
              <UserPlus className="h-4 w-4" />
              Invite employee
            </button>
          }
        />
      )}

      <SectionCard title="Employee directory" description="Search by name or email and filter by lifecycle state.">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row">
          <div className="relative max-w-xl flex-1">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
            <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} className="field-input pl-11" placeholder="Search employees by name or email" />
          </div>
          <AppSelect
            value={status}
            onValueChange={(value) => {
              setStatus(value as EmployeeStatus | '')
              setPage(1)
            }}
            options={EMPLOYEE_STATUS_SELECT_OPTIONS}
            triggerClassName="max-w-xs"
          />
        </div>

        {isLoading ? (
          <SkeletonTable rows={6} />
        ) : data && data.results.length > 0 ? (
          <>
            <div className="table-shell">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="table-head-row">
                    <th className="pb-3 pr-4 font-semibold">Employee</th>
                    <th className="pb-3 pr-4 font-semibold">Designation</th>
                    <th className="pb-3 pr-4 font-semibold">Department</th>
                    <th className="pb-3 pr-4 font-semibold">Location</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Joined</th>
                    <th className="pb-3 text-right font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="table-body">
                  {data.results.map((employee) => (
                    <tr key={employee.id} className="table-row border-b border-[hsl(var(--border)_/_0.76)] last:border-b-0">
                      <td className="py-4 pr-4">
                        <p className="table-primary font-semibold">{employee.full_name}</p>
                        <p className="table-secondary mt-1 text-xs">
                          {employee.email}
                          {employee.employee_code ? ` • ${employee.employee_code}` : ' • Code assigned on join'}
                        </p>
                      </td>
                      <td className="table-secondary py-4 pr-4">{employee.designation || 'Not assigned'}</td>
                      <td className="table-secondary py-4 pr-4">{employee.department_name || 'Unassigned'}</td>
                      <td className="table-secondary py-4 pr-4">{employee.office_location_name || 'Unassigned'}</td>
                      <td className="py-4 pr-4">
                        <StatusBadge tone={getEmployeeStatusTone(employee.status)}>{employee.status}</StatusBadge>
                      </td>
                      <td className="table-secondary py-4 pr-4">{formatDate(employee.date_of_joining)}</td>
                      <td className="py-4 text-right">
                        <Link to={`/org/employees/${employee.id}`} className="font-semibold text-[hsl(var(--brand))] hover:underline">
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {data.count > 20 ? (
              <div className="mt-5 flex items-center justify-between text-sm text-[hsl(var(--muted-foreground))]">
                <span>Page {page}</span>
                <div className="flex gap-2">
                  <button type="button" className="btn-secondary disabled:opacity-40" disabled={!data.previous} onClick={() => setPage((current) => Math.max(1, current - 1))}>
                    Previous
                  </button>
                  <button type="button" className="btn-secondary disabled:opacity-40" disabled={!data.next} onClick={() => setPage((current) => current + 1)}>
                    Next
                  </button>
                </div>
              </div>
            ) : null}
          </>
        ) : (
          <EmptyState title="No employees match the current filter" description="Adjust the filters or send the first invite to begin employee onboarding." icon={UserPlus} />
        )}
      </SectionCard>

      <AppDialog
        open={isInviteModalOpen}
        onOpenChange={(open) => {
          setIsInviteModalOpen(open)
          if (!open) {
            setInviteForm(inviteDefaults)
            setSelectedDocumentTypeIds([])
            setInviteFieldErrors({})
          }
        }}
        title="Invite employee"
        description="Invites consume licence capacity immediately, so collect only the documents you genuinely need for onboarding."
        contentClassName="sm:w-[min(92vw,64rem)]"
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setIsInviteModalOpen(false)
                setInviteForm(inviteDefaults)
                setSelectedDocumentTypeIds([])
                setInviteFieldErrors({})
              }}
            >
              Cancel
            </button>
            <button type="submit" form="invite-employee-form" className="btn-primary" disabled={inviteMutation.isPending}>
              {inviteMutation.isPending ? 'Sending invite...' : 'Invite employee'}
            </button>
          </div>
        }
      >
        <form id="invite-employee-form" onSubmit={handleInvite} className="grid gap-4 lg:grid-cols-3">
          <div>
            <label className="field-label" htmlFor="first_name">
              First name
            </label>
            <input
              id="first_name"
              type="text"
              className="field-input"
              required
              value={inviteForm.first_name}
              onChange={(event) => setInviteForm((current) => ({ ...current, first_name: event.target.value }))}
            />
            <FieldErrorText message={inviteFieldErrors.first_name} />
          </div>
          <div>
            <label className="field-label" htmlFor="last_name">
              Last name
            </label>
            <input
              id="last_name"
              type="text"
              className="field-input"
              required
              value={inviteForm.last_name}
              onChange={(event) => setInviteForm((current) => ({ ...current, last_name: event.target.value }))}
            />
            <FieldErrorText message={inviteFieldErrors.last_name} />
          </div>
          <div>
            <label className="field-label" htmlFor="company_email">
              Company email
            </label>
            <input
              id="company_email"
              type="email"
              className="field-input"
              required
              value={inviteForm.company_email}
              onChange={(event) => setInviteForm((current) => ({ ...current, company_email: event.target.value }))}
            />
            <FieldErrorText message={inviteFieldErrors.company_email} />
          </div>
          <div>
            <label className="field-label" htmlFor="designation">
              Designation
            </label>
            <AppSelect
              id="designation"
              value={inviteForm.designation}
              onValueChange={(value) => setInviteForm((current) => ({ ...current, designation: value }))}
              options={[
                { value: '', label: 'Select designation' },
                ...(designations?.map((d) => ({ value: d.name, label: d.name })) ?? []),
              ]}
              placeholder="Select designation"
            />
            <FieldErrorText message={inviteFieldErrors.designation} />
          </div>
          <div>
            <label className="field-label" htmlFor="employment-type">
              Employment type
            </label>
            <AppSelect
              id="employment-type"
              value={inviteForm.employment_type}
              onValueChange={(value) =>
                setInviteForm((current) => ({ ...current, employment_type: value as EmploymentType }))
              }
              options={EMPLOYMENT_TYPE_SELECT_OPTIONS}
            />
            <FieldErrorText message={inviteFieldErrors.employment_type} />
          </div>
          <div>
            <label className="field-label" htmlFor="date-of-joining">
              Planned joining date
            </label>
            <AppDatePicker
              id="date-of-joining"
              value={inviteForm.date_of_joining}
              onValueChange={(value) => setInviteForm((current) => ({ ...current, date_of_joining: value }))}
              placeholder="Select planned joining date"
            />
            <FieldErrorText message={inviteFieldErrors.date_of_joining} />
          </div>
          <div>
            <label className="field-label" htmlFor="department">
              Department
            </label>
            <AppSelect
              id="department"
              value={inviteForm.department_id}
              onValueChange={(value) => setInviteForm((current) => ({ ...current, department_id: value }))}
              placeholder="Unassigned"
              options={[
                { value: '', label: 'Unassigned' },
                ...(departments?.filter((department) => department.is_active).map((department) => ({
                  value: department.id,
                  label: department.name,
                })) ?? []),
              ]}
            />
            <FieldErrorText message={inviteFieldErrors.department_id} />
          </div>
          <div>
            <label className="field-label" htmlFor="location">
              Office location
            </label>
            <AppSelect
              id="location"
              value={inviteForm.office_location_id}
              onValueChange={(value) =>
                setInviteForm((current) => ({ ...current, office_location_id: value }))
              }
              placeholder="Unassigned"
              options={[
                { value: '', label: 'Unassigned' },
                ...(locations?.filter((location) => location.is_active).map((location) => ({
                  value: location.id,
                  label: location.name,
                })) ?? []),
              ]}
            />
            <FieldErrorText message={inviteFieldErrors.office_location_id} />
          </div>
          <div className="lg:col-span-3">
            <p className="mb-3 text-sm font-semibold text-[hsl(var(--foreground-strong))]">Requested onboarding documents</p>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {documentTypes?.map((documentType) => (
                <AppCheckbox
                  key={documentType.id}
                  id={`document-type-${documentType.id}`}
                  checked={selectedDocumentTypeIds.includes(documentType.id)}
                  onCheckedChange={(checked) =>
                    setSelectedDocumentTypeIds((current) =>
                      checked ? [...current, documentType.id] : current.filter((item) => item !== documentType.id),
                    )
                  }
                  label={documentType.name}
                  description={documentType.category.replace(/_/g, ' ')}
                />
              ))}
            </div>
          </div>
          <div className="surface-muted rounded-[26px] p-5 text-sm leading-6 text-[hsl(var(--muted-foreground))] lg:col-span-3">
            Employee codes are assigned only when you mark a pending employee as joined. If the invite is accepted but the employee never joins, you do not waste a code.
          </div>
        </form>
      </AppDialog>
    </div>
  )
}
