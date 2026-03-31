import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useDeleteEmployee,
  useDepartments,
  useEmployeeDetail,
  useEmployeeDocumentDownload,
  useEmployeeDocumentRequests,
  useEmployeeDocuments,
  useEmployees,
  useEndEmployeeEmployment,
  useLocations,
  useMarkEmployeeJoined,
  useUpdateEmployee,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { getDocumentRequestStatusTone, getDocumentStatusTone, getEmployeeStatusTone } from '@/lib/status'
import type { EmploymentType } from '@/types/hr'

export function EmployeeDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const employeeId = id ?? ''
  const { data: employee, isLoading } = useEmployeeDetail(employeeId)
  const { data: departments } = useDepartments()
  const { data: locations } = useLocations()
  const { data: managerOptions } = useEmployees({ status: 'ACTIVE', page: 1 })
  const { data: documentRequests } = useEmployeeDocumentRequests(employeeId)
  const { data: documents } = useEmployeeDocuments(employeeId)
  const updateMutation = useUpdateEmployee(employeeId)
  const markJoinedMutation = useMarkEmployeeJoined(employeeId)
  const endEmploymentMutation = useEndEmployeeEmployment(employeeId)
  const deleteEmployeeMutation = useDeleteEmployee(employeeId)
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
    designation: '',
    reporting_to_employee_id: '',
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
        <SkeletonTable rows={6} />
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
        designation: joinForm.designation || formValues.designation,
        reporting_to_employee_id: joinForm.reporting_to_employee_id || employee.id,
      })
      toast.success('Employee marked as joined.')
      setJoinForm({ employee_code: '', date_of_joining: '', designation: '', reporting_to_employee_id: '' })
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
        description={`${employee.email} • ${employee.employee_code || 'Code assigned on join'}`}
        actions={
          <div className="flex items-center gap-3">
            <StatusBadge tone={getEmployeeStatusTone(employee.status)}>{employee.status}</StatusBadge>
            <StatusBadge tone={employee.onboarding_status === 'COMPLETE' ? 'success' : 'warning'}>
              {employee.onboarding_status}
            </StatusBadge>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Employment settings" description="Assignments stay editable while the employee progresses through invited, pending, active, and end-of-employment states.">
          <form onSubmit={handleSave} className="grid gap-4">
            <input className="field-input" value={formValues.designation} onChange={(event) => setDraft((current) => ({ ...current, designation: event.target.value }))} placeholder="Designation" />
            <div className="grid gap-4 md:grid-cols-2">
              <select className="field-select" value={formValues.employment_type} onChange={(event) => setDraft((current) => ({ ...current, employment_type: event.target.value as EmploymentType }))}>
                {['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN'].map((type) => (
                  <option key={type} value={type}>
                    {type.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
              <input className="field-input" type="date" value={formValues.date_of_joining} onChange={(event) => setDraft((current) => ({ ...current, date_of_joining: event.target.value }))} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <select className="field-select" value={formValues.department_id} onChange={(event) => setDraft((current) => ({ ...current, department_id: event.target.value }))}>
                <option value="">Unassigned department</option>
                {departments?.filter((department) => department.is_active).map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
              <select className="field-select" value={formValues.office_location_id} onChange={(event) => setDraft((current) => ({ ...current, office_location_id: event.target.value }))}>
                <option value="">Unassigned location</option>
                {locations?.filter((location) => location.is_active).map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn-primary" disabled={updateMutation.isPending}>
              Save employee changes
            </button>
          </form>

          <div className="mt-6 grid gap-4">
            {employee.status === 'PENDING' ? (
              <form onSubmit={handleMarkJoined} className="surface-muted grid gap-4 rounded-[24px] p-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">Mark employee as joined</p>
                <input className="field-input" placeholder={employee.suggested_employee_code} value={joinForm.employee_code} onChange={(event) => setJoinForm((current) => ({ ...current, employee_code: event.target.value }))} />
                <div className="grid gap-4 md:grid-cols-2">
                  <input className="field-input" type="date" value={joinForm.date_of_joining} onChange={(event) => setJoinForm((current) => ({ ...current, date_of_joining: event.target.value }))} />
                  <input className="field-input" placeholder={formValues.designation || 'Designation'} value={joinForm.designation} onChange={(event) => setJoinForm((current) => ({ ...current, designation: event.target.value }))} />
                </div>
                <select className="field-select" value={joinForm.reporting_to_employee_id} onChange={(event) => setJoinForm((current) => ({ ...current, reporting_to_employee_id: event.target.value }))}>
                  <option value="">Use self as manager</option>
                  <option value={employee.id}>Self-managed / top-level employee</option>
                  {managerOptions?.results.map((manager) => (
                    <option key={manager.id} value={manager.id}>
                      {manager.full_name}
                    </option>
                  ))}
                </select>
                <button type="submit" className="btn-primary" disabled={markJoinedMutation.isPending}>
                  Mark as joined
                </button>
              </form>
            ) : null}

            {employee.status === 'ACTIVE' ? (
              <form onSubmit={handleEndEmployment} className="surface-muted grid gap-4 rounded-[24px] p-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">End employment</p>
                <div className="grid gap-4 md:grid-cols-2">
                  <select className="field-select" value={endEmploymentForm.status} onChange={(event) => setEndEmploymentForm((current) => ({ ...current, status: event.target.value as 'RESIGNED' | 'RETIRED' | 'TERMINATED' }))}>
                    {['RESIGNED', 'RETIRED', 'TERMINATED'].map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                  <input className="field-input" type="date" value={endEmploymentForm.date_of_exit} onChange={(event) => setEndEmploymentForm((current) => ({ ...current, date_of_exit: event.target.value }))} />
                </div>
                <button type="submit" className="btn-danger" disabled={endEmploymentMutation.isPending}>
                  End employment
                </button>
              </form>
            ) : null}

            {(employee.status === 'INVITED' || employee.status === 'PENDING') ? (
              <div className="surface-muted rounded-[24px] p-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">Delete employee record</p>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">Invited and pending employees can be deleted to release the consumed licence seat.</p>
                <button onClick={handleDelete} className="btn-danger mt-4" disabled={deleteEmployeeMutation.isPending}>
                  Delete employee
                </button>
              </div>
            ) : null}
          </div>
        </SectionCard>

        <SectionCard title="Employee snapshot" description="Onboarding checklist, profile summary, and uploaded files.">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Phone</p>
              <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">{employee.profile.phone_personal || 'Not provided'}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Address</p>
              <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                {[employee.profile.address_line1, employee.profile.city, employee.profile.state, employee.profile.country].filter(Boolean).join(', ') || 'Not provided'}
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <div className="space-y-3">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Requested documents</p>
              {documentRequests && documentRequests.length > 0 ? (
                documentRequests.map((request) => (
                  <div key={request.id} className="surface-muted rounded-[20px] px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{request.document_type.name}</p>
                      <StatusBadge tone={getDocumentRequestStatusTone(request.status)}>{request.status}</StatusBadge>
                    </div>
                    {request.rejection_note ? (
                      <p className="mt-2 text-sm text-[hsl(var(--danger))]">{request.rejection_note}</p>
                    ) : null}
                  </div>
                ))
              ) : (
                <EmptyState title="No requested documents" description="Assign onboarding documents from the employee invite or document checklist flow." />
              )}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Submitted files</p>
              {documents && documents.length > 0 ? (
                documents.map((document) => (
                  <div key={document.id} className="surface-muted flex items-center justify-between gap-3 rounded-[20px] px-4 py-3">
                    <div>
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{document.document_type}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">{document.file_name}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge tone={getDocumentStatusTone(document.status)}>{document.status}</StatusBadge>
                      <button className="btn-secondary" onClick={() => void handleDownload(document.id)}>
                        <Download className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState title="No submitted files yet" description="Uploaded documents will appear here after the employee starts their checklist." />
              )}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
