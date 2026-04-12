import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { OrgChartD3 } from '@/components/OrgChartD3'

const sampleTree = [
  {
    id: 'emp-1',
    name: 'Aditi Rao',
    email: 'aditi@clarisal.com',
    employee_code: 'EMP001',
    designation: 'HR Director',
    department: 'People Operations',
    status: 'ACTIVE' as const,
    profile_picture: null,
    direct_reports: [
      {
        id: 'emp-2',
        name: 'Rohan Mehta',
        email: 'rohan@clarisal.com',
        employee_code: 'EMP002',
        designation: 'HR Manager',
        department: 'People Operations',
        status: 'ACTIVE' as const,
        profile_picture: null,
        direct_reports: [],
      },
    ],
  },
]

describe('OrgChartD3', () => {
  it('renders the interactive chart, search bar, and employee nodes', () => {
    render(<OrgChartD3 data={sampleTree} />)

    expect(screen.getByPlaceholderText('Search employees')).toBeInTheDocument()
    expect(screen.getByText('Aditi Rao')).toBeInTheDocument()
    expect(screen.getByText('Rohan Mehta')).toBeInTheDocument()
  })

  it('dims non-matching nodes when search is applied', async () => {
    const user = userEvent.setup()
    render(<OrgChartD3 data={sampleTree} />)

    await user.type(screen.getByPlaceholderText('Search employees'), 'rohan')

    expect(screen.getByTestId('org-chart-node-emp-2')).toHaveAttribute('data-match-state', 'match')
    expect(screen.getByTestId('org-chart-node-emp-1')).toHaveAttribute('data-match-state', 'dim')
  })

  it('renders an empty state when there is no reporting data', () => {
    render(<OrgChartD3 data={[]} />)

    expect(screen.getByText('No reporting structure yet')).toBeInTheDocument()
  })
})
