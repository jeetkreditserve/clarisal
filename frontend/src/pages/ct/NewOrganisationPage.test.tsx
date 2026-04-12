import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NewOrganisationPage } from '@/pages/ct/NewOrganisationPage'

const navigate = vi.fn()
const toastSuccess = vi.fn()
const toastError = vi.fn()

const useCreateOrganisation = vi.fn()
const useCreateOrganisationAddress = vi.fn()
const useCreateLicenceBatch = vi.fn()
const useCtOrgOnboardingProgress = vi.fn()
const useInviteOrgAdmin = vi.fn()
const useOrganisation = vi.fn()
const useSeedCtOrgMasters = vi.fn()
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

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigate,
  }
})

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCreateOrganisation: () => useCreateOrganisation(),
  useCreateOrganisationAddress: (...args: unknown[]) => useCreateOrganisationAddress(...args),
  useCreateLicenceBatch: (...args: unknown[]) => useCreateLicenceBatch(...args),
  useCtOrgOnboardingProgress: (...args: unknown[]) => useCtOrgOnboardingProgress(...args),
  useInviteOrgAdmin: (...args: unknown[]) => useInviteOrgAdmin(...args),
  useOrganisation: (...args: unknown[]) => useOrganisation(...args),
  useSeedCtOrgMasters: (...args: unknown[]) => useSeedCtOrgMasters(...args),
  useUpdateCtOrganisationFeatureFlags: (...args: unknown[]) => useUpdateCtOrganisationFeatureFlags(...args),
  useUpdateLicenceBatch: (...args: unknown[]) => useUpdateLicenceBatch(...args),
  useUpdateOrganisation: (...args: unknown[]) => useUpdateOrganisation(...args),
  useUpdateOrganisationAddress: (...args: unknown[]) => useUpdateOrganisationAddress(...args),
}))

function makeMutation<TArgs extends unknown[] = [], TResult = void>(impl?: (...args: TArgs) => Promise<TResult>) {
  return {
    isPending: false,
    mutateAsync: vi.fn(impl ?? (async () => undefined as TResult)),
  }
}

