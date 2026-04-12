import api from '@/lib/api'
import type {
  ReportDataset,
  ReportFolder,
  ReportPreviewResult,
  ReportRun,
  ReportTemplate,
  ReportTemplatePayload,
} from '@/types/reports'

export async function fetchReportDatasets(): Promise<ReportDataset[]> {
  const { data } = await api.get<ReportDataset[]>('/org/reports/datasets/')
  return data
}

export async function fetchReportTemplates(): Promise<ReportTemplate[]> {
  const { data } = await api.get<ReportTemplate[]>('/org/reports/templates/')
  return data
}

export async function fetchReportTemplate(templateId: string): Promise<ReportTemplate> {
  const { data } = await api.get<ReportTemplate>(`/org/reports/templates/${templateId}/`)
  return data
}

export async function updateReportTemplate(templateId: string, payload: ReportTemplatePayload): Promise<ReportTemplate> {
  const { data } = await api.patch<ReportTemplate>(`/org/reports/templates/${templateId}/`, payload)
  return data
}

export async function previewReportTemplate(payload: ReportTemplatePayload): Promise<ReportPreviewResult> {
  const { data } = await api.post<ReportPreviewResult>('/org/reports/templates/preview-draft/', payload)
  return data
}

export async function saveReportTemplate(payload: ReportTemplatePayload): Promise<ReportTemplate> {
  const { data } = await api.post<ReportTemplate>('/org/reports/templates/', payload)
  return data
}

export async function fetchReportFolders(): Promise<ReportFolder[]> {
  const { data } = await api.get<ReportFolder[]>('/org/reports/folders/')
  return data
}

export async function fetchReportRuns(): Promise<ReportRun[]> {
  const { data } = await api.get<ReportRun[]>('/org/reports/runs/')
  return data
}

export async function fetchReportRun(runId: string): Promise<ReportRun> {
  const { data } = await api.get<ReportRun>(`/org/reports/runs/${runId}/`)
  return data
}

export async function runReportTemplate(
  templateId: string,
  payload: { file_format: 'csv' | 'xlsx'; parameters?: Record<string, string | number | boolean | null> },
): Promise<ReportRun> {
  const { data } = await api.post<ReportRun>(`/org/reports/templates/${templateId}/run/`, payload)
  return data
}

function parseFilename(disposition?: string): string {
  const matches = disposition?.match(/filename="?([^"]+)"?/)
  return matches?.[1] ?? 'report-export'
}

export async function downloadReportExport(runId: string, exportId: string): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get<Blob>(`/org/reports/runs/${runId}/exports/${exportId}/`, {
    responseType: 'blob',
  })
  return {
    blob: response.data,
    filename: parseFilename(response.headers['content-disposition']),
  }
}
