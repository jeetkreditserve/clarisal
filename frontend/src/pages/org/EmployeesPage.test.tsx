import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EmployeesPage } from '@/pages/org/EmployeesPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useDepartments = vi.fn()
const useDesignations = vi.fn()
const useEmployees = vi.fn()
const useInviteEmployee = vi.fn()
const useLocations = vi.fn()
const useOnboardingDocumentTypes = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useDepartments: () => useDepartments(),
  useDesignations: () => useDesignations(),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useInviteEmployee: () => useInviteEmployee(),
  useLocations: () => useLocations(),
  useOnboardingDocumentTypes: () => useOnboardingDocumentTypes(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <EmployeesPage />
    </MemoryRouter>,
  )
}

describe('EmployeesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useEmployees.mockReturnValue({
      isLoading: false,
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'employee-1',
            full_name: 'Priya Sharma',
            email: 'priya.sharma@acmeworkforce.com',
            employee_code: 'EMP002',
            designation: 'HR Operations Manager',
            department_name: 'People Operations',
            office_location_name: 'Registered Office',
            status: 'ACTIVE',
            date_of_joining: '2026-04-01',
          },
        ],
      },
    })
    useDepartments.mockReturnValue({
      data: [{ id: 'dept-1', name: 'People Operations', is_active: true }],
    })
    useDesignations.mockReturnValue({
      data: [{ id: 'des-1', name: 'Engineer', level: 1, is_active: true }],
    })
    useLocations.mockReturnValue({
      data: [{ id: 'loc-1', name: 'Registered Office', is_active: true }],
    })
    useOnboardingDocumentTypes.mockReturnValue({
      data: [{ id: 'doc-1', name: 'Address Proof', category: 'ADDRESS' }],
    })
    useInviteEmployee.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
  })

  it('submits the invite modal with selected documents and success feedback', async () => {
    const user = userEvent.setup()
    const inviteMutation = vi.fn().mockResolvedValue(undefined)
    useInviteEmployee.mockReturnValue({ isPending: false, mutateAsync: inviteMutation })
    useDesignations.mockReturnValue({
      data: [{ id: 'des-1', name: 'QA Engineer', level: 2, is_active: true }],
    })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Invite employee' }))
    await user.type(screen.getByLabelText('First name'), 'E2E')
    await user.type(screen.getByLabelText('Last name'), 'Tester')
    await user.type(screen.getByLabelText('Company email'), 'e2e.tester@acme.test')
    await user.click(screen.getByText('Select designation'))
    await user.click(screen.getByText('QA Engineer'))
    await user.click(screen.getByRole('checkbox', { name: /Address Proof/i }))
    const inviteButtons = screen.getAllByRole('button', { name: 'Invite employee' })
    await user.click(inviteButtons[inviteButtons.length - 1]!)

    await waitFor(() => {
      expect(inviteMutation).toHaveBeenCalledWith({
        company_email: 'e2e.tester@acme.test',
        first_name: 'E2E',
        last_name: 'Tester',
        designation: 'QA Engineer',
        employment_type: 'FULL_TIME',
        date_of_joining: null,
        department_id: null,
        office_location_id: null,
        required_document_type_ids: ['doc-1'],
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Employee invited.')
  }, 10000)

  it('renders the empty-state copy when no employees match the filters', () => {
    useEmployees.mockReturnValue({
      isLoading: false,
      data: { count: 0, next: null, previous: null, results: [] },
    })

    renderPage()

    expect(screen.getByText('No employees match the current filter')).toBeInTheDocument()
  })

  it('shows a toast error when the invite request fails without field errors', async () => {
    const user = userEvent.setup()
    const inviteMutation = vi.fn().mockRejectedValue(new Error('boom'))
    useInviteEmployee.mockReturnValue({ isPending: false, mutateAsync: inviteMutation })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Invite employee' }))
    await user.type(screen.getByLabelText('First name'), 'E2E')
    await user.type(screen.getByLabelText('Last name'), 'Tester')
    await user.type(screen.getByLabelText('Company email'), 'e2e.failure@acme.test')
    const inviteButtons = screen.getAllByRole('button', { name: 'Invite employee' })
    await user.click(inviteButtons[inviteButtons.length - 1]!)

    await waitFor(() => {
      expect(toastError).toHaveBeenCalledWith('Unable to invite employee.')
    })
  })
})
