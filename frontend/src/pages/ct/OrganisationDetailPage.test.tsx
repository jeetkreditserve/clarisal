import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OrganisationDetailPage } from '@/pages/ct/OrganisationDetailPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const refreshUser = vi.fn().mockResolvedValue(null)
const createExport = vi.fn().mockResolvedValue(undefined)

const useCreateCtApprovalWorkflow = vi.fn()
const useCreateCtDepartment = vi.fn()
const useCreateCtHolidayCalendar = vi.fn()
const useCreateCtLeaveCycle = vi.fn()
const useCreateCtLeavePlan = vi.fn()
const useCreateCtLocation = vi.fn()
const useCreateCtOrgNote = vi.fn()
const useCreateCtNotice = vi.fn()
const useCreateCtOnDutyPolicy = vi.fn()
const useCreateCtTenantDataExport = vi.fn()
const useCreateLicenceBatch = vi.fn()
const useCreateOrganisationAddress = vi.fn()
const useCtAuditLogs = vi.fn()
const useCtHolidayCalendars = vi.fn()
const useCtOrgAnalytics = vi.fn()
const useCtOrgApprovalSummary = vi.fn()
const useCtOrgAttendanceSummary = vi.fn()
const useCtOrgConfiguration = vi.fn()
const useCtOrgEmployeeDetail = vi.fn()
const useCtOrgEmployees = vi.fn()
const useCtOrgNotes = vi.fn()
const useCtOrgPayrollSummary = vi.fn()
const useCtOrgOnboardingChecklist = vi.fn()
const useCtOrgOnboardingProgress = vi.fn()
const useCtOrgOnboardingStepAction = vi.fn()
const useCtOrgOnboardingSummary = vi.fn()
const useCtTenantDataExportDownloadUrl = vi.fn()
const useCtTenantDataExports = vi.fn()
const useDeactivateCtDepartment = vi.fn()
const useDeactivateCtLocation = vi.fn()
const useDeactivateCtOrgAdmin = vi.fn()
const useDeactivateOrganisationAddress = vi.fn()
const useExtendLicenceBatchExpiry = vi.fn()
const useInviteOrgAdmin = vi.fn()
const useMarkLicenceBatchPaid = vi.fn()
const useOrganisation = vi.fn()
const useOrgAdmins = vi.fn()
const usePublishCtHolidayCalendar = vi.fn()
const usePublishCtNotice = vi.fn()
const useReactivateCtOrgAdmin = vi.fn()
const useResendOrgAdminInvite = vi.fn()
const useRestoreOrganisation = vi.fn()
const useRevokePendingCtOrgAdmin = vi.fn()
const useStartCtImpersonation = vi.fn()
const useSuspendOrganisation = vi.fn()
const useSyncCtOrgOnboardingProgress = vi.fn()
const useUpdateCtApprovalWorkflow = vi.fn()
const useUpdateCtBootstrapAdmin = vi.fn()
const useUpdateCtDepartment = vi.fn()
const useUpdateCtHolidayCalendar = vi.fn()
const useUpdateCtLeaveCycle = vi.fn()
const useUpdateCtLeavePlan = vi.fn()
const useUpdateCtLocation = vi.fn()
const useUpdateCtNotice = vi.fn()
const useUpdateCtOnDutyPolicy = vi.fn()
const useUpdateCtOrganisationFeatureFlags = vi.fn()
const useUpdateLicenceBatch = vi.fn()
const useUpdateOrganisation = vi.fn()
const useUpdateOrganisationAddress = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 'ct-user',
      email: 'ct@example.com',
      first_name: 'Control',
      last_name: 'Tower',
      full_name: 'Control Tower',
      account_type: 'CONTROL_TOWER',
      role: 'CONTROL_TOWER',
      organisation_id: null,
      organisation_name: null,
      default_route: '/ct/dashboard',
      has_control_tower_access: true,
      has_org_admin_access: false,
      has_employee_access: false,
      admin_organisations: [],
      employee_workspaces: [],
      impersonation: {
        session_id: 'act-as-1',
        organisation_id: 'org-1',
        organisation_name: 'Acme Workforce',
        reason: 'Support review',
        started_at: '2026-04-07T10:00:00Z',
        refreshed_at: '2026-04-07T10:05:00Z',
        is_active: true,
        return_path: '/ct/organisations/org-1',
        target_org_admin: null,
      },
      feature_flags: {},
      is_active: true,
    },
    refreshUser,
  }),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCreateCtApprovalWorkflow: () => useCreateCtApprovalWorkflow(),
  useCreateCtDepartment: () => useCreateCtDepartment(),
  useCreateCtHolidayCalendar: () => useCreateCtHolidayCalendar(),
  useCreateCtLeaveCycle: () => useCreateCtLeaveCycle(),
  useCreateCtLeavePlan: () => useCreateCtLeavePlan(),
  useCreateCtLocation: () => useCreateCtLocation(),
  useCreateCtOrgNote: () => useCreateCtOrgNote(),
  useCreateCtNotice: () => useCreateCtNotice(),
  useCreateCtOnDutyPolicy: () => useCreateCtOnDutyPolicy(),
  useCreateCtTenantDataExport: () => useCreateCtTenantDataExport(),
  useCreateLicenceBatch: () => useCreateLicenceBatch(),
  useCreateOrganisationAddress: () => useCreateOrganisationAddress(),
  useCtAuditLogs: (...args: unknown[]) => useCtAuditLogs(...args),
  useCtHolidayCalendars: (...args: unknown[]) => useCtHolidayCalendars(...args),
  useCtOrgAnalytics: (...args: unknown[]) => useCtOrgAnalytics(...args),
  useCtOrgApprovalSummary: (...args: unknown[]) => useCtOrgApprovalSummary(...args),
  useCtOrgAttendanceSummary: (...args: unknown[]) => useCtOrgAttendanceSummary(...args),
  useCtOrgConfiguration: (...args: unknown[]) => useCtOrgConfiguration(...args),
  useCtOrgEmployeeDetail: (...args: unknown[]) => useCtOrgEmployeeDetail(...args),
  useCtOrgEmployees: (...args: unknown[]) => useCtOrgEmployees(...args),
  useCtOrgNotes: (...args: unknown[]) => useCtOrgNotes(...args),
  useCtOrgPayrollSummary: (...args: unknown[]) => useCtOrgPayrollSummary(...args),
  useCtOrgOnboardingChecklist: (...args: unknown[]) => useCtOrgOnboardingChecklist(...args),
  useCtOrgOnboardingProgress: (...args: unknown[]) => useCtOrgOnboardingProgress(...args),
  useCtOrgOnboardingStepAction: (...args: unknown[]) => useCtOrgOnboardingStepAction(...args),
  useCtOrgOnboardingSummary: (...args: unknown[]) => useCtOrgOnboardingSummary(...args),
  useCtTenantDataExportDownloadUrl: (...args: unknown[]) => useCtTenantDataExportDownloadUrl(...args),
  useCtTenantDataExports: (...args: unknown[]) => useCtTenantDataExports(...args),
  useDeactivateCtDepartment: () => useDeactivateCtDepartment(),
  useDeactivateCtLocation: () => useDeactivateCtLocation(),
  useDeactivateCtOrgAdmin: () => useDeactivateCtOrgAdmin(),
  useDeactivateOrganisationAddress: () => useDeactivateOrganisationAddress(),
  useExtendLicenceBatchExpiry: () => useExtendLicenceBatchExpiry(),
  useInviteOrgAdmin: () => useInviteOrgAdmin(),
  useMarkLicenceBatchPaid: () => useMarkLicenceBatchPaid(),
  useOrganisation: (...args: unknown[]) => useOrganisation(...args),
  useOrgAdmins: (...args: unknown[]) => useOrgAdmins(...args),
  usePublishCtHolidayCalendar: () => usePublishCtHolidayCalendar(),
  usePublishCtNotice: () => usePublishCtNotice(),
  useReactivateCtOrgAdmin: () => useReactivateCtOrgAdmin(),
  useResendOrgAdminInvite: () => useResendOrgAdminInvite(),
  useRestoreOrganisation: () => useRestoreOrganisation(),
  useRevokePendingCtOrgAdmin: () => useRevokePendingCtOrgAdmin(),
  useStartCtImpersonation: () => useStartCtImpersonation(),
  useSuspendOrganisation: () => useSuspendOrganisation(),
  useSyncCtOrgOnboardingProgress: () => useSyncCtOrgOnboardingProgress(),
  useUpdateCtApprovalWorkflow: () => useUpdateCtApprovalWorkflow(),
  useUpdateCtBootstrapAdmin: () => useUpdateCtBootstrapAdmin(),
  useUpdateCtDepartment: () => useUpdateCtDepartment(),
  useUpdateCtHolidayCalendar: () => useUpdateCtHolidayCalendar(),
  useUpdateCtLeaveCycle: () => useUpdateCtLeaveCycle(),
  useUpdateCtLeavePlan: () => useUpdateCtLeavePlan(),
  useUpdateCtLocation: () => useUpdateCtLocation(),
  useUpdateCtNotice: () => useUpdateCtNotice(),
  useUpdateCtOnDutyPolicy: () => useUpdateCtOnDutyPolicy(),
  useUpdateCtOrganisationFeatureFlags: () => useUpdateCtOrganisationFeatureFlags(),
  useUpdateLicenceBatch: () => useUpdateLicenceBatch(),
  useUpdateOrganisation: () => useUpdateOrganisation(),
  useUpdateOrganisationAddress: () => useUpdateOrganisationAddress(),
}))

