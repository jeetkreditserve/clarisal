import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OrgChartPage } from '@/pages/org/OrgChartPage'

const useOrgChart = vi.fn()
const useOrgChartCycles = vi.fn()

vi.mock('@/hooks/useOrgAdmin', () => ({
  useOrgChart: (includeInactive?: boolean) => useOrgChart(includeInactive),
  useOrgChartCycles: () => useOrgChartCycles(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <OrgChartPage />
    </MemoryRouter>,
  )
}

describe('OrgChartPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the reporting tree and cycle warning when backend data is available', () => {
    useOrgChart.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'emp-1',
          name: 'Aditi Rao',
          email: 'aditi@clarisal.com',
          employee_code: 'EMP001',
          designation: 'HR Director',
          department: 'People Operations',
          status: 'ACTIVE',
          profile_picture: null,
          direct_reports: [
            {
              id: 'emp-2',
              name: 'Rohan Mehta',
              email: 'rohan@clarisal.com',
              employee_code: 'EMP002',
              designation: 'HR Manager',
              department: 'People Operations',
              status: 'ACTIVE',
              profile_picture: null,
              direct_reports: [],
            },
          ],
        },
      ],
    })
    useOrgChartCycles.mockReturnValue({
      data: {
        has_cycles: true,
        cycles: [['emp-1', 'emp-2', 'emp-1']],
      },
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Organisation chart' })).toBeInTheDocument()
    expect(screen.getByText('Aditi Rao')).toBeInTheDocument()
    expect(screen.getByText('Rohan Mehta')).toBeInTheDocument()
    expect(screen.getByText('Reporting cycle detected')).toBeInTheDocument()
  })

  it('renders the empty state when the organisation has no reporting roots yet', () => {
    useOrgChart.mockReturnValue({ isLoading: false, data: [] })
    useOrgChartCycles.mockReturnValue({ data: { has_cycles: false, cycles: [] } })

    renderPage()

    expect(screen.getByText('No reporting structure yet')).toBeInTheDocument()
  })
})