function makeOrganisationDetail(overrides: Record<string, unknown> = {}) {
  return {
    id: 'org-1',
    name: 'Acme Workforce',
    slug: 'acme-workforce',
    status: 'PENDING',
    billing_status: 'PENDING_PAYMENT',
    access_state: 'PROVISIONING',
    onboarding_stage: 'ORG_CREATED',
    licence_count: 0,
    country_code: 'IN',
    currency: 'INR',
    entity_type: 'PRIVATE_LIMITED',
    entity_type_label: 'Private Limited',
    pan_number: 'ABCDE1234F', // pragma: allowlist secret
    tan_number: '',
    esi_branch_code: '',
    address: 'Bengaluru',
    phone: '',
    email: '',
    logo_url: null,
    primary_admin_email: 'owner@acme.test',
    primary_admin: {
      first_name: 'Aditi',
      last_name: 'Rao',
      full_name: 'Aditi Rao',
      email: 'owner@acme.test',
      phone: '+919876543210',
      status: 'DRAFT',
      invited_user_id: null,
      invited_user_email: null,
      invitation_sent_at: null,
      accepted_at: null,
      modified_at: '2026-04-11T10:00:00Z',
    },
    bootstrap_admin: {
      first_name: 'Aditi',
      last_name: 'Rao',
      full_name: 'Aditi Rao',
      email: 'owner@acme.test',
      phone: '+919876543210',
      status: 'DRAFT',
      invited_user_id: null,
      invited_user_email: null,
      invitation_sent_at: null,
      accepted_at: null,
      modified_at: '2026-04-11T10:00:00Z',
    },
    paid_marked_at: null,
    activated_at: null,
    suspended_at: null,
    created_by_email: 'ct@example.com',
    created_at: '2026-04-11T09:00:00Z',
    modified_at: '2026-04-11T10:00:00Z',
    admin_count: 0,
    employee_count: 0,
    holiday_calendar_count: 0,
    note_count: 0,
    feature_flags: [
      { feature_code: 'ATTENDANCE', label: 'Attendance', is_enabled: true, is_default: true },
      { feature_code: 'APPROVALS', label: 'Approvals', is_enabled: true, is_default: true },
      { feature_code: 'PAYROLL', label: 'Payroll', is_enabled: true, is_default: true },
      { feature_code: 'RECRUITMENT', label: 'Recruitment', is_enabled: false, is_default: true },
      { feature_code: 'PERFORMANCE', label: 'Performance', is_enabled: false, is_default: true },
      { feature_code: 'ASSETS', label: 'Assets', is_enabled: false, is_default: true },
    ],
    addresses: [
      {
        id: 'registered-1',
        address_type: 'REGISTERED',
        address_type_label: 'Registered',
        label: 'Registered Office',
        line1: '123 Residency Road',
        line2: '',
        city: 'Bengaluru',
        state: 'Karnataka',
        state_code: 'KA',
        country: 'India',
        country_code: 'IN',
        pincode: '560001',
        gstin: '29ABCDE1234F1Z5', // pragma: allowlist secret
        is_active: true,
        created_at: '2026-04-11T09:00:00Z',
        modified_at: '2026-04-11T09:00:00Z',
      },
      {
        id: 'billing-1',
        address_type: 'BILLING',
        address_type_label: 'Billing',
        label: 'Billing Address',
        line1: '123 Residency Road',
        line2: '',
        city: 'Bengaluru',
        state: 'Karnataka',
        state_code: 'KA',
        country: 'India',
        country_code: 'IN',
        pincode: '560001',
        gstin: '29ABCDE1234F1Z5', // pragma: allowlist secret
        is_active: true,
        created_at: '2026-04-11T09:00:00Z',
        modified_at: '2026-04-11T09:00:00Z',
      },
    ],
    legal_identifiers: [],
    tax_registrations: [],
    state_transitions: [],
    lifecycle_events: [],
    licence_ledger_entries: [],
    licence_summary: {
      active_paid_quantity: 0,
      allocated: 0,
      available: 0,
      overage: 0,
      has_overage: false,
      utilisation_percent: 0,
    },
    licence_batches: [],
    batch_defaults: {
      start_date: '2026-04-11',
      end_date: '2026-05-10',
      price_per_licence_per_month: '999.00',
      billing_months: 1,
      total_amount: '999.00',
    },
    ...overrides,
  }
}

function renderPage(initialEntry = '/ct/organisations/new') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/ct/organisations/new" element={<NewOrganisationPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function chooseSelect(user: ReturnType<typeof userEvent.setup>, label: RegExp, option: string, index = 0) {
  const trigger = screen.getAllByLabelText(label)[index]
  await user.click(trigger)
  await user.click(await screen.findByRole('button', { name: new RegExp(option, 'i') }))
}

async function completeProfileStep(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/organisation name/i), 'Acme Workforce')
  await user.type(screen.getByLabelText(/pan number/i), 'ABCDE1234F') // pragma: allowlist secret
  await user.type(screen.getByLabelText(/first name/i), 'Aditi')
  await user.type(screen.getByLabelText(/last name/i), 'Rao')
  await user.type(screen.getByLabelText(/work email/i), 'owner@acme.test')
  await user.click(screen.getByLabelText(/same as registered address/i))
  await user.type(screen.getByLabelText(/address line 1/i), '123 Residency Road')
  await user.type(screen.getByLabelText(/^city/i), 'Bengaluru')
  await chooseSelect(user, /state/i, 'Karnataka')
  await user.type(screen.getByLabelText(/pin code|postal code|pincode/i), '560001')
  await user.type(screen.getByLabelText(/gstin/i), '29ABCDE1234F1Z5') // pragma: allowlist secret
  await user.click(screen.getByRole('button', { name: /next/i }))
}

