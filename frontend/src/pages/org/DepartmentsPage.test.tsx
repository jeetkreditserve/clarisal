import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DepartmentsPage } from '@/pages/org/DepartmentsPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useDepartments = vi.fn()
const useCreateDepartment = vi.fn()
const useUpdateDepartment = vi.fn()
const useDeactivateDepartment = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useDepartments: (...args: unknown[]) => useDepartments(...args),
  useCreateDepartment: () => useCreateDepartment(),
  useUpdateDepartment: () => useUpdateDepartment(),
  useDeactivateDepartment: () => useDeactivateDepartment(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <DepartmentsPage />
    </MemoryRouter>,
  )
}

describe('DepartmentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useDepartments.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'dept-1',
          name: 'Engineering',
          description: 'Builds internal systems.',
          parent_department_id: null,
          parent_department_name: null,
          is_active: true,
          modified_at: '2026-04-01T00:00:00Z',
        },
      ],
    })
    useCreateDepartment.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useUpdateDepartment.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useDeactivateDepartment.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue(undefined) })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('creates a department from the add modal', async () => {
    const user = userEvent.setup()
    const createMutation = vi.fn().mockResolvedValue(undefined)
    useCreateDepartment.mockReturnValue({ isPending: false, mutateAsync: createMutation })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Add department' }))
    await user.type(screen.getByLabelText('Department name'), 'Product')
    await user.type(screen.getByLabelText('Description'), 'Product delivery and execution')
    await user.click(screen.getByRole('button', { name: 'Create department' }))

    expect(createMutation).toHaveBeenCalledWith({
      name: 'Product',
      description: 'Product delivery and execution',
      parent_department_id: null,
    })
    expect(toastSuccess).toHaveBeenCalledWith('Department created.')
  })

  it('opens edit mode with prefilled values and saves updates', async () => {
    const user = userEvent.setup()
    const updateMutation = vi.fn().mockResolvedValue(undefined)
    useUpdateDepartment.mockReturnValue({ isPending: false, mutateAsync: updateMutation })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Edit' }))
    const nameInput = screen.getByLabelText('Department name')
    expect(nameInput).toHaveValue('Engineering')

    await user.clear(nameInput)
    await user.type(nameInput, 'Platform Engineering')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(updateMutation).toHaveBeenCalledWith({
      id: 'dept-1',
      payload: {
        name: 'Platform Engineering',
        description: 'Builds internal systems.',
        parent_department_id: null,
      },
    })
    expect(toastSuccess).toHaveBeenCalledWith('Department updated.')
  })

  it('confirms and deactivates an active department', async () => {
    const user = userEvent.setup()
    const deactivateMutation = vi.fn().mockResolvedValue(undefined)
    useDeactivateDepartment.mockReturnValue({ mutateAsync: deactivateMutation })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Deactivate' }))

    expect(window.confirm).toHaveBeenCalledWith('Deactivate this department?')
    expect(deactivateMutation).toHaveBeenCalledWith('dept-1')
    expect(toastSuccess).toHaveBeenCalledWith('Department deactivated.')
  })
})
