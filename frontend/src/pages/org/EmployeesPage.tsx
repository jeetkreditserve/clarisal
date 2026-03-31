import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, UserPlus } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useDepartments,
  useEmployees,
  useInviteEmployee,
  useLocations,
  useOnboardingDocumentTypes,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, startCase } from '@/lib/format'
import { getEmployeeStatusTone } from '@/lib/status'
import type { EmployeeStatus, EmploymentType } from '@/types/hr'

const employeeStatuses: Array<EmployeeStatus | ''> = ['', 'INVITED', 'PENDING', 'ACTIVE', 'RESIGNED', 'RETIRED', 'TERMINATED']

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

export function EmployeesPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<EmployeeStatus | ''>('')
  const [page, setPage] = useState(1)
  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteForm, setInviteForm] = useState(inviteDefaults)
  const [selectedDocumentTypeIds, setSelectedDocumentTypeIds] = useState<string[]>([])

  const { data, isLoading } = useEmployees({
    search: search || undefined,
    status: status || undefined,
    page,
  })
  const { data: departments } = useDepartments()
  const { data: locations } = useLocations()
  const { data: documentTypes } = useOnboardingDocumentTypes()
  const inviteMutation = useInviteEmployee()

  const handleInvite = async (event: React.FormEvent) => {
    event.preventDefault()
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
      setShowInviteForm(false)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to invite employee.'))
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
            <button onClick={() => setShowInviteForm((current) => !current)} className="btn-primary">
              <UserPlus className="h-4 w-4" />
              {showInviteForm ? 'Close invite form' : 'Invite employee'}
            </button>
          }
        />
      )}

      {showInviteForm ? (
        <SectionCard title="Invite employee" description="Invites consume licence capacity immediately, so collect only the documents you genuinely need for onboarding.">
          <form onSubmit={handleInvite} className="grid gap-4 lg:grid-cols-3">
            {[
              ['first_name', 'First name'],
              ['last_name', 'Last name'],
              ['company_email', 'Company email'],
              ['designation', 'Designation'],
            ].map(([field, label]) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {label}
                </label>
                <input
                  id={field}
                  type={field === 'company_email' ? 'email' : 'text'}
                  className="field-input"
                  required={field !== 'designation'}
                  value={inviteForm[field as keyof typeof inviteForm]}
                  onChange={(event) => setInviteForm((current) => ({ ...current, [field]: event.target.value }))}
                />
              </div>
            ))}
            <div>
              <label className="field-label" htmlFor="employment-type">
                Employment type
              </label>
              <select id="employment-type" className="field-select" value={inviteForm.employment_type} onChange={(event) => setInviteForm((current) => ({ ...current, employment_type: event.target.value as EmploymentType }))}>
                {['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN'].map((type) => (
                  <option key={type} value={type}>
                    {startCase(type)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="date-of-joining">
                Planned joining date
              </label>
              <input id="date-of-joining" type="date" className="field-input" value={inviteForm.date_of_joining} onChange={(event) => setInviteForm((current) => ({ ...current, date_of_joining: event.target.value }))} />
            </div>
            <div>
              <label className="field-label" htmlFor="department">
                Department
              </label>
              <select id="department" className="field-select" value={inviteForm.department_id} onChange={(event) => setInviteForm((current) => ({ ...current, department_id: event.target.value }))}>
                <option value="">Unassigned</option>
                {departments?.filter((department) => department.is_active).map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="location">
                Office location
              </label>
              <select id="location" className="field-select" value={inviteForm.office_location_id} onChange={(event) => setInviteForm((current) => ({ ...current, office_location_id: event.target.value }))}>
                <option value="">Unassigned</option>
                {locations?.filter((location) => location.is_active).map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button type="submit" className="btn-primary w-full" disabled={inviteMutation.isPending}>
                {inviteMutation.isPending ? 'Sending invite...' : 'Invite employee'}
              </button>
            </div>
            <div className="lg:col-span-3">
              <p className="mb-3 text-sm font-semibold text-[hsl(var(--foreground-strong))]">Requested onboarding documents</p>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {documentTypes?.map((documentType) => (
                  <label key={documentType.id} className="surface-muted flex items-start gap-3 rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
                    <input
                      type="checkbox"
                      checked={selectedDocumentTypeIds.includes(documentType.id)}
                      onChange={(event) =>
                        setSelectedDocumentTypeIds((current) =>
                          event.target.checked ? [...current, documentType.id] : current.filter((item) => item !== documentType.id),
                        )
                      }
                    />
                    <div>
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{documentType.name}</p>
                      <p className="text-xs">{documentType.category.replace(/_/g, ' ')}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
            <div className="surface-muted rounded-[26px] p-5 text-sm leading-6 text-[hsl(var(--muted-foreground))] lg:col-span-3">
              Employee codes are assigned only when you mark a pending employee as joined. If the invite is accepted but the employee never joins, you do not waste a code.
            </div>
          </form>
        </SectionCard>
      ) : null}

      <SectionCard title="Employee directory" description="Search by name or email and filter by lifecycle state.">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row">
          <div className="relative max-w-xl flex-1">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
            <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} className="field-input pl-11" placeholder="Search employees by name or email" />
          </div>
          <select className="field-select max-w-xs" value={status} onChange={(event) => { setStatus(event.target.value as EmployeeStatus | ''); setPage(1) }}>
            {employeeStatuses.map((employeeStatus) => (
              <option key={employeeStatus} value={employeeStatus}>
                {employeeStatus ? startCase(employeeStatus) : 'All statuses'}
              </option>
            ))}
          </select>
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
    </div>
  )
}
