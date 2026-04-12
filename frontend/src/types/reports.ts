export interface ReportField {
  id: string
  code: string
  label: string
  data_type: string
  is_filterable: boolean
  is_groupable: boolean
  is_summarizable: boolean
  is_sensitive: boolean
}

export interface ReportDataset {
  id: string
  code: string
  label: string
  description: string
  default_date_field: string
  fields: ReportField[]
}

export interface ReportFilter {
  field: string
  operator: string
  value: string
}

export interface ReportGrouping {
  field: string
  position: number
}

export interface ReportSummary {
  field: string
  function: 'count' | 'sum' | 'avg' | 'min' | 'max'
}

export interface ReportFormulaField {
  label: string
  expression: string
}

export interface ReportChart {
  type: 'bar' | 'line' | 'pie' | 'table'
  x?: string
  y?: string
}

export interface ReportTemplatePayload {
  dataset_code: string
  name: string
  description: string
  status: 'DRAFT' | 'DEPLOYED' | 'ARCHIVED'
  columns: string[]
  filters: ReportFilter[]
  filter_logic: string
  groupings: ReportGrouping[]
  summaries: ReportSummary[]
  formula_fields: ReportFormulaField[]
  chart: ReportChart | Record<string, never>
}

export interface ReportTemplate extends ReportTemplatePayload {
  id: string
  dataset_label: string
  folder: string | null
  folder_name: string | null
  version: number
  is_system: boolean
  created_at: string
  modified_at: string
}

export interface ReportFolder {
  id: string
  name: string
  description: string
  created_at: string
  modified_at: string
}

export interface ReportPreviewResult {
  columns: Array<{ code: string; label: string; data_type: string }>
  rows: Array<Record<string, string | number | null>>
  truncated: boolean
}

export interface ReportExport {
  id: string
  file_format: string
  file_name: string
  content_type: string
  byte_size: number
  created_at: string
}

export interface ReportRun {
  id: string
  template: string
  template_name: string
  requested_by_name: string
  requested_by_email: string
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED'
  parameters: Record<string, string | number | boolean | null>
  row_count: number
  error_message: string
  started_at: string | null
  completed_at: string | null
  created_at: string
  exports: ReportExport[]
}
