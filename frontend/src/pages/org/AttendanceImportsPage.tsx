import { useEffect, useState } from 'react'
import { Download, FileUp, Link2, Upload } from 'lucide-react'
import { toast } from 'sonner'

import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import { EmptyState } from '@/components/ui/EmptyState'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useAttendanceDashboard,
  useAttendanceDays,
  useAttendanceImports,
  useAttendancePolicies,
  useAttendanceReport,
  useAttendanceRegularizations,
  useAttendanceSources,
  useAttendanceShiftAssignments,
  useAttendanceShifts,
  useCreateAttendancePolicy,
  useCreateAttendanceSource,
  useCreateAttendanceShift,
  useCreateAttendanceShiftAssignment,
  useDownloadAttendanceTemplate,
  useDownloadNormalizedAttendanceFile,
  useEmployees,
  useOverrideAttendanceDay,
  useUpdateAttendancePolicy,
  useUpdateAttendanceSource,
  useUploadAttendanceSheet,
  useUploadPunchSheet,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'
import { getAttendanceDayStatusTone, getAttendanceImportTone } from '@/lib/status'
import type { AttendanceDayRecord, AttendancePolicy } from '@/types/hr'

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function getRegularizationTone(status: string) {
  if (status === 'APPROVED') return 'success'
  if (status === 'PENDING') return 'warning'
  if (status === 'WITHDRAWN' || status === 'CANCELLED') return 'info'
  return 'danger'
}

function createPolicyForm(policy: AttendancePolicy | null) {
  return {
    name: policy?.name ?? 'Default Attendance Policy',
    timezone_name: policy?.timezone_name ?? 'Asia/Kolkata',
    default_start_time: policy?.default_start_time ?? '09:00:00',
    default_end_time: policy?.default_end_time ?? '18:00:00',
    grace_minutes: String(policy?.grace_minutes ?? 15),
    full_day_min_minutes: String(policy?.full_day_min_minutes ?? 480),
    half_day_min_minutes: String(policy?.half_day_min_minutes ?? 240),
    overtime_after_minutes: String(policy?.overtime_after_minutes ?? 540),
    week_off_days: (policy?.week_off_days ?? [6]).join(','),
    allow_web_punch: policy?.allow_web_punch ?? true,
    restrict_by_ip: policy?.restrict_by_ip ?? false,
    allowed_ip_ranges: (policy?.allowed_ip_ranges ?? []).join('\n'),
    restrict_by_geo: policy?.restrict_by_geo ?? false,
    allowed_geo_sites: JSON.stringify(policy?.allowed_geo_sites ?? [], null, 2),
  }
}

