import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NoticeEditorPage } from '@/pages/org/NoticeEditorPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()

const useCreateNotice = vi.fn()
const useDepartments = vi.fn()
const useEmployees = vi.fn()
const useLocations = vi.fn()
const useNotice = vi.fn()
const usePublishNotice = vi.fn()
const useUpdateNotice = vi.fn()
const useCreateCtNotice = vi.fn()
const useCtOrgConfiguration = vi.fn()
const useCtOrgEmployees = vi.fn()
const usePublishCtNotice = vi.fn()
const useUpdateCtNotice = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/components/ui/AppDateTimePicker', () => ({
  AppDateTimePicker: ({
    value,
    onValueChange,
    placeholder,
  }: {
    value?: string | null
    onValueChange: (value: string) => void
    placeholder?: string
  }) => (
    <button
      type="button"
      onClick={() =>
        onValueChange(
          placeholder === 'Schedule publish time'
            ? '2026-04-10T09:00'
            : '2026-04-09T09:00',
        )
      }
    >
      {value ?? placeholder ?? 'Pick date'}
    </button>
  ),
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useCreateNotice: () => useCreateNotice(),
  useDepartments: (...args: unknown[]) => useDepartments(...args),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useLocations: (...args: unknown[]) => useLocations(...args),
  useNotice: (...args: unknown[]) => useNotice(...args),
  usePublishNotice: () => usePublishNotice(),
  useUpdateNotice: (...args: unknown[]) => useUpdateNotice(...args),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCreateCtNotice: (...args: unknown[]) => useCreateCtNotice(...args),
  useCtOrgConfiguration: (...args: unknown[]) => useCtOrgConfiguration(...args),
  useCtOrgEmployees: (...args: unknown[]) => useCtOrgEmployees(...args),
  usePublishCtNotice: (...args: unknown[]) => usePublishCtNotice(...args),
  useUpdateCtNotice: (...args: unknown[]) => useUpdateCtNotice(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/org/notices/new']}>
      <Routes>
        <Route path="/org/notices/new" element={<NoticeEditorPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('NoticeEditorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useCreateNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useDepartments.mockReturnValue({ data: [] })
    useEmployees.mockReturnValue({ data: { results: [] } })
    useLocations.mockReturnValue({ data: [] })
    useNotice.mockReturnValue({ data: undefined, isLoading: false })
    usePublishNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useUpdateNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCreateCtNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCtOrgConfiguration.mockReturnValue({ data: undefined, isLoading: false })
    useCtOrgEmployees.mockReturnValue({ data: { results: [] } })
    usePublishCtNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useUpdateCtNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
  })

  it('shows scheduling warnings for missing publish time and invalid expiry windows', async () => {
    const user = userEvent.setup()

    renderPage()

    expect(
      screen.queryByText('Scheduled notices need a publish time before they can be automated.'),
    ).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Draft' }))
    await user.click(screen.getByRole('button', { name: 'Scheduled' }))

    expect(
      screen.getByText('Scheduled notices need a publish time before they can be automated.'),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Schedule publish time' }))

    expect(
      screen.queryByText('Scheduled notices need a publish time before they can be automated.'),
    ).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Optional expiry time' }))

    expect(screen.getByText('Expiry must be later than the scheduled publish time.')).toBeInTheDocument()
  })
})
