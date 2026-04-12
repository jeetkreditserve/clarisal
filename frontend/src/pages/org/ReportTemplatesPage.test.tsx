import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ReportRunDetailPage } from '@/pages/org/ReportRunDetailPage'
import { ReportTemplateListPage } from '@/pages/org/ReportTemplateListPage'

const {
  fetchReportFolders,
  fetchReportRun,
  fetchReportTemplates,
  runReportTemplate,
  saveReportTemplate,
  updateReportTemplate,
  downloadReportExport,
  useAuth,
  toastSuccess,
  toastError,
} = vi.hoisted(() => ({
  fetchReportFolders: vi.fn(),
  fetchReportRun: vi.fn(),
  fetchReportTemplates: vi.fn(),
  runReportTemplate: vi.fn(),
  saveReportTemplate: vi.fn(),
  updateReportTemplate: vi.fn(),
  downloadReportExport: vi.fn(),
  useAuth: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => useAuth(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: toastSuccess,
    error: toastError,
  },
}))

vi.mock('@/lib/api/reports', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/reports')>('@/lib/api/reports')
  return {
    ...actual,
    fetchReportFolders,
    fetchReportRun,
    fetchReportTemplates,
    runReportTemplate,
    saveReportTemplate,
    updateReportTemplate,
    downloadReportExport,
  }
})

function renderWithProviders(initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/org/reports/templates" element={<ReportTemplateListPage />} />
          <Route path="/org/reports/runs/:runId" element={<ReportRunDetailPage />} />
          <Route path="/org/dashboard" element={<div>Org dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Report template pages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({
      user: {
        effective_permissions: ['org.reports.read', 'org.reports.builder.manage', 'org.reports.export'],
      },
    })
    fetchReportFolders.mockResolvedValue([
      {
        id: 'folder-1',
        name: 'Workforce',
        description: 'Headcount and people reporting',
        created_at: '2026-04-12T08:00:00Z',
        modified_at: '2026-04-12T08:00:00Z',
      },
    ])
    fetchReportTemplates.mockResolvedValue([
      {
        id: 'template-1',
        dataset_code: 'employees',
        dataset_label: 'Employees',
        folder: 'folder-1',
        folder_name: 'Workforce',
        name: 'Monthly Headcount',
        description: '',
        status: 'DEPLOYED',
        columns: ['employee.employee_number'],
        filters: [],
        filter_logic: '',
        groupings: [],
        summaries: [],
        formula_fields: [],
        chart: {},
        version: 2,
        is_system: false,
        created_at: '2026-04-12T08:00:00Z',
        modified_at: '2026-04-12T08:00:00Z',
      },
      {
        id: 'template-2',
        dataset_code: 'leave_requests',
        dataset_label: 'Leave Requests',
        folder: null,
        folder_name: null,
        name: 'Leave Draft',
        description: '',
        status: 'DRAFT',
        columns: ['leave.status'],
        filters: [],
        filter_logic: '',
        groupings: [],
        summaries: [],
        formula_fields: [],
        chart: {},
        version: 1,
        is_system: false,
        created_at: '2026-04-12T08:00:00Z',
        modified_at: '2026-04-12T08:00:00Z',
      },
    ])
    runReportTemplate.mockResolvedValue({
      id: 'run-1',
      template: 'template-1',
      template_name: 'Monthly Headcount',
      requested_by_name: 'Report Admin',
      requested_by_email: 'reports@test.com',
      status: 'SUCCEEDED',
      parameters: {},
      row_count: 12,
      error_message: '',
      started_at: '2026-04-12T08:00:00Z',
      completed_at: '2026-04-12T08:01:00Z',
      created_at: '2026-04-12T08:00:00Z',
      exports: [],
    })
    saveReportTemplate.mockResolvedValue({
      id: 'template-3',
      dataset_code: 'employees',
      dataset_label: 'Employees',
      folder: 'folder-1',
      folder_name: 'Workforce',
      name: 'Monthly Headcount copy',
      description: '',
      status: 'DRAFT',
      columns: ['employee.employee_number'],
      filters: [],
      filter_logic: '',
      groupings: [],
      summaries: [],
      formula_fields: [],
      chart: {},
      version: 1,
      is_system: false,
      created_at: '2026-04-12T08:00:00Z',
      modified_at: '2026-04-12T08:00:00Z',
    })
    updateReportTemplate.mockResolvedValue({
      id: 'template-1',
      dataset_code: 'employees',
      dataset_label: 'Employees',
      folder: 'folder-1',
      folder_name: 'Workforce',
      name: 'Monthly Headcount',
      description: '',
      status: 'ARCHIVED',
      columns: ['employee.employee_number'],
      filters: [],
      filter_logic: '',
      groupings: [],
      summaries: [],
      formula_fields: [],
      chart: {},
      version: 3,
      is_system: false,
      created_at: '2026-04-12T08:00:00Z',
      modified_at: '2026-04-12T08:00:00Z',
    })
    fetchReportRun.mockResolvedValue({
      id: 'run-1',
      template: 'template-1',
      template_name: 'Monthly Headcount',
      requested_by_name: 'Report Admin',
      requested_by_email: 'reports@test.com',
      status: 'SUCCEEDED',
      parameters: {},
      row_count: 12,
      error_message: '',
      started_at: '2026-04-12T08:00:00Z',
      completed_at: '2026-04-12T08:01:00Z',
      created_at: '2026-04-12T08:00:00Z',
      exports: [
        {
          id: 'export-1',
          file_format: 'csv',
          file_name: 'monthly-headcount.csv',
          content_type: 'text/csv',
          byte_size: 1024,
          created_at: '2026-04-12T08:01:00Z',
        },
      ],
    })
    downloadReportExport.mockResolvedValue({
      blob: new Blob(['report']),
      filename: 'monthly-headcount.csv',
    })
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:report'),
      revokeObjectURL: vi.fn(),
    })
    HTMLAnchorElement.prototype.click = vi.fn()
  })

  it('filters templates by folder and triggers clone, archive, and run actions', async () => {
    const user = userEvent.setup()

    renderWithProviders(['/org/reports/templates'])

    expect(await screen.findByText('Monthly Headcount')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /all folders/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /workforce/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /deployed/i }))
    expect(screen.getByText('Monthly Headcount')).toBeInTheDocument()
    expect(screen.queryByText('Leave Draft')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /clone monthly headcount/i }))
    await waitFor(() => {
      expect(saveReportTemplate).toHaveBeenCalledWith(expect.objectContaining({ name: 'Monthly Headcount copy' }))
    })

    await user.click(screen.getByRole('button', { name: /archive monthly headcount/i }))
    await waitFor(() => {
      expect(updateReportTemplate).toHaveBeenCalledWith('template-1', expect.objectContaining({ status: 'ARCHIVED' }))
    })

    await user.click(screen.getByRole('button', { name: /run monthly headcount/i }))
    await waitFor(() => {
      expect(runReportTemplate).toHaveBeenCalledWith('template-1', { file_format: 'xlsx', parameters: {} })
    })
  })

  it('renders run detail and downloads an export', async () => {
    const user = userEvent.setup()

    renderWithProviders(['/org/reports/runs/run-1'])

    expect(await screen.findByText('Monthly Headcount')).toBeInTheDocument()
    expect(screen.getByText(/succeeded/i)).toBeInTheDocument()
    expect(screen.getByText('reports@test.com')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /download monthly-headcount\.csv/i }))

    await waitFor(() => {
      expect(downloadReportExport).toHaveBeenCalledWith('run-1', 'export-1')
    })
  })
})
