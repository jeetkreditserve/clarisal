import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock3, Copy, Folder, Play, Search, Settings2 } from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useAuth } from '@/hooks/useAuth'
import {
  fetchReportFolders,
  fetchReportTemplates,
  runReportTemplate,
  saveReportTemplate,
  updateReportTemplate,
} from '@/lib/api/reports'
import { getErrorMessage } from '@/lib/errors'
import { hasPermission } from '@/lib/rbac'
import type { ReportTemplate, ReportTemplatePayload } from '@/types/reports'

type StatusFilter = 'ALL' | 'DRAFT' | 'DEPLOYED' | 'ARCHIVED'

function toTemplatePayload(template: ReportTemplate, overrides: Partial<ReportTemplatePayload> = {}): ReportTemplatePayload {
  return {
    dataset_code: template.dataset_code,
    name: template.name,
    description: template.description,
    status: template.status,
    columns: template.columns,
    filters: template.filters,
    filter_logic: template.filter_logic,
    groupings: template.groupings,
    summaries: template.summaries,
    formula_fields: template.formula_fields,
    chart: template.chart,
    ...overrides,
  }
}

function statusTone(status: ReportTemplate['status']) {
  if (status === 'DEPLOYED') return 'bg-[hsl(var(--success)_/_0.12)] text-[hsl(var(--success))] border-[hsl(var(--success)_/_0.22)]'
  if (status === 'ARCHIVED') return 'bg-[hsl(var(--surface-subtle))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border)_/_0.92)]'
  return 'bg-[hsl(var(--brand)_/_0.12)] text-[hsl(var(--brand))] border-[hsl(var(--brand)_/_0.22)]'
}

