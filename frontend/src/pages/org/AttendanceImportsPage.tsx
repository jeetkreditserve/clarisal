import { useState } from 'react'
import { Download, FileUp, Upload } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useAttendanceImports,
  useDownloadAttendanceTemplate,
  useDownloadNormalizedAttendanceFile,
  useUploadAttendanceSheet,
  useUploadPunchSheet,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function getImportTone(status: string) {
  if (status === 'POSTED') return 'success'
  if (status === 'READY_FOR_REVIEW') return 'info'
  return 'danger'
}

export function AttendanceImportsPage() {
  const { data, isLoading } = useAttendanceImports()
  const uploadAttendanceMutation = useUploadAttendanceSheet()
  const uploadPunchMutation = useUploadPunchSheet()
  const downloadTemplateMutation = useDownloadAttendanceTemplate()
  const downloadNormalizedMutation = useDownloadNormalizedAttendanceFile()
  const [attendanceFile, setAttendanceFile] = useState<File | null>(null)
  const [punchFile, setPunchFile] = useState<File | null>(null)

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
      toast.success(
        job.status === 'POSTED'
          ? `Attendance import posted for ${job.posted_rows} employee-day records.`
          : 'Attendance import failed. Review the row errors below.',
      )
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
      toast.success(
        job.valid_rows
          ? `Punch sheet normalized into ${job.valid_rows} attendance rows. Download the review file next.`
          : 'Punch sheet upload failed. Review the row errors below.',
      )
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

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Attendance"
        title="Attendance imports"
        description="Upload direct attendance Excel sheets or raw punch Excel sheets, then download the normalized review file when punches need pairing."
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

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          title="Attendance sheet import"
          description="Upload one row per employee and date with actual check-in and check-out times. Valid rows post attendance directly."
        >
          <div className="space-y-4">
            <input
              type="file"
              accept=".xlsx"
              onChange={(event) => setAttendanceFile(event.target.files?.[0] ?? null)}
              className="field-input"
            />
            <div className="rounded-[18px] border border-[hsl(var(--info)_/_0.22)] bg-[hsl(var(--info)_/_0.1)] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Required columns: <span className="font-medium text-[hsl(var(--foreground-strong))]">employee_code, date, check_in, check_out</span>
            </div>
            <button type="button" className="btn-primary" disabled={uploadAttendanceMutation.isPending} onClick={() => void handleAttendanceUpload()}>
              <Upload className="h-4 w-4" />
              {uploadAttendanceMutation.isPending ? 'Uploading...' : 'Upload attendance sheet'}
            </button>
          </div>
        </SectionCard>

        <SectionCard
          title="Punch sheet import"
          description="Upload raw punches only. The system turns them into a reviewable attendance sheet using first punch as check-in and last punch as check-out."
        >
          <div className="space-y-4">
            <input
              type="file"
              accept=".xlsx"
              onChange={(event) => setPunchFile(event.target.files?.[0] ?? null)}
              className="field-input"
            />
            <div className="rounded-[18px] border border-[hsl(var(--warning)_/_0.26)] bg-[hsl(var(--warning)_/_0.12)] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              Required columns: <span className="font-medium text-[hsl(var(--foreground-strong))]">employee_code, date, punch_time</span>
            </div>
            <button type="button" className="btn-primary" disabled={uploadPunchMutation.isPending} onClick={() => void handlePunchUpload()}>
              <FileUp className="h-4 w-4" />
              {uploadPunchMutation.isPending ? 'Uploading...' : 'Upload punch sheet'}
            </button>
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Recent import jobs"
        description="Review recent uploads, validation failures, and normalized punch files that are ready to download."
      >
        {data && data.length ? (
          <div className="space-y-4">
            {data.map((job) => (
              <div key={job.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{job.original_filename}</p>
                      <StatusBadge tone={getImportTone(job.status)}>{job.status}</StatusBadge>
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
        ) : (
          <EmptyState
            title="No attendance imports yet"
            description="Start with a sample Excel template, then upload either a direct attendance sheet or a raw punch sheet."
            icon={FileUp}
          />
        )}
      </SectionCard>
    </div>
  )
}
