import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Download, FileCheck2 } from 'lucide-react'
import { toast } from 'sonner'
import {
  useDepartments,
  useEmployeeDetail,
  useEmployeeDocumentDownload,
  useEmployeeDocuments,
  useLocations,
  useRejectEmployeeDocument,
  useTerminateEmployee,
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
import type { EmployeeStatus, EmploymentType } from '@/types/hr'

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const employeeId = id ?? ''
  const { data: employee, isLoading } = useEmployeeDetail(employeeId)
  const { data: departments } = useDepartments()
  const { data: locations } = useLocations()
  const { data: documents } = useEmployeeDocuments(employeeId)
  const updateMutation = useUpdateEmployee(employeeId)
  const terminateMutation = useTerminateEmployee(employeeId)
  const verifyDocumentMutation = useVerifyEmployeeDocument(employeeId)
  const rejectDocumentMutation = useRejectEmployeeDocument(employeeId)
  const downloadDocumentMutation = useEmployeeDocumentDownload()

  const [draft, setDraft] = useState<Partial<{
    designation: string
    employment_type: EmploymentType
    date_of_joining: string
    department_id: string
    office_location_id: string
    status: EmployeeStatus
  }>>({})

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
    status: draft.status ?? employee.status,
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
        status: formValues.status,
      })
      toast.success('Employee updated.')
      setDraft({})
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update employee.'))
    }
  }

  const handleTerminate = async () => {
    if (!window.confirm('Terminate this employee record?')) return
    try {
      await terminateMutation.mutateAsync()
      toast.success('Employee terminated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to terminate employee.'))
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

  return (
    <div className="space-y-6">
      <Link to="/org/employees" className="inline-flex items-center gap-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]">
        <ArrowLeft className="h-4 w-4" />
        Back to employees
      </Link>

      <PageHeader
        eyebrow="Employee detail"
        title={employee.full_name}
        description={`${employee.employee_code} • ${employee.email}`}
        actions={
          <>
            <StatusBadge tone={getEmployeeStatusTone(employee.status)}>{employee.status}</StatusBadge>
            {employee.status !== 'TERMINATED' ? (
              <button onClick={handleTerminate} className="btn-danger" disabled={terminateMutation.isPending}>
                Terminate employee
              </button>
            ) : null}
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <SectionCard title="Employment settings" description="Department, location, dates, and lifecycle state.">
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
            <div>
              <label className="field-label" htmlFor="status">
                Employee status
              </label>
              <select
                id="status"
                className="field-select"
                value={formValues.status}
                onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value as EmployeeStatus }))}
              >
                {['INVITED', 'ACTIVE', 'INACTIVE', 'TERMINATED'].map((status) => (
                  <option key={status} value={status}>
                    {startCase(status)}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn-primary" disabled={updateMutation.isPending}>
              Save employee changes
            </button>
          </form>
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