export function ReportTemplateListPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [folderFilter, setFolderFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const canReadReports = hasPermission(user, 'org.reports.read')
  const canManageReports = hasPermission(user, 'org.reports.builder.manage')
  const canExportReports = hasPermission(user, 'org.reports.export')

  const { data: folders = [], isLoading } = useQuery({ queryKey: ['org', 'report-folders'], queryFn: fetchReportFolders })
  const { data: templates = [] } = useQuery({ queryKey: ['org', 'report-templates'], queryFn: fetchReportTemplates, enabled: canReadReports })

  const cloneMutation = useMutation({
    mutationFn: (template: ReportTemplate) =>
      saveReportTemplate(
        toTemplatePayload(template, {
          name: `${template.name} copy`,
          status: 'DRAFT',
        }),
      ),
    onSuccess: () => {
      toast.success('Template cloned.')
      void queryClient.invalidateQueries({ queryKey: ['org', 'report-templates'] })
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Unable to clone this template.')),
  })

  const archiveMutation = useMutation({
    mutationFn: (template: ReportTemplate) =>
      updateReportTemplate(
        template.id,
        toTemplatePayload(template, {
          status: 'ARCHIVED',
        }),
      ),
    onSuccess: () => {
      toast.success('Template archived.')
      void queryClient.invalidateQueries({ queryKey: ['org', 'report-templates'] })
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Unable to archive this template.')),
  })

  const runMutation = useMutation({
    mutationFn: (templateId: string) => runReportTemplate(templateId, { file_format: 'xlsx', parameters: {} }),
    onSuccess: () => {
      toast.success('Report run started.')
      void queryClient.invalidateQueries({ queryKey: ['org', 'report-runs'] })
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Unable to run this template.')),
  })

  const filteredTemplates = useMemo(() => {
    const term = search.trim().toLowerCase()
    return templates.filter((template) => {
      if (statusFilter !== 'ALL' && template.status !== statusFilter) return false
      if (folderFilter !== 'all' && template.folder !== folderFilter) return false
      if (!term) return true
      return (
        template.name.toLowerCase().includes(term) ||
        template.dataset_label.toLowerCase().includes(term) ||
        (template.folder_name ?? '').toLowerCase().includes(term)
      )
    })
  }, [folderFilter, search, statusFilter, templates])

  if (!canReadReports) {
    return <Navigate to="/org/dashboard" replace />
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
        eyebrow="Reports"
        title="Saved templates"
        description="Browse governed templates by folder, promote drafts deliberately, and launch controlled exports without leaving the reporting workspace."
        actions={
          <>
            {canManageReports ? (
              <Link to="/org/reports/builder" className="btn-secondary">
                New template
              </Link>
            ) : null}
            <Link to="/org/reports" className="btn-secondary">
              Fixed reports
            </Link>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)]">
        <SectionCard title="Folders" description="Templates stay grouped by operational domain.">
          <div className="space-y-2">
            <button
              type="button"
              className={`flex w-full items-center justify-between rounded-[18px] px-4 py-3 text-left text-sm ${
                folderFilter === 'all'
                  ? 'bg-[hsl(var(--brand)_/_0.12)] text-[hsl(var(--brand))]'
                  : 'surface-muted text-[hsl(var(--foreground-strong))]'
              }`}
              onClick={() => setFolderFilter('all')}
            >
              <span className="flex items-center gap-2">
                <Folder className="h-4 w-4" />
                All folders
              </span>
              <span>{templates.length}</span>
            </button>
            {folders.map((folder) => (
              <button
                key={folder.id}
                type="button"
                className={`flex w-full items-center justify-between rounded-[18px] px-4 py-3 text-left text-sm ${
                  folderFilter === folder.id
                    ? 'bg-[hsl(var(--brand)_/_0.12)] text-[hsl(var(--brand))]'
                    : 'surface-muted text-[hsl(var(--foreground-strong))]'
                }`}
                onClick={() => setFolderFilter(folder.id)}
              >
                <span className="truncate">{folder.name}</span>
                <span>{templates.filter((template) => template.folder === folder.id).length}</span>
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Templates" description="Search, clone, archive, and run only the reports that belong in the active governance lane.">
          <div className="flex flex-col gap-4 border-b border-[hsl(var(--border)_/_0.84)] pb-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-2">
              {(['ALL', 'DRAFT', 'DEPLOYED', 'ARCHIVED'] as StatusFilter[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  className={`rounded-full px-4 py-2 text-sm font-medium ${
                    statusFilter === status
                      ? 'bg-[hsl(var(--foreground-strong))] text-[hsl(var(--surface-contrast-foreground))]'
                      : 'surface-muted text-[hsl(var(--muted-foreground-strong))]'
                  }`}
                  onClick={() => setStatusFilter(status)}
                >
                  {status === 'ALL' ? 'All' : status.charAt(0) + status.slice(1).toLowerCase()}
                </button>
              ))}
            </div>

            <label className="relative block w-full max-w-sm">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
              <input
                className="field-input pl-10"
                placeholder="Search by name, dataset, or folder"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
          </div>

          <div className="space-y-4 pt-5">
            {filteredTemplates.length === 0 ? (
              <div className="rounded-[24px] border border-dashed border-[hsl(var(--border)_/_0.84)] px-5 py-12 text-center text-sm text-[hsl(var(--muted-foreground))]">
                No templates match this filter set.
              </div>
            ) : null}

            {filteredTemplates.map((template) => (
              <div
                key={template.id}
                className="rounded-[26px] border border-[hsl(var(--border)_/_0.82)] bg-[linear-gradient(180deg,hsl(var(--surface)_/_0.98),hsl(var(--surface-subtle)_/_0.92))] p-5"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`status-pill ${statusTone(template.status)}`}>{template.status}</span>
                      <span className="status-pill bg-[hsl(var(--surface-subtle))] text-[hsl(var(--muted-foreground-strong))] border-[hsl(var(--border)_/_0.92)]">
                        {template.dataset_label}
                      </span>
                      {template.folder_name ? (
                        <span className="status-pill bg-[hsl(var(--brand)_/_0.1)] text-[hsl(var(--brand))] border-[hsl(var(--brand)_/_0.18)]">
                          {template.folder_name}
                        </span>
                      ) : null}
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-[hsl(var(--foreground-strong))]">{template.name}</h2>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        v{template.version} • {template.columns.length} columns • {template.filters.length} filters
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {canManageReports ? (
                      <Link to={`/org/reports/builder?templateId=${template.id}`} className="btn-secondary">
                        <Settings2 className="h-4 w-4" />
                        Edit
                      </Link>
                    ) : null}
                    {canManageReports ? (
                      <button
                        type="button"
                        className="btn-secondary"
                        aria-label={`Clone ${template.name}`}
                        onClick={() => cloneMutation.mutate(template)}
                      >
                        <Copy className="h-4 w-4" />
                        Clone
                      </button>
                    ) : null}
                    {canManageReports && template.status !== 'ARCHIVED' ? (
                      <button
                        type="button"
                        className="btn-secondary"
                        aria-label={`Archive ${template.name}`}
                        onClick={() => archiveMutation.mutate(template)}
                      >
                        <Clock3 className="h-4 w-4" />
                        Archive
                      </button>
                    ) : null}
                    {canExportReports ? (
                      <button
                        type="button"
                        className="btn-primary"
                        aria-label={`Run ${template.name}`}
                        onClick={() => runMutation.mutate(template.id)}
                      >
                        <Play className="h-4 w-4" />
                        Run Excel
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="surface-muted rounded-[20px] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Columns</p>
                    <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">{template.columns.join(', ')}</p>
                  </div>
                  <div className="surface-muted rounded-[20px] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Governance</p>
                    <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                      {template.is_system ? 'System seeded template' : 'Org-managed template'}
                    </p>
                  </div>
                  <div className="surface-muted rounded-[20px] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Actions</p>
                    <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                      {canExportReports ? 'Run and export enabled' : 'Run/export withheld until export permission is granted'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