export function AttendanceImportsPage() {
  const today = new Date().toISOString().slice(0, 10)
  const currentMonth = new Date().toISOString().slice(0, 7)
  const [selectedDate, setSelectedDate] = useState(today)
  const [reportMonth, setReportMonth] = useState(currentMonth)
  const [dayStatusFilter, setDayStatusFilter] = useState('')
  const [attendanceFile, setAttendanceFile] = useState<File | null>(null)
  const [punchFile, setPunchFile] = useState<File | null>(null)
  const [newShift, setNewShift] = useState({
    name: '',
    start_time: '09:00',
    end_time: '18:00',
    grace_minutes: '15',
    full_day_min_minutes: '480',
    half_day_min_minutes: '240',
    overtime_after_minutes: '540',
    is_overnight: false,
  })
  const [assignment, setAssignment] = useState({
    employee_id: '',
    shift_id: '',
    start_date: today,
    end_date: '',
  })
  const [overrideDrafts, setOverrideDrafts] = useState<Record<string, { check_in: string; check_out: string; note: string }>>({})
  const [sourceForm, setSourceForm] = useState({
    name: 'Primary API Adapter',
    kind: 'API' as 'API' | 'EXCEL' | 'DEVICE',
  })

  const { data: dashboard, isLoading: dashboardLoading } = useAttendanceDashboard(selectedDate)
  const { data: attendanceDays, isLoading: daysLoading } = useAttendanceDays({ date: selectedDate, status: dayStatusFilter || undefined })
  const { data: attendanceReport, isLoading: reportLoading } = useAttendanceReport(reportMonth)
  const { data: regularizations, isLoading: regularizationLoading } = useAttendanceRegularizations('PENDING')
  const { data: policies, isLoading: policiesLoading } = useAttendancePolicies()
  const { data: sources, isLoading: sourcesLoading } = useAttendanceSources()
  const { data: shifts, isLoading: shiftsLoading } = useAttendanceShifts()
  const { data: assignments, isLoading: assignmentsLoading } = useAttendanceShiftAssignments()
  const { data: attendanceImports, isLoading: importsLoading } = useAttendanceImports()
  const { data: employees } = useEmployees({ status: 'ACTIVE', page: 1 })
  const createPolicyMutation = useCreateAttendancePolicy()
  const createSourceMutation = useCreateAttendanceSource()
  const updatePolicyMutation = useUpdateAttendancePolicy()
  const updateSourceMutation = useUpdateAttendanceSource()
  const createShiftMutation = useCreateAttendanceShift()
  const assignShiftMutation = useCreateAttendanceShiftAssignment()
  const overrideDayMutation = useOverrideAttendanceDay()
  const uploadAttendanceMutation = useUploadAttendanceSheet()
  const uploadPunchMutation = useUploadPunchSheet()
  const downloadTemplateMutation = useDownloadAttendanceTemplate()
  const downloadNormalizedMutation = useDownloadNormalizedAttendanceFile()

  const defaultPolicy = policies?.find((item) => item.is_default) ?? policies?.[0] ?? null
  const [policyForm, setPolicyForm] = useState(createPolicyForm(defaultPolicy))

  useEffect(() => {
    setPolicyForm(createPolicyForm(defaultPolicy))
  }, [defaultPolicy])

  const employeeOptions = employees?.results?.map((employee) => ({
    value: employee.id,
    label: `${employee.full_name}${employee.employee_code ? ` • ${employee.employee_code}` : ''}`,
  })) ?? []

  const shiftOptions = shifts?.map((shift) => ({
    value: shift.id,
    label: `${shift.name} • ${shift.start_time.slice(0, 5)}-${shift.end_time.slice(0, 5)}`,
  })) ?? []

  const handleTemplateDownload = async (mode: 'attendance-sheet' | 'punch-sheet') => {
    try {
      const result = await downloadTemplateMutation.mutateAsync(mode)
      triggerDownload(result.blob, result.filename)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to download the sample file.'))
    }
  }

  const handleAttendanceUpload = async () => {
    if (!attendanceFile) {
      toast.error('Choose an attendance-sheet Excel file first.')
      return
    }
    try {
      const job = await uploadAttendanceMutation.mutateAsync(attendanceFile)
      toast.success(job.status === 'POSTED' ? `Attendance imported for ${job.posted_rows} employee-day records.` : 'Attendance import failed.')
      setAttendanceFile(null)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to import the attendance sheet.'))
    }
  }

  const handlePunchUpload = async () => {
    if (!punchFile) {
      toast.error('Choose a punch-sheet Excel file first.')
      return
    }
    try {
      const job = await uploadPunchMutation.mutateAsync(punchFile)
      toast.success(job.valid_rows ? `Punch sheet normalized into ${job.valid_rows} attendance rows.` : 'Punch sheet upload failed.')
      setPunchFile(null)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to import the punch sheet.'))
    }
  }

  const handleNormalizedDownload = async (jobId: string) => {
    try {
      const result = await downloadNormalizedMutation.mutateAsync(jobId)
      triggerDownload(result.blob, result.filename)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to download the normalized attendance file.'))
    }
  }

  const handlePolicySave = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      const allowedGeoSites = policyForm.allowed_geo_sites.trim() ? JSON.parse(policyForm.allowed_geo_sites) : []
      const payload = {
        name: policyForm.name,
        timezone_name: policyForm.timezone_name,
        default_start_time: policyForm.default_start_time,
        default_end_time: policyForm.default_end_time,
        grace_minutes: Number(policyForm.grace_minutes),
        full_day_min_minutes: Number(policyForm.full_day_min_minutes),
        half_day_min_minutes: Number(policyForm.half_day_min_minutes),
        overtime_after_minutes: Number(policyForm.overtime_after_minutes),
        week_off_days: policyForm.week_off_days.split(',').map((item) => Number(item.trim())).filter((item) => !Number.isNaN(item)),
        allow_web_punch: policyForm.allow_web_punch,
        restrict_by_ip: policyForm.restrict_by_ip,
        allowed_ip_ranges: policyForm.allowed_ip_ranges.split('\n').map((item) => item.trim()).filter(Boolean),
        restrict_by_geo: policyForm.restrict_by_geo,
        allowed_geo_sites: Array.isArray(allowedGeoSites) ? allowedGeoSites : [],
        is_default: true,
        is_active: true,
      }
      if (defaultPolicy) {
        await updatePolicyMutation.mutateAsync({ id: defaultPolicy.id, payload })
      } else {
        await createPolicyMutation.mutateAsync(payload)
      }
      toast.success('Attendance policy saved.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save the attendance policy.'))
    }
  }

  const handleCreateSource = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      const source = await createSourceMutation.mutateAsync({
        name: sourceForm.name,
        kind: sourceForm.kind,
        configuration: sourceForm.kind === 'API' ? { source_id: crypto.randomUUID?.() ?? `source-${Date.now()}` } : {},
        is_active: true,
      })
      toast.success(source.raw_api_key ? `Source created. Copy API key: ${source.raw_api_key}` : 'Attendance source created.')
      setSourceForm({ name: 'Primary API Adapter', kind: 'API' })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the attendance source.'))
    }
  }

  const handleRotateSourceKey = async (id: string) => {
    try {
      const source = await updateSourceMutation.mutateAsync({ id, payload: { rotate_api_key: true } })
      toast.success(source.raw_api_key ? `New API key: ${source.raw_api_key}` : 'API key rotated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to rotate the API key.'))
    }
  }

  const handleShiftCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createShiftMutation.mutateAsync({
        name: newShift.name,
        start_time: newShift.start_time,
        end_time: newShift.end_time,
        grace_minutes: Number(newShift.grace_minutes),
        full_day_min_minutes: Number(newShift.full_day_min_minutes),
        half_day_min_minutes: Number(newShift.half_day_min_minutes),
        overtime_after_minutes: Number(newShift.overtime_after_minutes),
        is_overnight: newShift.is_overnight,
        is_active: true,
      })
      toast.success('Shift created.')
      setNewShift({
        name: '',
        start_time: '09:00',
        end_time: '18:00',
        grace_minutes: '15',
        full_day_min_minutes: '480',
        half_day_min_minutes: '240',
        overtime_after_minutes: '540',
        is_overnight: false,
      })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the shift.'))
    }
  }

  const handleShiftAssignment = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await assignShiftMutation.mutateAsync({
        employee_id: assignment.employee_id,
        shift_id: assignment.shift_id,
        start_date: assignment.start_date,
        end_date: assignment.end_date || null,
      })
      toast.success('Shift assigned.')
      setAssignment((current) => ({ ...current, employee_id: '', shift_id: '', end_date: '' }))
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to assign the shift.'))
    }
  }

  const handleDayOverride = async (day: AttendanceDayRecord) => {
    const draft = overrideDrafts[day.id] ?? {
      check_in: day.check_in_at ? new Date(day.check_in_at).toISOString().slice(11, 16) : '',
      check_out: day.check_out_at ? new Date(day.check_out_at).toISOString().slice(11, 16) : '',
      note: day.note ?? '',
    }
    try {
      await overrideDayMutation.mutateAsync({
        id: day.id,
        payload: {
          check_in: draft.check_in || null,
          check_out: draft.check_out || null,
          note: draft.note,
        },
      })
      toast.success('Attendance day updated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update the attendance day.'))
    }
  }

  if (dashboardLoading || policiesLoading || shiftsLoading || importsLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonMetricCard key={index} />
          ))}
        </div>
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Attendance"
        title="Attendance operations"
        description="Run daily attendance, maintain shifts and policies, review exceptions, and continue using Excel imports where devices or historical data still need ingestion."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => void handleTemplateDownload('attendance-sheet')}>
              <Download className="h-4 w-4" />
              Attendance sample
            </button>
            <button type="button" className="btn-secondary" onClick={() => void handleTemplateDownload('punch-sheet')}>
              <Download className="h-4 w-4" />
              Punch sample
            </button>
          </>
        }
      />

      {dashboard ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard title="Present" value={dashboard.present_count} hint={`For ${dashboard.date}`} tone="success" />
          <MetricCard title="Half day" value={dashboard.half_day_count} hint="Attendance plus half-day leave / OD." tone="info" />
          <MetricCard title="Absent" value={dashboard.absent_count} hint="No approved attendance signal for the day." tone="danger" />
          <MetricCard title="Incomplete" value={dashboard.incomplete_count} hint="Missing punch or regularization needed." tone="warning" />
          <MetricCard title="Pending regularizations" value={dashboard.pending_regularizations} hint="Approval backlog impacting attendance closure." tone="primary" />
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Default attendance policy" description="Configure the organisation-wide timing, grace, week-off, and web-punch rules.">
          <form className="grid gap-4" onSubmit={handlePolicySave}>
            <input className="field-input" value={policyForm.name} onChange={(event) => setPolicyForm((current) => ({ ...current, name: event.target.value }))} placeholder="Policy name" />
            <div className="grid gap-4 md:grid-cols-2">
              <input className="field-input" value={policyForm.timezone_name} onChange={(event) => setPolicyForm((current) => ({ ...current, timezone_name: event.target.value }))} placeholder="Timezone" />
              <div className="flex items-center gap-3 rounded-[18px] border border-[hsl(var(--border))] px-4 py-3">
                <input id="allow-web-punch" type="checkbox" checked={policyForm.allow_web_punch} onChange={(event) => setPolicyForm((current) => ({ ...current, allow_web_punch: event.target.checked }))} />
                <label htmlFor="allow-web-punch" className="text-sm font-medium text-[hsl(var(--foreground-strong))]">
                  Allow employee web punch
                </label>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <input className="field-input" type="time" value={policyForm.default_start_time.slice(0, 5)} onChange={(event) => setPolicyForm((current) => ({ ...current, default_start_time: event.target.value }))} />
              <input className="field-input" type="time" value={policyForm.default_end_time.slice(0, 5)} onChange={(event) => setPolicyForm((current) => ({ ...current, default_end_time: event.target.value }))} />
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <input className="field-input" value={policyForm.grace_minutes} onChange={(event) => setPolicyForm((current) => ({ ...current, grace_minutes: event.target.value }))} placeholder="Grace minutes" />
              <input className="field-input" value={policyForm.full_day_min_minutes} onChange={(event) => setPolicyForm((current) => ({ ...current, full_day_min_minutes: event.target.value }))} placeholder="Full-day minutes" />
              <input className="field-input" value={policyForm.half_day_min_minutes} onChange={(event) => setPolicyForm((current) => ({ ...current, half_day_min_minutes: event.target.value }))} placeholder="Half-day minutes" />
              <input className="field-input" value={policyForm.overtime_after_minutes} onChange={(event) => setPolicyForm((current) => ({ ...current, overtime_after_minutes: event.target.value }))} placeholder="OT after minutes" />
            </div>
            <input className="field-input" value={policyForm.week_off_days} onChange={(event) => setPolicyForm((current) => ({ ...current, week_off_days: event.target.value }))} placeholder="Week off days as weekday numbers, for example 6 or 5,6" />
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3 rounded-[18px] border border-[hsl(var(--border))] px-4 py-4">
                <label className="flex items-center gap-3 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                  <input type="checkbox" checked={policyForm.restrict_by_ip} onChange={(event) => setPolicyForm((current) => ({ ...current, restrict_by_ip: event.target.checked }))} />
                  Restrict punches by IP range
                </label>
                <textarea
                  className="field-textarea"
                  value={policyForm.allowed_ip_ranges}
                  onChange={(event) => setPolicyForm((current) => ({ ...current, allowed_ip_ranges: event.target.value }))}
                  placeholder={'One CIDR range per line, for example:\n10.0.0.0/24'}
                />
              </div>
              <div className="space-y-3 rounded-[18px] border border-[hsl(var(--border))] px-4 py-4">
                <label className="flex items-center gap-3 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                  <input type="checkbox" checked={policyForm.restrict_by_geo} onChange={(event) => setPolicyForm((current) => ({ ...current, restrict_by_geo: event.target.checked }))} />
                  Restrict punches by approved sites
                </label>
                <textarea
                  className="field-textarea"
                  value={policyForm.allowed_geo_sites}
                  onChange={(event) => setPolicyForm((current) => ({ ...current, allowed_geo_sites: event.target.value }))}
                  placeholder={'JSON array, for example:\n[{"label":"HQ","latitude":19.076,"longitude":72.8777,"radius_meters":250}]'}
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={createPolicyMutation.isPending || updatePolicyMutation.isPending}>
              Save attendance policy
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Shifts and assignments" description="Create shifts, then assign them to active employees so attendance days resolve against the right timing rules.">
          <form className="grid gap-4" onSubmit={handleShiftCreate}>
            <input className="field-input" value={newShift.name} onChange={(event) => setNewShift((current) => ({ ...current, name: event.target.value }))} placeholder="Shift name" />
            <div className="grid gap-4 md:grid-cols-2">
              <input className="field-input" type="time" value={newShift.start_time} onChange={(event) => setNewShift((current) => ({ ...current, start_time: event.target.value }))} />
              <input className="field-input" type="time" value={newShift.end_time} onChange={(event) => setNewShift((current) => ({ ...current, end_time: event.target.value }))} />
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <input className="field-input" value={newShift.grace_minutes} onChange={(event) => setNewShift((current) => ({ ...current, grace_minutes: event.target.value }))} placeholder="Grace minutes" />
              <input className="field-input" value={newShift.full_day_min_minutes} onChange={(event) => setNewShift((current) => ({ ...current, full_day_min_minutes: event.target.value }))} placeholder="Full-day minutes" />
              <input className="field-input" value={newShift.half_day_min_minutes} onChange={(event) => setNewShift((current) => ({ ...current, half_day_min_minutes: event.target.value }))} placeholder="Half-day minutes" />
              <input className="field-input" value={newShift.overtime_after_minutes} onChange={(event) => setNewShift((current) => ({ ...current, overtime_after_minutes: event.target.value }))} placeholder="OT after minutes" />
            </div>
            <div className="flex items-center gap-3 rounded-[18px] border border-[hsl(var(--border))] px-4 py-3">
              <input id="overnight-shift" type="checkbox" checked={newShift.is_overnight} onChange={(event) => setNewShift((current) => ({ ...current, is_overnight: event.target.checked }))} />
              <label htmlFor="overnight-shift" className="text-sm font-medium text-[hsl(var(--foreground-strong))]">
                Overnight shift
              </label>
            </div>
            <button type="submit" className="btn-primary" disabled={createShiftMutation.isPending}>
              Create shift
            </button>
          </form>

          <form className="mt-5 grid gap-4" onSubmit={handleShiftAssignment}>
            <AppSelect value={assignment.employee_id} onValueChange={(value) => setAssignment((current) => ({ ...current, employee_id: value }))} options={employeeOptions} placeholder="Select employee" />
            <AppSelect value={assignment.shift_id} onValueChange={(value) => setAssignment((current) => ({ ...current, shift_id: value }))} options={shiftOptions} placeholder="Select shift" />
            <div className="grid gap-4 md:grid-cols-2">
              <AppDatePicker value={assignment.start_date} onValueChange={(value) => setAssignment((current) => ({ ...current, start_date: value }))} placeholder="Start date" />
              <AppDatePicker value={assignment.end_date} onValueChange={(value) => setAssignment((current) => ({ ...current, end_date: value }))} placeholder="End date (optional)" />
            </div>
            <button type="submit" className="btn-secondary" disabled={assignShiftMutation.isPending}>
              Assign shift
            </button>
          </form>

          <div className="mt-5 space-y-3">
            {shifts?.map((shift) => (
              <div key={shift.id} className="surface-muted rounded-[18px] px-4 py-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-[hsl(var(--foreground-strong))]">{shift.name}</p>
                  <StatusBadge tone={shift.is_active ? 'success' : 'warning'}>{shift.is_active ? 'ACTIVE' : 'INACTIVE'}</StatusBadge>
                </div>
                <p className="mt-2 text-[hsl(var(--muted-foreground))]">
                  {shift.start_time.slice(0, 5)} to {shift.end_time.slice(0, 5)} • Grace {shift.grace_minutes ?? defaultPolicy?.grace_minutes ?? 0} mins
                </p>
              </div>
            ))}
            {assignments?.slice(0, 4).map((item) => (
              <div key={item.id} className="surface-muted rounded-[18px] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
                {item.employee_name} • {item.shift_name} • {item.start_date}{item.end_date ? ` to ${item.end_date}` : ''}
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <SectionCard title="Daily attendance review" description="Review the selected day, fix missing check-ins or check-outs, and surface incomplete attendance before payroll picks it up.">
          <div className="mb-4 grid gap-4 md:grid-cols-2">
            <AppDatePicker value={selectedDate} onValueChange={setSelectedDate} placeholder="Select attendance date" />
            <AppSelect
              value={dayStatusFilter}
              onValueChange={setDayStatusFilter}
              placeholder="Filter by status"
              options={[
                { value: '', label: 'All statuses' },
                { value: 'INCOMPLETE', label: 'Incomplete' },
                { value: 'ABSENT', label: 'Absent' },
                { value: 'PRESENT', label: 'Present' },
                { value: 'HALF_DAY', label: 'Half day' },
                { value: 'ON_LEAVE', label: 'On leave' },
                { value: 'ON_DUTY', label: 'On duty' },
              ]}
            />
          </div>
          {daysLoading ? (
            <SkeletonTable rows={5} />
          ) : attendanceDays?.length ? (
            <div className="space-y-4">
              {attendanceDays.map((day) => {
                const draft = overrideDrafts[day.id] ?? {
                  check_in: day.check_in_at ? new Date(day.check_in_at).toISOString().slice(11, 16) : '',
                  check_out: day.check_out_at ? new Date(day.check_out_at).toISOString().slice(11, 16) : '',
                  note: day.note ?? '',
                }
                return (
                  <div key={day.id} className="surface-muted rounded-[22px] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{day.employee_name}</p>
                        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                          {day.employee_code || 'Unassigned code'} • Worked {day.worked_minutes} mins • OT {day.overtime_minutes} mins
                        </p>
                      </div>
                      <StatusBadge tone={getAttendanceDayStatusTone(day.status)}>{day.status}</StatusBadge>
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <input
                        className="field-input"
                        type="time"
                        value={draft.check_in}
                        onChange={(event) =>
                          setOverrideDrafts((current) => ({
                            ...current,
                            [day.id]: { ...draft, check_in: event.target.value },
                          }))
                        }
                      />
                      <input
                        className="field-input"
                        type="time"
                        value={draft.check_out}
                        onChange={(event) =>
                          setOverrideDrafts((current) => ({
                            ...current,
                            [day.id]: { ...draft, check_out: event.target.value },
                          }))
                        }
                      />
                      <button type="button" className="btn-secondary" onClick={() => void handleDayOverride(day)}>
                        Save override
                      </button>
                    </div>
                    <textarea
                      className="field-textarea mt-3"
                      placeholder="Admin review note"
                      value={draft.note}
                      onChange={(event) =>
                        setOverrideDrafts((current) => ({
                          ...current,
                          [day.id]: { ...draft, note: event.target.value },
                        }))
                      }
                    />
                  </div>
                )
              })}
            </div>
          ) : (
            <EmptyState title="No attendance rows for this date yet" description="Attendance days will populate from employee punches, imports, leave, holidays, on-duty, and regularization activity." icon={Upload} />
          )}
        </SectionCard>

        <SectionCard title="Pending regularizations" description="Keep an eye on approval-driven attendance changes that still need manager action.">
          {regularizationLoading ? (
            <SkeletonTable rows={4} />
          ) : regularizations?.length ? (
            <div className="space-y-3">
              {regularizations.map((item) => (
                <div key={item.id} className="surface-muted rounded-[20px] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-[hsl(var(--foreground-strong))]">{item.employee_name}</p>
                    <StatusBadge tone={getRegularizationTone(item.status)}>{item.status}</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {item.attendance_date} • {item.requested_check_in_at ? new Date(item.requested_check_in_at).toLocaleTimeString() : 'No check-in'} •{' '}
                    {item.requested_check_out_at ? new Date(item.requested_check_out_at).toLocaleTimeString() : 'No check-out'}
                  </p>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{item.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No pending regularizations" description="When employees submit attendance corrections, they will appear here while the workflow is pending." icon={FileUp} />
          )}
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Attendance source adapters" description="Create managed API or device adapters so external punch feeds land in the same attendance engine as web punch and Excel imports.">
          <form className="grid gap-4" onSubmit={handleCreateSource}>
            <input className="field-input" value={sourceForm.name} onChange={(event) => setSourceForm((current) => ({ ...current, name: event.target.value }))} placeholder="Source name" />
            <AppSelect
              value={sourceForm.kind}
              onValueChange={(value) => setSourceForm((current) => ({ ...current, kind: value as 'API' | 'EXCEL' | 'DEVICE' }))}
              options={[
                { value: 'API', label: 'API adapter' },
                { value: 'DEVICE', label: 'Device adapter' },
                { value: 'EXCEL', label: 'Excel channel' },
              ]}
              placeholder="Select source type"
            />
            <button type="submit" className="btn-primary" disabled={createSourceMutation.isPending}>
              Create source
            </button>
          </form>

          <div className="mt-5 space-y-3">
            {sourcesLoading ? (
              <SkeletonTable rows={3} />
            ) : sources?.length ? (
              sources.map((source) => (
                <div key={source.id} className="surface-muted rounded-[20px] px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{source.name}</p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        {source.kind} • {source.is_active ? 'Active' : 'Inactive'}{source.api_key_masked ? ` • Key ${source.api_key_masked}` : ''}
                      </p>
                    </div>
                    {source.kind === 'API' ? (
                      <button type="button" className="btn-secondary" onClick={() => void handleRotateSourceKey(source.id)}>
                        <Link2 className="h-4 w-4" />
                        Rotate key
                      </button>
                    ) : null}
                  </div>
                  {source.kind === 'API' ? (
                    <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
                      POST punches to <span className="font-medium text-[hsl(var(--foreground-strong))]">/api/org/attendance/public-sources/{source.id}/punches/</span> with header <span className="font-medium text-[hsl(var(--foreground-strong))]">X-Attendance-Source-Key</span>.
                    </p>
                  ) : null}
                  {source.last_error ? <p className="mt-3 text-sm text-[hsl(var(--danger))]">{source.last_error}</p> : null}
                </div>
              ))
            ) : (
              <EmptyState title="No attendance sources yet" description="Create an API adapter when you want a device or external system to push punches directly instead of relying only on spreadsheets." icon={Link2} />
            )}
          </div>
        </SectionCard>

        <SectionCard title="Monthly attendance report" description="Track late marks, overtime, absences, and incomplete days before the period reaches payroll.">
          <div className="mb-4 max-w-sm">
            <input className="field-input" type="month" value={reportMonth} onChange={(event) => setReportMonth(event.target.value)} />
          </div>
          {reportLoading ? (
            <SkeletonTable rows={5} />
          ) : attendanceReport ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard title="Present days" value={attendanceReport.present_days} hint={`Across ${attendanceReport.employee_count} active employees`} tone="success" />
                <MetricCard title="Absences" value={attendanceReport.absent_days} hint="Days classified absent" tone="danger" />
                <MetricCard title="Incomplete days" value={attendanceReport.incomplete_days} hint="Needs punch correction or review" tone="warning" />
                <MetricCard title="Late marks" value={attendanceReport.late_marks} hint={`OT ${attendanceReport.overtime_minutes} mins`} tone="info" />
              </div>
              <div className="space-y-3">
                {attendanceReport.rows.slice(0, 12).map((day) => (
                  <div key={day.id} className="surface-muted flex flex-col gap-3 rounded-[20px] px-4 py-4 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{day.employee_name}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        {day.attendance_date} • Worked {day.worked_minutes} mins • OT {day.overtime_minutes} mins
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge tone={getAttendanceDayStatusTone(day.status)}>{day.status}</StatusBadge>
                      {day.is_late ? <StatusBadge tone="warning">Late</StatusBadge> : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState title="No report data yet" description="Monthly attendance insights will appear once the organisation starts recording attendance through punch, imports, or regularizations." icon={Download} />
          )}
        </SectionCard>
      </div>

      <SectionCard title="Attendance imports" description="Keep using direct attendance uploads and raw punch normalization where biometric/API sources are not ready yet.">
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-4">
            <input type="file" accept=".xlsx" onChange={(event) => setAttendanceFile(event.target.files?.[0] ?? null)} className="field-input" />
            <div className="rounded-[18px] border border-[hsl(var(--info)_/_0.22)] bg-[hsl(var(--info)_/_0.1)] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Required columns: <span className="font-medium text-[hsl(var(--foreground-strong))]">employee_code, date, check_in, check_out</span>
            </div>
            <button type="button" className="btn-primary" disabled={uploadAttendanceMutation.isPending} onClick={() => void handleAttendanceUpload()}>
              <Upload className="h-4 w-4" />
              Upload attendance sheet
            </button>
          </div>
          <div className="space-y-4">
            <input type="file" accept=".xlsx" onChange={(event) => setPunchFile(event.target.files?.[0] ?? null)} className="field-input" />
            <div className="rounded-[18px] border border-[hsl(var(--warning)_/_0.26)] bg-[hsl(var(--warning)_/_0.12)] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Required columns: <span className="font-medium text-[hsl(var(--foreground-strong))]">employee_code, date, punch_time</span>
            </div>
            <button type="button" className="btn-primary" disabled={uploadPunchMutation.isPending} onClick={() => void handlePunchUpload()}>
              <FileUp className="h-4 w-4" />
              Upload punch sheet
            </button>
          </div>
        </div>

        <div className="mt-5 space-y-4">
          {attendanceImports?.map((job) => (
            <div key={job.id} className="surface-muted rounded-[22px] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{job.original_filename}</p>
                    <StatusBadge tone={getAttendanceImportTone(job.status)}>{job.status}</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {job.mode.replace(/_/g, ' ')} • Uploaded {formatDateTime(job.created_at)} • Valid {job.valid_rows} • Errors {job.error_rows}
                  </p>
                </div>
                {job.normalized_file_available ? (
                  <button type="button" className="btn-secondary" onClick={() => void handleNormalizedDownload(job.id)}>
                    <Download className="h-4 w-4" />
                    Download normalized file
                  </button>
                ) : null}
              </div>
              {job.error_preview.length ? (
                <div className="mt-4 rounded-[18px] border border-[hsl(var(--danger)_/_0.18)] bg-[hsl(var(--danger)_/_0.08)] px-4 py-3 text-sm text-[hsl(var(--foreground-strong))]">
                  <p className="font-medium">Top validation issues</p>
                  <ul className="mt-2 space-y-1 text-[hsl(var(--muted-foreground))]">
                    {job.error_preview.map((error) => (
                      <li key={`${job.id}-${error.row_number}`}>
                        Row {error.row_number}: {error.employee_code || 'Unknown employee'} • {error.message}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
