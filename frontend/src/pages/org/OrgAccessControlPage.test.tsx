import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AccessSimulatorPage } from '@/pages/org/AccessSimulatorPage'
import { CtAccessControlPage } from '@/pages/ct/CtAccessControlPage'
import { OrgAccessControlPage } from '@/pages/org/OrgAccessControlPage'

const {
  assignCtAccessRole,
  assignOrgAccessRole,
  createCtAccessRole,
  createOrgAccessRole,
  fetchCtAccessControlOverview,
  fetchOrgAccessControlOverview,
  simulateOrgAccess,
} = vi.hoisted(() => ({
  assignCtAccessRole: vi.fn(),
  assignOrgAccessRole: vi.fn(),
  createCtAccessRole: vi.fn(),
  createOrgAccessRole: vi.fn(),
  fetchCtAccessControlOverview: vi.fn(),
  fetchOrgAccessControlOverview: vi.fn(),
  simulateOrgAccess: vi.fn(),
}))

const useAuth = vi.fn()
const useDepartments = vi.fn()
const useEmployees = vi.fn()
const useLocations = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => useAuth(),
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useDepartments: (...args: unknown[]) => useDepartments(...args),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useLocations: (...args: unknown[]) => useLocations(...args),
}))

vi.mock('@/lib/api/access-control', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/access-control')>('@/lib/api/access-control')
  return {
    ...actual,
    assignCtAccessRole,
    assignOrgAccessRole,
    createCtAccessRole,
    createOrgAccessRole,
    fetchCtAccessControlOverview,
    fetchOrgAccessControlOverview,
    simulateOrgAccess,
  }
})

