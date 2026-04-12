import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Navigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useAuth } from '@/hooks/useAuth'
import {
  fetchReportDatasets,
  fetchReportTemplate,
  previewReportTemplate,
  saveReportTemplate,
  updateReportTemplate,
} from '@/lib/api/reports'
import { getErrorMessage } from '@/lib/errors'
import { hasPermission } from '@/lib/rbac'
import type { ReportDataset, ReportPreviewResult, ReportTemplatePayload } from '@/types/reports'

function createPayload(datasetCode: string, name: string, columns: string[]): ReportTemplatePayload {
  return {
    dataset_code: datasetCode,
    name,
    description: '',
    status: 'DRAFT',
    columns,
    filters: [],
    filter_logic: '',
    groupings: [],
    summaries: [],
    formula_fields: [],
    chart: {},
  }
}

function ReportBuilderForm({
  datasets,
  templateId,
  initialDatasetCode,
  initialTemplateName,
  initialSelectedColumns,
}: {
  datasets: ReportDataset[]
  templateId: string | null
  initialDatasetCode: string
  initialTemplateName: string
  initialSelectedColumns: string[]
}) {
  const [datasetCode, setDatasetCode] = useState(initialDatasetCode)
  const [templateName, setTemplateName] = useState(initialTemplateName)
  const [selectedColumns, setSelectedColumns] = useState<string[]>(initialSelectedColumns)
  const [preview, setPreview] = useState<ReportPreviewResult | null>(null)
  const selectedDataset = datasets.find((dataset) => dataset.code === datasetCode) ?? datasets[0]
  const fields = selectedDataset?.fields ?? []
  const payload = useMemo(
    () => createPayload(selectedDataset?.code ?? '', templateName, selectedColumns),
    [selectedDataset?.code, selectedColumns, templateName],
  )
  const previewMutation = useMutation({ mutationFn: previewReportTemplate })
  const saveMutation = useMutation({
    mutationFn: (nextPayload: ReportTemplatePayload) =>
      templateId ? updateReportTemplate(templateId, nextPayload) : saveReportTemplate(nextPayload),
  })

  const toggleColumn = (code: string) => {
    setSelectedColumns((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]))
  }

  const runPreview = async () => {
    if (!payload.dataset_code || payload.columns.length === 0) {
      toast.error('Select a dataset and at least one column.')
      return
    }
    try {
      setPreview(await previewMutation.mutateAsync(payload))
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to preview report.'))
    }
  }

  const saveDraft = async () => {
    if (!payload.dataset_code || payload.columns.length === 0) {
      toast.error('Select a dataset and at least one column.')
      return
    }
    try {
      await saveMutation.mutateAsync(payload)
      toast.success('Report template saved.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save report template.'))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reports"
        title={templateId ? 'Edit report template' : 'Report builder'}
        description="Create governed reports from approved datasets and fields."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => void runPreview()} disabled={previewMutation.isPending}>
              {previewMutation.isPending ? 'Previewing...' : 'Preview'}
            </button>
            <button type="button" className="btn-primary" onClick={() => void saveDraft()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving...' : templateId ? 'Save changes' : 'Save draft'}
            </button>
          </>
        }
      />

      <SectionCard title="Dataset" description="Choose the source records for this report.">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2">
            <span className="field-label">Dataset</span>
            <select
              className="field-input"
              value={selectedDataset?.code ?? ''}
              onChange={(event) => {
                setDatasetCode(event.target.value)
                setSelectedColumns([])
                setPreview(null)
              }}
            >
              {datasets.map((dataset) => (
                <option key={dataset.code} value={dataset.code}>
                  {dataset.label}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2">
            <span className="field-label">Report name</span>
            <input className="field-input" value={templateName} onChange={(event) => setTemplateName(event.target.value)} />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Columns" description="Only catalogued fields can be selected. Sensitive fields remain governed by backend permissions.">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {fields.map((field) => (
            <label key={field.code} className="surface-muted flex items-start gap-3 rounded-[18px] p-4">
              <input
                type="checkbox"
                className="mt-1"
                checked={selectedColumns.includes(field.code)}
                onChange={() => toggleColumn(field.code)}
              />
              <span>
                <span className="block font-medium text-[hsl(var(--foreground-strong))]">{field.label}</span>
                <span className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">{field.data_type}</span>
              </span>
            </label>
          ))}
        </div>
      </SectionCard>

      {preview ? (
        <SectionCard title="Preview" description={preview.truncated ? 'Showing the first rows only.' : 'Preview rows from the selected report.'}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr>
                  {preview.columns.map((column) => (
                    <th key={column.code} className="px-3 py-2 text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, index) => (
                  <tr key={index} className="border-t border-[hsl(var(--border)_/_0.72)]">
                    {preview.columns.map((column) => (
                      <td key={column.code} className="px-3 py-3">
                        {row[column.code] ?? ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      ) : null}
    </div>
  )
}

export function ReportBuilderPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const templateId = searchParams.get('templateId')
  const { data: datasets = [], isLoading } = useQuery({ queryKey: ['org', 'report-datasets'], queryFn: fetchReportDatasets })
  const { data: existingTemplate } = useQuery({
    queryKey: ['org', 'report-template', templateId],
    queryFn: () => fetchReportTemplate(templateId ?? ''),
    enabled: Boolean(templateId),
  })
  const canManageReports = hasPermission(user, 'org.reports.builder.manage')

  if (!canManageReports) {
    return <Navigate to="/org/dashboard" replace />
  }

  if (isLoading || (templateId && !existingTemplate)) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={8} />
      </div>
    )
  }

  return (
    <ReportBuilderForm
      key={existingTemplate?.id ?? 'new'}
      datasets={datasets}
      templateId={templateId}
      initialDatasetCode={existingTemplate?.dataset_code ?? datasets[0]?.code ?? ''}
      initialTemplateName={existingTemplate?.name ?? 'New report'}
      initialSelectedColumns={existingTemplate?.columns ?? []}
    />
  )
}
