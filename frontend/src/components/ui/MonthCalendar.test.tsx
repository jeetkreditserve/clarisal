import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MonthCalendar } from '@/components/ui/MonthCalendar'

describe('MonthCalendar', () => {
  it('renders weekday headers, leading blanks, and day entries', () => {
    const { container } = render(
      <MonthCalendar
        month={{
          month: '2026-04',
          days: [
            {
              date: '2026-04-01',
              entries: [{ date: '2026-04-01', kind: 'LEAVE', label: 'Casual Leave', status: 'APPROVED', color: '#2563eb' }],
            },
            {
              date: '2026-04-02',
              entries: [],
            },
          ],
        } as any}
      />,
    )

    expect(screen.getByText('Mon')).toBeInTheDocument()
    expect(screen.getByText('Sun')).toBeInTheDocument()
    expect(container.querySelectorAll('.border-dashed')).toHaveLength(2)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('Casual Leave')).toBeInTheDocument()
    expect(screen.getByText('APPROVED')).toBeInTheDocument()
  })
})
