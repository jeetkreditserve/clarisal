import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApprovalWorkflowBuilderPage } from '@/pages/org/ApprovalWorkflowBuilderPage'
import { ApprovalWorkflowReadinessPage } from '@/pages/org/ApprovalWorkflowReadinessPage'

const useApprovalWorkflow = vi.fn()
const useApprovalWorkflowCatalog = vi.fn()
const useApprovalWorkflowReadiness = vi.fn()
const useCreateApprovalWorkflow = vi.fn()
const useDepartments = vi.fn()
const useEmployees = vi.fn()
const useLeavePlans = vi.fn()
const useLocations = vi.fn()
const useSimulateApprovalWorkflow = vi.fn()
const useUpdateApprovalWorkflow = vi.fn()
const useCreateCtApprovalWorkflow = vi.fn()
const useCtOrgConfiguration = vi.fn()
const useCtOrgEmployees = vi.fn()
const useUpdateCtApprovalWorkflow = vi.fn()

vi.mock('@/hooks/useOrgAdmin', () => ({
  useApprovalWorkflow: (...args: unknown[]) => useApprovalWorkflow(...args),
  useApprovalWorkflowCatalog: (...args: unknown[]) => useApprovalWorkflowCatalog(...args),
  useApprovalWorkflowReadiness: (...args: unknown[]) => useApprovalWorkflowReadiness(...args),
  useCreateApprovalWorkflow: () => useCreateApprovalWorkflow(),
  useDepartments: (...args: unknown[]) => useDepartments(...args),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useLeavePlans: (...args: unknown[]) => useLeavePlans(...args),
  useLocations: (...args: unknown[]) => useLocations(...args),
  useSimulateApprovalWorkflow: () => useSimulateApprovalWorkflow(),
  useUpdateApprovalWorkflow: (...args: unknown[]) => useUpdateApprovalWorkflow(...args),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCreateCtApprovalWorkflow: (...args: unknown[]) => useCreateCtApprovalWorkflow(...args),
  useCtOrgConfiguration: (...args: unknown[]) => useCtOrgConfiguration(...args),
  useCtOrgEmployees: (...args: unknown[]) => useCtOrgEmployees(...args),
  useUpdateCtApprovalWorkflow: (...args: unknown[]) => useUpdateCtApprovalWorkflow(...args),
}))

function renderBuilder() {
  return render(
    <MemoryRouter initialEntries={['/org/approval-workflows/new']}>
      <Routes>
        <Route path="/org/approval-workflows/new" element={<ApprovalWorkflowBuilderPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderReadiness() {
  return render(
    <MemoryRouter initialEntries={['/org/approval-workflows/readiness']}>
      <Routes>
        <Route path="/org/approval-workflows/readiness" element={<ApprovalWorkflowReadinessPage />} />
        <Route path="/org/approval-workflows" element={<div>Workflow list</div>} />
        <Route path="/org/approval-workflows/new" element={<div>Workflow builder</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ApprovalWorkflowBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useApprovalWorkflow.mockReturnValue({ data: null, isLoading: false })
    useApprovalWorkflowCatalog.mockReturnValue({
      data: {
        request_kinds: [
          { kind: 'LEAVE', label: 'Leave', module: 'Time Off', supports_amount_rules: false, supports_leave_type_rules: true },
          { kind: 'PROMOTION', label: 'Promotion', module: 'Employee Lifecycle', supports_amount_rules: true, supports_leave_type_rules: false },
          { kind: 'TRANSFER', label: 'Transfer', module: 'Employee Lifecycle', supports_amount_rules: false, supports_leave_type_rules: false },
        ],
        approver_types: ['REPORTING_MANAGER', 'NTH_LEVEL_MANAGER', 'FINANCE_APPROVER', 'ROLE', 'SPECIFIC_EMPLOYEE', 'PRIMARY_ORG_ADMIN'],
        fallback_types: ['NONE', 'REPORTING_MANAGER', 'ROLE', 'SPECIFIC_EMPLOYEE', 'PRIMARY_ORG_ADMIN'],
        stage_modes: ['ALL', 'ANY'],
      },
    })
    useDepartments.mockReturnValue({ data: [] })
    useEmployees.mockReturnValue({ data: { results: [{ id: 'employee-1', full_name: 'Ava Patel', designation: 'Manager' }] } })
    useLeavePlans.mockReturnValue({ data: [] })
    useLocations.mockReturnValue({ data: [] })
    useCreateApprovalWorkflow.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useUpdateApprovalWorkflow.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useSimulateApprovalWorkflow.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useCreateCtApprovalWorkflow.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useUpdateCtApprovalWorkflow.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useCtOrgConfiguration.mockReturnValue({ data: null, isLoading: false })
    useCtOrgEmployees.mockReturnValue({ data: { results: [] } })
    useApprovalWorkflowReadiness.mockReturnValue({
      isLoading: false,
      data: [
        { kind: 'LEAVE', label: 'Leave', module: 'Time Off', ready: true, has_default_workflow: true, active_rule_count: 1 },
        { kind: 'PROMOTION', label: 'Promotion', module: 'Employee Lifecycle', ready: false, has_default_workflow: false, active_rule_count: 0 },
      ],
    })
  })

  it('shows promotion and transfer as configurable workflow types', async () => {
    const user = userEvent.setup()
    renderBuilder()

    await user.click(screen.getAllByRole('button', { name: /Leave/i })[0])

    expect(await screen.findByText('Promotion')).toBeInTheDocument()
    expect(screen.getByText('Transfer')).toBeInTheDocument()
  })

  it('flags missing workflow defaults on readiness page', () => {
    renderReadiness()

    expect(screen.getByText('1 request kind needs configuration.')).toBeInTheDocument()
    expect(screen.getByText('Promotion')).toBeInTheDocument()
    expect(screen.getByText('Needs workflow')).toBeInTheDocument()
  })
})
