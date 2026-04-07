import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OrgLayout } from '@/components/layouts/OrgLayout'

const navigate = vi.fn()
const logout = vi.fn()
const refreshUser = vi.fn()
const stopImpersonation = vi.fn()
const refreshImpersonation = vi.fn()
const toastSuccess = vi.fn()
const toastError = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigate,
  }
})

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 'ct-user-1',
      email: 'ct@clarisal.com',
      account_type: 'CONTROL_TOWER',
      first_name: 'Control',
      last_name: 'Tower',
      full_name: 'Control Tower',
      role: 'CONTROL_TOWER',
      organisation_id: 'org-1',
      organisation_name: 'Northstar Labs',
      organisation_status: 'ACTIVE',
      organisation_onboarding_stage: 'ADMIN_ACTIVATED',
      organisation_access_state: 'ACTIVE',
      active_workspace_kind: 'ADMIN',
      default_route: '/org/dashboard',
      has_control_tower_access: true,
      has_org_admin_access: true,
      has_employee_access: false,
      admin_organisations: [],
      employee_workspaces: [],
      org_operations_guard: null,
      org_setup_required: false,
      org_setup_current_step: null,
      org_setup_completed_at: null,
      feature_flags: {
        ATTENDANCE: true,
        APPROVALS: true,
        BIOMETRICS: true,
        NOTICES: false,
        PAYROLL: true,
        PERFORMANCE: false,
        RECRUITMENT: false,
        REPORTS: true,
        TIMEOFF: true,
      },
      impersonation: {
        session_id: 'act-as-1',
        organisation_id: 'org-1',
        organisation_name: 'Northstar Labs',
        reason: 'Investigating payroll issue',
        started_at: '2026-04-04T10:00:00Z',
        refreshed_at: '2026-04-04T10:05:00Z',
        is_active: true,
        return_path: '/ct/organisations/org-1',
        target_org_admin: {
          id: 'admin-1',
          full_name: 'Aditi Rao',
          email: 'aditi@northstar.com',
        },
      },
      is_active: true,
    },
    logout,
    refreshUser,
  }),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useRefreshCtImpersonation: () => ({
    mutateAsync: refreshImpersonation,
  }),
  useStopCtImpersonation: () => ({
    isPending: false,
    mutateAsync: stopImpersonation,
  }),
}))

vi.mock('@/components/layouts/SidebarNav', () => ({
  SidebarNav: ({ groups }: { groups: Array<{ label: string; items: Array<{ label: string }> }> }) => (
    <div data-testid="sidebar-nav">
      {groups.map((group) => (
        <div key={group.label}>
          <p>{group.label}</p>
          {group.items.map((item) => (
            <span key={item.label}>{item.label}</span>
          ))}
        </div>
      ))}
    </div>
  ),
}))

vi.mock('@/components/layouts/WorkspaceSwitcher', () => ({
  WorkspaceSwitcher: () => <div data-testid="workspace-switcher" />,
}))

vi.mock('@/components/ui/NotificationBell', () => ({
  NotificationBell: () => <div data-testid="notification-bell" />,
}))

vi.mock('@/components/ui/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}))

vi.mock('@/components/org/OrgSetupBanner', () => ({
  OrgSetupBanner: () => <div data-testid="org-setup-banner" />,
}))

describe('OrgLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    refreshImpersonation.mockResolvedValue(undefined)
    stopImpersonation.mockResolvedValue({ organisation_id: 'org-1' })
    refreshUser.mockResolvedValue(null)
  })

  it('shows the impersonation banner and lets control tower stop the session', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <OrgLayout />
      </MemoryRouter>,
    )

    expect(screen.getByText('Control Tower impersonation is active.')).toBeInTheDocument()
    expect(screen.getByText(/Investigating payroll issue/)).toBeInTheDocument()
    expect(screen.getByText('Organisation workspace')).toBeInTheDocument()
    expect(screen.getByText('Attendance live')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reactivate admin' })).toHaveAttribute('href', '/ct/organisations/org-1?tab=admins')
    expect(screen.getByRole('link', { name: 'Reset onboarding step' })).toHaveAttribute('href', '/ct/organisations/org-1?tab=onboarding')
    expect(screen.getByRole('link', { name: 'Extend licence expiry' })).toHaveAttribute('href', '/ct/organisations/org-1?tab=licences')
    expect(screen.queryByText('Notices')).not.toBeInTheDocument()
    expect(screen.queryByText('Job postings')).not.toBeInTheDocument()
    expect(screen.queryByText('Goal cycles')).not.toBeInTheDocument()
    expect(screen.getByText('Payroll Preview')).toBeInTheDocument()

    await waitFor(() => {
      expect(refreshImpersonation).toHaveBeenCalled()
    })

    await user.click(screen.getByRole('button', { name: 'Stop impersonation' }))

    await waitFor(() => {
      expect(stopImpersonation).toHaveBeenCalled()
      expect(refreshUser).toHaveBeenCalled()
      expect(navigate).toHaveBeenCalledWith('/ct/organisations/org-1', { replace: true })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Returned to Control Tower.')
  })
})