function makeMutation() {
  return { isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/ct/organisations/org-1']}>
      <Routes>
        <Route path="/ct/organisations/:id" element={<OrganisationDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

function makeOrganisationDetail(overrides: Record<string, unknown> = {}) {
  return {
    id: 'org-1',
    name: 'Acme Workforce',
    slug: 'acme-workforce',
    status: 'ACTIVE',
    billing_status: 'PAID',
    access_state: 'ACTIVE',
    onboarding_stage: 'EMPLOYEES_INVITED',
    licence_count: 25,
    country_code: 'IN',
    currency: 'INR',
    entity_type: 'PRIVATE_LIMITED',
    entity_type_label: 'Private Limited',
    pan_number: 'ABCDE1234F', // pragma: allowlist secret
    address: 'Bengaluru',
    phone: '',
    email: '',
    logo_url: null,
    primary_admin_email: 'admin@example.com',
    primary_admin: null,
    bootstrap_admin: null,
    paid_marked_at: '2026-04-01T00:00:00Z',
    activated_at: '2026-04-02T00:00:00Z',
    suspended_at: null,
    created_by_email: 'ct@example.com',
    created_at: '2026-04-01T00:00:00Z',
    modified_at: '2026-04-07T00:00:00Z',
    admin_count: 2,
    employee_count: 10,
    holiday_calendar_count: 1,
    note_count: 2,
    configuration_summary: {
      locations: 0,
      departments: 0,
      leave_cycles: 0,
      leave_plans: 0,
      on_duty_policies: 0,
      approval_workflows: 0,
      notices: 0,
    },
    operations_guard: {
      licence_expired: false,
      admin_mutations_blocked: false,
      approval_actions_blocked: false,
      seat_assignment_blocked: false,
      reason: '',
      summary: {
        active_paid_quantity: 25,
        allocated: 10,
        available: 15,
        overage: 0,
        has_overage: false,
        utilisation_percent: 40,
      },
    },
    feature_flags: [],
    addresses: [],
    legal_identifiers: [],
    tax_registrations: [],
    state_transitions: [],
    lifecycle_events: [],
    licence_ledger_entries: [],
    licence_summary: {
      active_paid_quantity: 25,
      allocated: 10,
      available: 15,
      overage: 0,
      has_overage: false,
      utilisation_percent: 40,
    },
    licence_batches: [
      {
        id: 'batch-1',
        quantity: 25,
        price_per_licence_per_month: '1000.00',
        start_date: '2026-04-01',
        end_date: '2026-04-30',
        billing_months: 1,
        total_amount: '25000.00',
        payment_status: 'PAID',
        lifecycle_state: 'ACTIVE',
        note: '',
        payment_provider: 'RAZORPAY',
        payment_reference: 'pay_1',
        invoice_reference: 'inv_1',
        created_by_email: 'ct@example.com',
        paid_by_email: 'ct@example.com',
        paid_at: '2026-04-01',
        created_at: '2026-04-01T00:00:00Z',
        modified_at: '2026-04-01T00:00:00Z',
      },
    ],
    batch_defaults: {
      start_date: '2026-05-01',
      end_date: '2026-05-31',
      price_per_licence_per_month: '1000.00',
      billing_months: 1,
      total_amount: '25000.00',
    },
    ...overrides,
  }
}

describe('OrganisationDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.assign(window, { open: vi.fn() })

    useOrganisation.mockReturnValue({
      isLoading: false,
      data: makeOrganisationDetail(),
    })
    useOrgAdmins.mockReturnValue({ data: [] })
    useCtOrgEmployees.mockReturnValue({ isLoading: false, data: { count: 0, next: null, previous: null, results: [] } })
    useCtOrgEmployeeDetail.mockReturnValue({ isLoading: false, data: null })
    useCtHolidayCalendars.mockReturnValue({ isLoading: false, data: [] })
    useCtOrgConfiguration.mockReturnValue({
      isLoading: false,
      data: {
        locations: [],
        departments: [],
        leave_cycles: [],
        leave_plans: [],
        on_duty_policies: [],
        approval_workflows: [],
        notices: [],
      },
    })
    useCtOrgOnboardingSummary.mockReturnValue({
      isLoading: false,
      data: {
        onboarding_status_counts: { NOT_STARTED: 0, BASIC_DETAILS_PENDING: 0, DOCUMENTS_PENDING: 0, COMPLETE: 0 },
        blocked_employees: [],
        top_blocker_types: [],
        document_request_status_counts: { REQUESTED: 0, SUBMITTED: 0, REJECTED: 0, VERIFIED: 0 },
      },
    })
    useCtOrgOnboardingChecklist.mockReturnValue({
      data: {
        stages: [],
        activation_blockers: [],
      },
    })
    useCtOrgOnboardingProgress.mockReturnValue({
      isLoading: false,
      data: {
        steps: [],
      },
    })
    useCtOrgAnalytics.mockReturnValue({
      isLoading: false,
      data: {
        latest: {
          snapshot_date: '2026-04-07',
          active_employees: 10,
          active_users: 10,
          attendance_days_count: 9,
          leave_requests_count: 2,
          payroll_runs_count: 1,
          pending_approvals_count: 1,
          metadata: {},
        },
        series: {
          active_employees: [{ date: '2026-04-07', value: 10 }],
          active_users: [{ date: '2026-04-07', value: 10 }],
          attendance_days_count: [{ date: '2026-04-07', value: 9 }],
          leave_requests_count: [{ date: '2026-04-07', value: 2 }],
          payroll_runs_count: [{ date: '2026-04-07', value: 1 }],
          pending_approvals_count: [{ date: '2026-04-07', value: 1 }],
        },
      },
    })
    useCtTenantDataExports.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'export-1',
          export_type: 'AUDIT_LOG',
          status: 'COMPLETED',
          file_name: 'audit-log.zip',
          content_type: 'application/zip',
          file_size_bytes: 2048,
          generated_at: '2026-04-07T11:00:00Z',
          failure_reason: '',
          metadata: { row_count: 12 },
          requested_by: { id: 'ct-user', full_name: 'Control Tower', email: 'ct@example.com' },
          created_at: '2026-04-07T10:58:00Z',
          modified_at: '2026-04-07T11:00:00Z',
        },
      ],
    })
    useCtOrgAttendanceSummary.mockReturnValue({ isLoading: false, data: null })
    useCtOrgApprovalSummary.mockReturnValue({ isLoading: false, data: null })
    useCtOrgPayrollSummary.mockReturnValue({ isLoading: false, data: null })
    useCtAuditLogs.mockReturnValue({ data: [] })
    useCtOrgNotes.mockReturnValue({ isLoading: false, data: [] })

    useUpdateOrganisation.mockReturnValue(makeMutation())
    useUpdateCtBootstrapAdmin.mockReturnValue(makeMutation())
    useCreateOrganisationAddress.mockReturnValue(makeMutation())
    useUpdateOrganisationAddress.mockReturnValue(makeMutation())
    useDeactivateOrganisationAddress.mockReturnValue(makeMutation())
    useSuspendOrganisation.mockReturnValue(makeMutation())
    useRestoreOrganisation.mockReturnValue(makeMutation())
    useStartCtImpersonation.mockReturnValue(makeMutation())
    useUpdateCtOrganisationFeatureFlags.mockReturnValue(makeMutation())
    useInviteOrgAdmin.mockReturnValue(makeMutation())
    useResendOrgAdminInvite.mockReturnValue(makeMutation())
    useDeactivateCtOrgAdmin.mockReturnValue(makeMutation())
    useReactivateCtOrgAdmin.mockReturnValue(makeMutation())
    useRevokePendingCtOrgAdmin.mockReturnValue(makeMutation())
    useCreateLicenceBatch.mockReturnValue(makeMutation())
    useUpdateLicenceBatch.mockReturnValue(makeMutation())
    useMarkLicenceBatchPaid.mockReturnValue(makeMutation())
    useExtendLicenceBatchExpiry.mockReturnValue(makeMutation())
    useCreateCtHolidayCalendar.mockReturnValue(makeMutation())
    useUpdateCtHolidayCalendar.mockReturnValue(makeMutation())
    usePublishCtHolidayCalendar.mockReturnValue(makeMutation())
    useCreateCtOrgNote.mockReturnValue(makeMutation())
    useCreateCtLocation.mockReturnValue(makeMutation())
    useUpdateCtLocation.mockReturnValue(makeMutation())
    useDeactivateCtLocation.mockReturnValue(makeMutation())
    useCreateCtDepartment.mockReturnValue(makeMutation())
    useUpdateCtDepartment.mockReturnValue(makeMutation())
    useDeactivateCtDepartment.mockReturnValue(makeMutation())
    useCreateCtLeaveCycle.mockReturnValue(makeMutation())
    useUpdateCtLeaveCycle.mockReturnValue(makeMutation())
    useCreateCtLeavePlan.mockReturnValue(makeMutation())
    useUpdateCtLeavePlan.mockReturnValue(makeMutation())
    useCreateCtOnDutyPolicy.mockReturnValue(makeMutation())
    useUpdateCtOnDutyPolicy.mockReturnValue(makeMutation())
    useCreateCtApprovalWorkflow.mockReturnValue(makeMutation())
    useUpdateCtApprovalWorkflow.mockReturnValue(makeMutation())
    useCreateCtNotice.mockReturnValue(makeMutation())
    useUpdateCtNotice.mockReturnValue(makeMutation())
    usePublishCtNotice.mockReturnValue(makeMutation())
    useSyncCtOrgOnboardingProgress.mockReturnValue(makeMutation())
    useCtOrgOnboardingStepAction.mockReturnValue(makeMutation())
    useCtTenantDataExportDownloadUrl.mockReturnValue(makeMutation())
    useCreateCtTenantDataExport.mockReturnValue({ isPending: false, mutateAsync: createExport })
  })

  it('renders impersonation guidance and requests tenant exports', async () => {
    const user = userEvent.setup()

    renderPage()

    expect(screen.getByText('This Control Tower act-as session allows a narrow write set only.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reactivate admin' })).toBeInTheDocument()
    expect(screen.getByText('Data & Compliance')).toBeInTheDocument()
    expect(screen.getByText('Employees CSV')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download' })).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: 'Request export' })[0])

    await waitFor(() => {
      expect(createExport).toHaveBeenCalledWith({ export_type: 'EMPLOYEES' })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Employees CSV requested.')
  })

  it('shows a resume onboarding banner for incomplete wizard setups', () => {
    useOrganisation.mockReturnValue({
      isLoading: false,
      data: makeOrganisationDetail({
        status: 'PENDING',
        billing_status: 'PENDING_PAYMENT',
        access_state: 'PROVISIONING',
        onboarding_stage: 'ORG_CREATED',
        licence_batches: [],
        licence_summary: {
          active_paid_quantity: 0,
          allocated: 0,
          available: 0,
          overage: 0,
          has_overage: false,
          utilisation_percent: 0,
        },
      }),
    })
    useCtOrgOnboardingProgress.mockReturnValue({
      isLoading: false,
      data: {
        current_stage: 'ORG_CREATED',
        completed_count: 1,
        total_count: 8,
        percent_complete: 13,
        steps: [
          {
            step: 'ADMINS',
            label: 'Admins',
            is_completed: false,
            completed_at: null,
            completion_source: null,
            blockers: ['No active organisation admin'],
            can_reset: false,
            is_actionable: true,
            action: 'admins',
          },
        ],
      },
    })

    renderPage()

    expect(screen.getByText('Resume onboarding wizard')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Resume onboarding wizard' })).toHaveAttribute(
      'href',
      '/ct/organisations/new?organisationId=org-1',
    )
  })
})
