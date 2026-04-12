import { useMutation, useQuery } from '@tanstack/react-query'
import { Download, FileSpreadsheet } from 'lucide-react'
import { Navigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useAuth } from '@/hooks/useAuth'
import { downloadReportExport, fetchReportRun } from '@/lib/api/reports'
import { getErrorMessage } from '@/lib/errors'
import { hasPermission } from '@/lib/rbac'

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function statusTone(status: string) {
  if (status === 'SUCCEEDED') return 'bg-[hsl(var(--success)_/_0.12)] text-[hsl(var(--success))] border-[hsl(var(--success)_/_0.22)]'
  if (status === 'FAILED') return 'bg-[hsl(var(--destructive)_/_0.12)] text-[hsl(var(--destructive))] border-[hsl(var(--destructive)_/_0.22)]'
  return 'bg-[hsl(var(--brand)_/_0.12)] text-[hsl(var(--brand))] border-[hsl(var(--brand)_/_0.22)]'
}

export function ReportRunDetailPage() {
  const { user } = useAuth()
  const { runId = '' } = useParams()
  const canReadReports = hasPermission(user, 'org.reports.read')
  const canExportReports = hasPermission(user, 'org.reports.export')
  const { data: run, isLoading } = useQuery({
    queryKey: ['org', 'report-run', runId],
    queryFn: () => fetchReportRun(runId),
    enabled: Boolean(runId && canReadReports),
  })
  const downloadMutation = useMutation({
    mutationFn: ({ runId: activeRunId, exportId }: { runId: string; exportId: string }) => downloadReportExport(activeRunId, exportId),
    onSuccess: ({ blob, filename }) => {
      triggerDownload(blob, filename)
      toast.success('Export downloaded.')
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Unable to download this export.')),
  })

  if (!canReadReports) {
    return <Navigate to="/org/dashboard" replace />
  }

  if (isLoading || !run) {
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
        eyebrow="Reports"
        title={run.template_name}
        description="Inspect execution state, who requested the report, and which exports were produced for downstream distribution."
      />

      <SectionCard title="Run status" description="This record captures the governed execution result for a single report request.">
        <div className="grid gap-4 lg:grid-cols-4">
          <div className="surface-muted rounded-[22px] px-5 py-5">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Status</p>
            <div className={`mt-3 inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${statusTone(run.status)}`}>{run.status}</div>
          </div>
          <div className="surface-muted rounded-[22px] px-5 py-5">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Requested by</p>
            <p className="mt-3 text-sm font-semibold text-[hsl(var(--foreground-strong))]">{run.requested_by_name || run.requested_by_email}</p>
            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{run.requested_by_email}</p>
          </div>
          <div className="surface-muted rounded-[22px] px-5 py-5">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Rows exported</p>
            <p className="mt-3 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">{run.row_count}</p>
          </div>
          <div className="surface-muted rounded-[22px] px-5 py-5">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Timeline</p>
            <p className="mt-3 text-sm font-semibold text-[hsl(var(--foreground-strong))]">{run.started_at ?? 'Queued'}</p>
            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{run.completed_at ?? 'Still running'}</p>
          </div>
        </div>
        {run.error_message ? (
          <div className="mt-4 rounded-[20px] border border-[hsl(var(--destructive)_/_0.18)] bg-[hsl(var(--destructive)_/_0.08)] px-4 py-4 text-sm text-[hsl(var(--foreground-strong))]">
            {run.error_message}
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Exports" description="Downloads are retained per run so downstream consumers can retrieve the exact generated artifact.">
        <div className="space-y-3">
          {run.exports.length === 0 ? (
            <div className="rounded-[22px] border border-dashed border-[hsl(var(--border)_/_0.84)] px-5 py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No exports are attached to this run yet.
            </div>
          ) : null}
          {run.exports.map((exportArtifact) => (
            <div
              key={exportArtifact.id}
              className="flex flex-col gap-4 rounded-[22px] border border-[hsl(var(--border)_/_0.82)] bg-[hsl(var(--surface)_/_0.92)] px-5 py-4 lg:flex-row lg:items-center lg:justify-between"
            >
              <div className="flex items-start gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-[16px] bg-[hsl(var(--brand)_/_0.1)] text-[hsl(var(--brand))]">
                  <FileSpreadsheet className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-medium text-[hsl(var(--foreground-strong))]">{exportArtifact.file_name}</p>
                  <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                    {exportArtifact.file_format.toUpperCase()} • {exportArtifact.byte_size} bytes
                  </p>
                </div>
              </div>

              {canExportReports ? (
                <button
                  type="button"
                  className="btn-primary"
                  aria-label={`Download ${exportArtifact.file_name}`}
                  onClick={() => downloadMutation.mutate({ runId, exportId: exportArtifact.id })}
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
              ) : (
                <span className="text-sm text-[hsl(var(--muted-foreground))]">Download access requires `org.reports.export`.</span>
              )}
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