describe('NewOrganisationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useCreateOrganisation.mockReturnValue(
      makeMutation(async () => makeOrganisationDetail())
    )
    useCreateOrganisationAddress.mockReturnValue(makeMutation(async () => ({ id: 'address-1' })))
    useCreateLicenceBatch.mockReturnValue(makeMutation(async () => ({ id: 'batch-1' })))
    useCtOrgOnboardingProgress.mockReturnValue({
      data: {
        current_stage: 'ORG_CREATED',
        completed_count: 0,
        total_count: 8,
        percent_complete: 0,
        steps: [
          {
            step: 'PAYROLL',
            label: 'Payroll',
            is_completed: false,
            completed_at: null,
            completion_source: null,
            blockers: ['No active payroll tax slab set'],
            can_reset: false,
            is_actionable: true,
            action: 'configuration',
          },
        ],
      },
      isFetched: true,
      refetch: vi.fn().mockResolvedValue(undefined),
    })
    useUpdateCtOrganisationFeatureFlags.mockReturnValue(makeMutation(async () => []))
    useUpdateLicenceBatch.mockReturnValue(makeMutation(async () => ({ id: 'batch-1' })))
    useUpdateOrganisation.mockReturnValue(makeMutation(async () => makeOrganisationDetail()))
    useUpdateOrganisationAddress.mockReturnValue(makeMutation(async () => ({ id: 'address-1' })))
    useSeedCtOrgMasters.mockReturnValue(
      makeMutation(async () => ({
        seeded: {
          payroll_components: { created_count: 4, existing_count: 0, total_count: 4, codes: ['BASIC', 'HRA'] },
          document_types: { created_count: 3, existing_count: 0, total_count: 3 },
        },
      }))
    )
    useInviteOrgAdmin.mockReturnValue(makeMutation(async () => ({ status: 'PENDING' })))
    useOrganisation.mockReturnValue({ isLoading: false, data: undefined })
  })

  it('creates an organisation, moves to the licence step, and keeps profile values when going back', async () => {
    const user = userEvent.setup()

    renderPage()

    expect(screen.getByText('Organisation Profile')).toBeInTheDocument()

    await completeProfileStep(user)

    await waitFor(() => {
      expect(useCreateOrganisation.mock.results[0]?.value.mutateAsync).toHaveBeenCalled()
    })
    expect(screen.getByText('Licence Configuration')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /back/i }))

    expect(screen.getByText('Organisation Profile')).toBeInTheDocument()
    expect(screen.getByLabelText(/organisation name/i)).toHaveValue('Acme Workforce')
    expect(screen.getByLabelText(/work email/i)).toHaveValue('owner@acme.test')
  }, 20000)

  it('saves progress and exits to the created organisation detail page', async () => {
    const user = userEvent.setup()

    renderPage()
    await completeProfileStep(user)

    await waitFor(() => {
      expect(screen.getByText('Licence Configuration')).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: 'Save & Exit' }))

    expect(navigate).toHaveBeenCalledWith('/ct/organisations/org-1', { replace: true })
  }, 20000)

  it('runs the remaining wizard steps and finishes on the organisation detail page', async () => {
    const user = userEvent.setup()

    renderPage()
    await completeProfileStep(user)

    await user.clear(screen.getByLabelText(/seat count/i))
    await user.type(screen.getByLabelText(/seat count/i), '25')
    await chooseSelect(user, /plan tier/i, 'Growth')
    await chooseSelect(user, /billing cycle/i, 'Annual')
    await user.click(screen.getByRole('button', { name: /next/i }))

    expect(screen.getByText('Feature Flags')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /next/i }))

    expect(screen.getByText('Payroll & Compliance Settings')).toBeInTheDocument()
    await user.type(screen.getByLabelText(/tds tan number/i), 'BLRA12345B')
    await user.type(screen.getByLabelText(/esi branch code/i), 'ESI-42')
    await user.click(screen.getByRole('button', { name: /next/i }))

    expect(screen.getByText('Seed Payroll Masters')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /seed default masters/i }))
    await waitFor(() => {
      expect(useSeedCtOrgMasters.mock.results[0]?.value.mutateAsync).toHaveBeenCalled()
    })
    await user.click(screen.getByRole('button', { name: /continue/i }))

    expect(screen.getByText('Invite First Admin')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /save and finish later/i }))

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/ct/organisations/org-1', { replace: true })
    })
  }, 20000)
})
