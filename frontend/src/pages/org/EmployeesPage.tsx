import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, UserPlus } from 'lucide-react'
import { toast } from 'sonner'
import { useDepartments, useEmployees, useInviteEmployee, useLocations } from '@/hooks/useOrgAdmin'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate, startCase } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'
import { getEmployeeStatusTone } from '@/lib/status'
import type { EmployeeStatus, EmploymentType } from '@/types/hr'

const employeeStatuses: Array<EmployeeStatus | ''> = ['', 'INVITED', 'ACTIVE', 'INACTIVE', 'TERMINATED']

const inviteDefaults = {
  email: '',
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

  const { data, isLoading } = useEmployees({
    search: search || undefined,
    status: status || undefined,
    page,
  })
  const { data: departments } = useDepartments()
  const { data: locations } = useLocations()
  const inviteMutation = useInviteEmployee()

  const handleInvite = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await inviteMutation.mutateAsync({
        ...inviteForm,
        date_of_joining: inviteForm.date_of_joining || null,
        department_id: inviteForm.department_id || null,
        office_location_id: inviteForm.office_location_id || null,
      })
      toast.success('Employee invited.')
      setInviteForm(inviteDefaults)
      setShowInviteForm(false)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to invite employee.'))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workforce"
        title="Employees"
        description="Invite employees, monitor activation state, and manage assignments."
        actions={
          <button onClick={() => setShowInviteForm((current) => !current)} className="btn-primary">
            <UserPlus className="h-4 w-4" />
            {showInviteForm ? 'Close invite form' : 'Invite employee'}
          </button>
        }
      />

      {showInviteForm ? (
        <SectionCard title="Invite employee" description="Seat availability is enforced server-side against purchased licences.">
          <form onSubmit={handleInvite} className="grid gap-4 lg:grid-cols-3">
            {[
              ['email', 'Email'],
              ['first_name', 'First name'],
              ['last_name', 'Last name'],
              ['designation', 'Designation'],
            ].map(([field, label]) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {label}
                </label>
                <input
                  id={field}
                  type={field === 'email' ? 'email' : 'text'}
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
              <select
                id="employment-type"
                className="field-select"
                value={inviteForm.employment_type}
                onChange={(event) => setInviteForm((current) => ({ ...current, employment_type: event.target.value as EmploymentType }))}
              >
                {['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN'].map((type) => (
                  <option key={type} value={type}>
                    {startCase(type)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="date-of-joining">
                Joining date
              </label>
              <input
                id="date-of-joining"
                type="date"
                className="field-input"
                value={inviteForm.date_of_joining}
                onChange={(event) => setInviteForm((current) => ({ ...current, date_of_joining: event.target.value }))}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="department">
                Department
              </label>
              <select
                id="department"
                className="field-select"
                value={inviteForm.department_id}
                onChange={(event) => setInviteForm((current) => ({ ...current, department_id: event.target.value }))}
              >
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
              <select
                id="location"
                className="field-select"
                value={inviteForm.office_location_id}
                onChange={(event) => setInviteForm((current) => ({ ...current, office_location_id: event.target.value }))}
              >
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
          </form>
        </SectionCard>
      ) : null}

      <SectionCard title="Employee directory" description="Search by name or email and filter by lifecycle state.">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row">
          <div className="relative max-w-xl flex-1">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
              className="field-input pl-11"
              placeholder="Search employees by name or email"
            />
          </div>
          <select
            className="field-select max-w-xs"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as EmployeeStatus | '')
              setPage(1)
            }}
          >
            {employeeStatuses.map((employeeStatus) => (
              <option key={employeeStatus} value={employeeStatus}>
                {employeeStatus ? startCase(employeeStatus) : 'All statuses'}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-16" />
            ))}
          </div>
        ) : data && data.results.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.16em] text-slate-500">
                    <th className="pb-3 pr-4 font-semibold">Employee</th>
                    <th className="pb-3 pr-4 font-semibold">Designation</th>
                    <th className="pb-3 pr-4 font-semibold">Department</th>
                    <th className="pb-3 pr-4 font-semibold">Location</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Joined</th>
                    <th className="pb-3 text-right font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/80">
                  {data.results.map((employee) => (
                    <tr key={employee.id}>
                      <td className="py-4 pr-4">
                        <p className="font-semibold text-slate-950">{employee.full_name}</p>
                        <p className="mt-1 text-xs text-slate-500">{employee.email} • {employee.employee_code}</p>
                      </td>
                      <td className="py-4 pr-4 text-slate-600">{employee.designation || 'Not assigned'}</td>
                      <td className="py-4 pr-4 text-slate-600">{employee.department_name || 'Unassigned'}</td>
                      <td className="py-4 pr-4 text-slate-600">{employee.office_location_name || 'Unassigned'}</td>
                      <td className="py-4 pr-4">
                        <StatusBadge tone={getEmployeeStatusTone(employee.status)}>{employee.status}</StatusBadge>
                      </td>
                      <td className="py-4 pr-4 text-slate-600">{formatDate(employee.date_of_joining)}</td>
                      <td className="py-4 text-right">
                        <Link to={`/org/employees/${employee.id}`} className="font-semibold text-[hsl(var(--primary))] hover:underline">
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {data.count > 20 ? (
              <div className="mt-5 flex items-center justify-between text-sm text-slate-600">
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
          <p className="text-sm text-slate-500">No employees match the current filter.</p>
        )}
      </SectionCard>
    </div>
  )
}
