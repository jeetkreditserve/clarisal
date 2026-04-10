import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OrgAuditPage } from '@/pages/org/AuditPage'

const { useOrgAuditLogs, useCtAuditLogs } = vi.hoisted(() => ({
  useOrgAuditLogs: vi.fn(),
  useCtAuditLogs: vi.fn(),
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useOrgAuditLogs: (...args: unknown[]) => useOrgAuditLogs(...args),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCtAuditLogs: (...args: unknown[]) => useCtAuditLogs(...args),
}))

vi.mock('@/components/ui/AppDatePicker', () => ({
  AppDatePicker: ({ id, value = '', onValueChange, placeholder = 'Select date' }: { id?: string; value?: string; onValueChange: (value: string) => void; placeholder?: string }) => (
    <input
      id={id}
      data-testid="app-date-picker"
      aria-label={placeholder}
      value={value}
      onChange={(event) => onValueChange(event.target.value)}
    />
  ),
}))

describe('OrgAuditPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useOrgAuditLogs.mockReturnValue({
      data: { count: 0, results: [], next: null, previous: null },
      isLoading: false,
    })
    useCtAuditLogs.mockReturnValue({
      data: { count: 0, results: [], next: null, previous: null },
      isLoading: false,
    })
  })

  it('uses the shared date picker for audit date filters', () => {
    render(
      <MemoryRouter>
        <OrgAuditPage />
      </MemoryRouter>,
    )

    expect(screen.getAllByTestId('app-date-picker')).toHaveLength(2)
  })
})
