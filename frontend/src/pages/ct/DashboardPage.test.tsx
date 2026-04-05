import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CTDashboardPage } from '@/pages/ct/DashboardPage'

const useCtStats = vi.fn()
const useOrganisations = vi.fn()

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCtStats: () => useCtStats(),
  useOrganisations: (...args: unknown[]) => useOrganisations(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <CTDashboardPage />
    </MemoryRouter>,
  )
}

describe('CTDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders metrics and recent organisations when data is available', () => {
    useCtStats.mockReturnValue({
      data: {
        total_organisations: 5,
        active_organisations: 2,
        pending_organisations: 1,
        allocated_licences: 12,
        total_licences: 20,
        total_employees: 16,
        suspended_organisations: 1,
      },
    })
    useOrganisations.mockReturnValue({
      data: {
        results: [
          {
            id: 'org-1',
            name: 'Acme Workforce Pvt Ltd',
            slug: 'acme-workforce',
            status: 'ACTIVE',
            licence_count: 12,
            created_at: '2026-04-01T00:00:00Z',
          },
        ],
      },
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Platform dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Total organisations')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('Allocated licences')).toBeInTheDocument()
    expect(screen.getByText('12/20')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Acme Workforce Pvt Ltd' })).toHaveAttribute('href', '/ct/organisations/org-1')
  })

  it('renders the empty state when there are no recent organisations', () => {
    useCtStats.mockReturnValue({
      data: {
        total_organisations: 0,
        active_organisations: 0,
        pending_organisations: 0,
        allocated_licences: 0,
        total_licences: 0,
        total_employees: 0,
        suspended_organisations: 0,
      },
    })
    useOrganisations.mockReturnValue({
      data: {
        results: [],
      },
    })

    renderPage()

    expect(screen.getByText('No organisations yet')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Create organisation' })[0]).toHaveAttribute('href', '/ct/organisations/new')
  })
})
