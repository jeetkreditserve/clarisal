import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HolidaysPage } from '@/pages/org/HolidaysPage'

const toastSuccess = vi.fn()
const useCreateHolidayCalendar = vi.fn()
const useHolidayCalendars = vi.fn()
const useLocations = vi.fn()
const usePublishHolidayCalendar = vi.fn()
const useUpdateHolidayCalendar = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: vi.fn(),
  },
}))

vi.mock('@/components/ui/AppDatePicker', () => ({
  AppDatePicker: ({ id, value = '', onValueChange, placeholder = 'Select holiday date' }: { id?: string; value?: string; onValueChange: (value: string) => void; placeholder?: string }) => (
    <input
      id={id}
      aria-label={placeholder}
      value={value}
      onChange={(event) => onValueChange(event.target.value)}
    />
  ),
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useCreateHolidayCalendar: () => useCreateHolidayCalendar(),
  useHolidayCalendars: () => useHolidayCalendars(),
  useLocations: () => useLocations(),
  usePublishHolidayCalendar: () => usePublishHolidayCalendar(),
  useUpdateHolidayCalendar: (...args: unknown[]) => useUpdateHolidayCalendar(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <HolidaysPage />
    </MemoryRouter>,
  )
}

describe('HolidaysPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useHolidayCalendars.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'calendar-1',
          name: 'Draft Holiday Calendar',
          year: 2026,
          description: '',
          status: 'DRAFT',
          is_default: true,
          location_ids: [],
          holidays: [{ id: 'holiday-1', name: 'Founders Day', holiday_date: '2026-04-01', classification: 'PUBLIC', session: 'FULL_DAY' }],
        },
      ],
    })
    useLocations.mockReturnValue({
      data: [{ id: 'loc-1', name: 'Registered Office', is_active: true }],
    })
    useCreateHolidayCalendar.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    usePublishHolidayCalendar.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useUpdateHolidayCalendar.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
  })

  it('creates a holiday calendar from the modal form', async () => {
    const user = userEvent.setup()
    const createMutation = vi.fn().mockResolvedValue(undefined)
    useCreateHolidayCalendar.mockReturnValue({ isPending: false, mutateAsync: createMutation })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Add holiday calendar' }))
    await user.type(screen.getByPlaceholderText('Calendar name'), 'FY 2027')
    await user.type(screen.getByPlaceholderText('Description'), 'Location-specific schedule')
    await user.type(screen.getByPlaceholderText('Holiday name'), 'New Year')
    await user.type(screen.getByLabelText('Select holiday date'), '2027-01-01')
    await user.click(screen.getByRole('button', { name: 'Save holiday calendar' }))

    await waitFor(() => {
      expect(createMutation).toHaveBeenCalledWith({
        name: 'FY 2027',
        year: new Date().getFullYear(),
        description: 'Location-specific schedule',
        is_default: true,
        location_ids: [],
        holidays: [
          {
            name: 'New Year',
            holiday_date: '2027-01-01',
            classification: 'PUBLIC',
            session: 'FULL_DAY',
            description: '',
          },
        ],
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Holiday calendar created.')
  })

  it('publishes a draft calendar from the catalogue', async () => {
    const user = userEvent.setup()
    const publishMutation = vi.fn().mockResolvedValue(undefined)
    usePublishHolidayCalendar.mockReturnValue({ mutateAsync: publishMutation })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Publish' }))

    expect(publishMutation).toHaveBeenCalledWith('calendar-1')
  })
})