function renderWithProviders(initialEntries: string[], element: ReactNode) {
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
          <Route path="/org/access-control" element={<OrgAccessControlPage />} />
          <Route path="/org/access-control/simulator" element={<AccessSimulatorPage />} />
          <Route path="/ct/access-control" element={<CtAccessControlPage />} />
          <Route path="/org/dashboard" element={<div>Org dashboard</div>} />
          <Route path="/ct/dashboard" element={<div>CT dashboard</div>} />
          <Route path={initialEntries[0]} element={element} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function buildOrgOverview() {
  return {
    permissions: [
      { id: 'perm-1', code: 'org.employees.read', label: 'Read employees', domain: 'org', resource: 'employees', action: 'read', description: '' },
      { id: 'perm-2', code: 'org.payroll.process', label: 'Process payroll', domain: 'org', resource: 'payroll', action: 'process', description: '' },
      { id: 'perm-3', code: 'org.access_control.manage', label: 'Manage access', domain: 'org', resource: 'access_control', action: 'manage', description: '' },
    ],
    roles: [
      {
        id: 'role-1',
        code: 'ORG_PAYROLL_ADMIN',
        scope: 'ORGANISATION',
        name: 'Payroll Admin',
        description: 'Payroll access',
        is_system: true,
        permissions: ['org.employees.read', 'org.payroll.process'],
      },
    ],
    assignments: [
      {
        id: 'assignment-1',
        user_id: 'user-1',
        user_email: 'ava@example.com',
        user_full_name: 'Ava Patel',
        role_code: 'ORG_PAYROLL_ADMIN',
        role_name: 'Payroll Admin',
        is_active: true,
        scopes: [{ id: 'scope-1', scope_kind: 'SELECTED_OFFICE_LOCATIONS', office_location_id: 'loc-1', label: 'HQ' }],
      },
    ],
    users: [
      { id: 'user-1', email: 'ava@example.com', full_name: 'Ava Patel', account_type: 'WORKFORCE' },
      { id: 'user-2', email: 'morgan@example.com', full_name: 'Morgan Singh', account_type: 'WORKFORCE' },
    ],
  }
}

function buildCtOverview() {
  return {
    permissions: [
      { id: 'perm-1', code: 'ct.organisations.read', label: 'Read organisations', domain: 'ct', resource: 'organisations', action: 'read', description: '' },
      { id: 'perm-2', code: 'ct.billing.write', label: 'Manage billing', domain: 'ct', resource: 'billing', action: 'write', description: '' },
    ],
    roles: [
      {
        id: 'ct-role-1',
        code: 'CT_SUPPORT',
        scope: 'CONTROL_TOWER',
        name: 'CT Support',
        description: 'Support role',
        is_system: true,
        permissions: ['ct.organisations.read'],
      },
    ],
    assignments: [
      {
        id: 'ct-assignment-1',
        user_id: 'ct-user-1',
        user_email: 'support@example.com',
        user_full_name: 'Support Agent',
        role_code: 'CT_SUPPORT',
        role_name: 'CT Support',
        is_active: true,
        scopes: [],
      },
    ],
    users: [{ id: 'ct-user-1', email: 'support@example.com', full_name: 'Support Agent', account_type: 'CONTROL_TOWER' }],
  }
}

describe('Access control pages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({
      user: {
        id: 'viewer-1',
        effective_permissions: ['org.access_control.manage', 'ct.organisations.write'],
      },
    })
    useDepartments.mockReturnValue({ data: [{ id: 'dept-1', name: 'Finance' }] })
    useLocations.mockReturnValue({ data: [{ id: 'loc-1', name: 'HQ' }] })
    useEmployees.mockReturnValue({
      data: {
        results: [
          { id: 'employee-1', full_name: 'Ava Patel', designation: 'Manager' },
          { id: 'employee-2', full_name: 'Morgan Singh', designation: 'Analyst' },
        ],
      },
    })
    fetchOrgAccessControlOverview.mockResolvedValue(buildOrgOverview())
    fetchCtAccessControlOverview.mockResolvedValue(buildCtOverview())
    createOrgAccessRole.mockResolvedValue({
      id: 'role-created',
      code: 'ORG_CUSTOM_PAYROLL',
      scope: 'ORGANISATION',
      name: 'Custom Payroll',
      description: '',
      is_system: false,
      permissions: ['org.payroll.process'],
    })
    assignOrgAccessRole.mockResolvedValue({
      id: 'assignment-created',
      user_id: 'user-2',
      user_email: 'morgan@example.com',
      user_full_name: 'Morgan Singh',
      role_code: 'ORG_PAYROLL_ADMIN',
      role_name: 'Payroll Admin',
      is_active: true,
      scopes: [],
    })
    createCtAccessRole.mockResolvedValue({
      id: 'ct-role-created',
      code: 'CT_CUSTOM_BILLING',
      scope: 'CONTROL_TOWER',
      name: 'Billing Ops',
      description: '',
      is_system: false,
      permissions: ['ct.billing.write'],
    })
    assignCtAccessRole.mockResolvedValue({
      id: 'ct-assignment-created',
      user_id: 'ct-user-1',
      user_email: 'support@example.com',
      user_full_name: 'Support Agent',
      role_code: 'CT_SUPPORT',
      role_name: 'CT Support',
      is_active: true,
      scopes: [],
    })
    simulateOrgAccess.mockResolvedValue({
      user_id: 'user-1',
      organisation_id: 'org-1',
      effective_permissions: ['org.employees.read', 'org.payroll.process'],
      effective_scopes: [{ kind: 'SELECTED_OFFICE_LOCATIONS', label: 'HQ' }],
      employee_access: { employee_id: 'employee-1', allowed: true },
    })
  })

  it('redirects the org access-control page when the user lacks manage permission', async () => {
    useAuth.mockReturnValue({
      user: {
        id: 'viewer-1',
        effective_permissions: ['org.employees.read'],
      },
    })

    renderWithProviders(['/org/access-control'], <OrgAccessControlPage />)

    expect(await screen.findByText('Org dashboard')).toBeInTheDocument()
  })

  it('renders org roles, assignments, and the high-risk warning banner', async () => {
    renderWithProviders(['/org/access-control'], <OrgAccessControlPage />)

    expect((await screen.findAllByText('Payroll Admin')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Ava Patel')).length).toBeGreaterThan(0)
    expect(screen.getByText(/high-risk permissions/i)).toBeInTheDocument()
  })

  it('renders CT roles and assignments', async () => {
    renderWithProviders(['/ct/access-control'], <CtAccessControlPage />)

    expect((await screen.findAllByText('CT Support')).length).toBeGreaterThan(0)
    expect(screen.getByText('support@example.com')).toBeInTheDocument()
  })

  it('runs an access simulation and shows the effective result', async () => {
    const user = userEvent.setup()
    renderWithProviders(['/org/access-control/simulator'], <AccessSimulatorPage />)

    await screen.findByText('Access simulator')
    await user.selectOptions(screen.getByLabelText('User'), 'user-1')
    await user.selectOptions(screen.getByLabelText('Employee check'), 'employee-1')
    await user.click(screen.getByRole('button', { name: 'Run simulation' }))

    await waitFor(() => {
      expect(simulateOrgAccess).toHaveBeenCalled()
    })
    expect(simulateOrgAccess.mock.calls[0]?.[0]).toEqual({ user_id: 'user-1', employee_id: 'employee-1' })
    expect(await screen.findByText('org.payroll.process')).toBeInTheDocument()
    expect(screen.getByText('HQ')).toBeInTheDocument()
    expect(screen.getByText('In scope')).toBeInTheDocument()
  })
})
