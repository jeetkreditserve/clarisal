import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, FileCheck2, UserRoundCheck, UserRoundMinus } from 'lucide-react'
import { toast } from 'sonner'

import {
  useDeleteEmployee,
  useDepartments,
  useEmployeeDetail,
  useEmployeeDocumentDownload,
  useEmployeeDocuments,
  useEndEmployeeEmployment,
  useLocations,
  useMarkEmployeeJoined,
  useRejectEmployeeDocument,
  useUpdateEmployee,
  useVerifyEmployeeDocument,
} from '@/hooks/useOrgAdmin'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDateTime, startCase } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'
import { getDocumentStatusTone, getEmployeeStatusTone } from '@/lib/status'
import type { EmploymentType } from '@/types/hr'

export function EmployeeDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const employeeId = id ?? ''
  const { data: employee, isLoading } = useEmployeeDetail(employeeId)
  const { data: departments } = useDepartments()
  const { data: locations } = useLocations()
  const { data: documents } = useEmployeeDocuments(employeeId)
  const updateMutation = useUpdateEmployee(employeeId)
  const markJoinedMutation = useMarkEmployeeJoined(employeeId)
  const endEmploymentMutation = useEndEmployeeEmployment(employeeId)
  const deleteEmployeeMutation = useDeleteEmployee(employeeId)
  const verifyDocumentMutation = useVerifyEmployeeDocument(employeeId)
  const rejectDocumentMutation = useRejectEmployeeDocument(employeeId)
  const downloadDocumentMutation = useEmployeeDocumentDownload()

  const [draft, setDraft] = useState<Partial<{
    designation: string
    employment_type: EmploymentType
    date_of_joining: string
    department_id: string
    office_location_id: string
  }>>({})
  const [joinForm, setJoinForm] = useState({
    employee_code: '',
    date_of_joining: '',
  })
  const [endEmploymentForm, setEndEmploymentForm] = useState({
    status: 'RESIGNED' as 'RESIGNED' | 'RETIRED' | 'TERMINATED',
    date_of_exit: '',
  })

  if (isLoading || !employee) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonFormBlock rows={6} />
        <div className="grid gap-6 xl:grid-cols-2">
          <SkeletonTable rows={5} />
          <SkeletonTable rows={5} />
        </div>
      </div>
    )
  }

  const formValues = {
    designation: draft.designation ?? employee.designation ?? '',
    employment_type: draft.employment_type ?? employee.employment_type,
    date_of_joining: draft.date_of_joining ?? employee.date_of_joining ?? '',
    department_id: draft.department_id ?? employee.department ?? '',
    office_location_id: draft.office_location_id ?? employee.office_location ?? '',
  }

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await updateMutation.mutateAsync({
        designation: formValues.designation,
        employment_type: formValues.employment_type,
        date_of_joining: formValues.date_of_joining || null,
        department_id: formValues.department_id || null,
        office_location_id: formValues.office_location_id || null,
      })
      toast.success('Employee updated.')
      setDraft({})
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update employee.'))
    }
  }

  const handleMarkJoined = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await markJoinedMutation.mutateAsync({
        employee_code: joinForm.employee_code || employee.suggested_employee_code,
        date_of_joining: joinForm.date_of_joining || formValues.date_of_joining,
      })
      toast.success('Employee marked as joined.')
      setJoinForm({ employee_code: '', date_of_joining: '' })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to mark employee as joined.'))
    }
  }

  const handleEndEmployment = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await endEmploymentMutation.mutateAsync(endEmploymentForm)
      toast.success('Employment ended.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to end employment.'))
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete this invited or pending employee record?')) return
    try {
      await deleteEmployeeMutation.mutateAsync()
      toast.success('Employee deleted.')
      navigate('/org/employees')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to delete employee.'))
    }
  }

  const handleVerifyDocument = async (documentId: string) => {
    try {
      await verifyDocumentMutation.mutateAsync(documentId)
      toast.success('Document verified.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to verify document.'))
    }
  }

  const handleRejectDocument = async (documentId: string) => {
    const note = window.prompt('Add a rejection note for the employee:', '')
    if (note === null) return
    try {
      await rejectDocumentMutation.mutateAsync({ documentId, note })
      toast.success('Document rejected.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to reject document.'))
    }
  }

  const handleDownload = async (documentId: string) => {
    try {
      const response = await downloadDocumentMutation.mutateAsync({ employeeId, documentId })
      window.open(response.url, '_blank', 'noopener,noreferrer')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to open document.'))
    }
  }

  const employeeCodeLabel = employee.employee_code ?? 'Code assigned on join'

  return (
    <div className="space-y-6">
      <Link to="/org/employees" className="inline-flex items-center gap-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]">
        <ArrowLeft className="h-4 w-4" />
        Back to employees
      </Link>

      <PageHeader
        eyebrow="Employee detail"
        title={employee.full_name}
        description={`${employeeCodeLabel} • ${employee.email}`}
        actions={<StatusBadge tone={getEmployeeStatusTone(employee.status)}>{employee.status}</StatusBadge>}
      />

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <SectionCard title="Employment settings" description="Assignment details stay editable across invited, pending, and active states.">
          <form onSubmit={handleSave} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="designation">
                Designation
              </label>
              <input
                id="designation"
                className="field-input"
                value={formValues.designation}
                onChange={(event) => setDraft((current) => ({ ...current, designation: event.target.value }))}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="employment-type">
                  Employment type
                </label>
                <select
                  id="employment-type"
                  className="field-select"
                  value={formValues.employment_type}
                  onChange={(event) => setDraft((current) => ({ ...current, employment_type: event.target.value as EmploymentType }))}
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
                  Date of joining
                </label>
                <input
                  id="date-of-joining"
                  type="date"
                  className="field-input"
                  value={formValues.date_of_joining}
                  onChange={(event) => setDraft((current) => ({ ...current, date_of_joining: event.target.value }))}
                />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="department">
                  Department
                </label>
                <select
                  id="department"
                  className="field-select"
                  value={formValues.department_id}
                  onChange={(event) => setDraft((current) => ({ ...current, department_id: event.target.value }))}
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
                <label className="field-label" htmlFor="office-location">
                  Office location
                </label>
                <select
                  id="office-location"
                  className="field-select"
                  value={formValues.office_location_id}
                  onChange={(event) => setDraft((current) => ({ ...current, office_location_id: event.target.value }))}
                >
                  <option value="">Unassigned</option>
                  {locations?.filter((location) => location.is_active).map((location) => (
                    <option key={location.id} value={location.id}>
                      {location.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={updateMutation.isPending}>
              Save employee changes
            </button>
          </form>

          <div className="mt-6 grid gap-4">
            {employee.status === 'PENDING' ? (
              <form onSubmit={handleMarkJoined} className="surface-muted grid gap-4 rounded-[24px] p-5">
                <div className="flex items-center gap-2">
                  <UserRoundCheck className="h-4 w-4 text-[hsl(var(--success))]" />
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">Mark employee as joined</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="field-label" htmlFor="employee-code">
                      Employee code
                    </label>
                    <input
                      id="employee-code"
                      className="field-input"
                      placeholder={employee.suggested_employee_code}
                      value={joinForm.employee_code}
                      onChange={(event) => setJoinForm((current) => ({ ...current, employee_code: event.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="field-label" htmlFor="join-date">
                      Date of joining
                    </label>
                    <input
                      id="join-date"
                      type="date"
                      className="field-input"
                      value={joinForm.date_of_joining}
                      onChange={(event) => setJoinForm((current) => ({ ...current, date_of_joining: event.target.value }))}
                    />
                  </div>
                </div>
                <button type="submit" className="btn-primary" disabled={markJoinedMutation.isPending}>
                  Mark as joined
                </button>
              </form>
            ) : null}

            {employee.status === 'ACTIVE' ? (
              <form onSubmit={handleEndEmployment} className="surface-muted grid gap-4 rounded-[24px] p-5">
                <div className="flex items-center gap-2">
                  <UserRoundMinus className="h-4 w-4 text-[hsl(var(--warning))]" />
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">End employment</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="field-label" htmlFor="end-status">
                      End status
                    </label>
                    <select
                      id="end-status"
                      className="field-select"
                      value={endEmploymentForm.status}
                      onChange={(event) =>
                        setEndEmploymentForm((current) => ({
                          ...current,
                          status: event.target.value as 'RESIGNED' | 'RETIRED' | 'TERMINATED',
                        }))
                      }
                    >
                      {['RESIGNED', 'RETIRED', 'TERMINATED'].map((status) => (
                        <option key={status} value={status}>
                          {startCase(status)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="field-label" htmlFor="date-of-exit">
                      Date of exit
                    </label>
                    <input
                      id="date-of-exit"
                      type="date"
                      className="field-input"
                      value={endEmploymentForm.date_of_exit}
                      onChange={(event) => setEndEmploymentForm((current) => ({ ...current, date_of_exit: event.target.value }))}
                    />
                  </div>
                </div>
                <button type="submit" className="btn-danger" disabled={endEmploymentMutation.isPending}>
                  End employment
                </button>
              </form>
            ) : null}

            {(employee.status === 'INVITED' || employee.status === 'PENDING') ? (
              <div className="surface-muted rounded-[24px] p-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">Delete employee record</p>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                  Invited and pending employees can be deleted and their licence seat will be released.
                </p>
                <button onClick={handleDelete} className="btn-danger mt-4" disabled={deleteEmployeeMutation.isPending}>
                  Delete employee
                </button>
              </div>
            ) : null}
          </div>
        </SectionCard>

        <SectionCard title="Profile snapshot" description="Current self-service details, identity records, and bank setup.">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ['Phone', employee.profile.phone_personal || 'Not provided'],
              ['Emergency contact', employee.profile.emergency_contact_name || 'Not provided'],
              ['Emergency relation', employee.profile.emergency_contact_relation || 'Not provided'],
              ['Address', [employee.profile.address_line1, employee.profile.city, employee.profile.state, employee.profile.country].filter(Boolean).join(', ') || 'Not provided'],
            ].map(([label, value]) => (
              <div key={label} className="surface-muted rounded-[24px] p-5">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{label}</p>
                <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <div>
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Government IDs</p>
              <div className="mt-3 space-y-3">
                {employee.government_ids.length > 0 ? (
                  employee.government_ids.map((record) => (
                    <div key={record.id} className="surface-shell rounded-[20px] px-4 py-3">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-[hsl(var(--foreground-strong))]">{record.id_type}</p>
                        <StatusBadge tone={record.status === 'VERIFIED' ? 'success' : record.status === 'REJECTED' ? 'danger' : 'warning'}>
                          {record.status}
                        </StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{record.identifier}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">No government IDs submitted yet.</p>
                )}
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Bank accounts</p>
              <div className="mt-3 space-y-3">
                {employee.bank_accounts.length > 0 ? (
                  employee.bank_accounts.map((account) => (
                    <div key={account.id} className="surface-shell rounded-[20px] px-4 py-3">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-[hsl(var(--foreground-strong))]">{account.bank_name || 'Bank account'}</p>
                        {account.is_primary ? <StatusBadge tone="success">Primary</StatusBadge> : null}
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {account.account_holder_name} • {account.account_number} • {account.ifsc}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">No bank accounts submitted yet.</p>
                )}
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Documents" description="Review and act on employee-uploaded documents.">
        {documents && documents.length > 0 ? (
          <div className="table-shell">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Document</th>
                  <th className="pb-3 pr-4 font-semibold">Status</th>
                  <th className="pb-3 pr-4 font-semibold">Uploaded</th>
                  <th className="pb-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {documents.map((document) => (
                  <tr key={document.id} className="table-row border-b border-[hsl(var(--border)_/_0.76)] last:border-b-0">
                    <td className="py-4 pr-4">
                      <p className="table-primary font-semibold">{startCase(document.document_type)}</p>
                      <p className="table-secondary mt-1 text-xs">{document.file_name}</p>
                    </td>
                    <td className="py-4 pr-4">
                      <StatusBadge tone={getDocumentStatusTone(document.status)}>{document.status}</StatusBadge>
                    </td>
                    <td className="table-secondary py-4 pr-4">{formatDateTime(document.created_at)}</td>
                    <td className="py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button type="button" onClick={() => handleDownload(document.id)} className="btn-secondary">
                          <Download className="h-4 w-4" />
                          Open
                        </button>
                        {document.status !== 'VERIFIED' ? (
                          <button type="button" onClick={() => handleVerifyDocument(document.id)} className="btn-primary">
                            <FileCheck2 className="h-4 w-4" />
                            Verify
                          </button>
                        ) : null}
                        {document.status !== 'REJECTED' ? (
                          <button type="button" onClick={() => handleRejectDocument(document.id)} className="btn-danger">
                            Reject
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No documents uploaded yet"
            description="This employee has not submitted any files for review yet."
            icon={FileCheck2}
          />
        )}
      </SectionCard>
    </div>
  )
}
