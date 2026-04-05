import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NotificationBell } from '@/components/ui/NotificationBell'

const useNotifications = vi.fn()
const useMarkNotificationRead = vi.fn()
const useMarkAllNotificationsRead = vi.fn()

vi.mock('@/hooks/useNotifications', () => ({
  useNotifications: () => useNotifications(),
  useMarkNotificationRead: () => useMarkNotificationRead(),
  useMarkAllNotificationsRead: () => useMarkAllNotificationsRead(),
}))

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useNotifications.mockReturnValue({
      isLoading: false,
      data: {
        unread_count: 2,
        results: [
          {
            id: 'notif-1',
            kind: 'GENERAL',
            title: 'Draft payroll approved',
            body: 'Your payroll draft is approved.',
            is_read: false,
            read_at: null,
            created_at: '2026-04-03T10:00:00Z',
            object_id: 'obj-1',
          },
        ],
      },
    })
    useMarkNotificationRead.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useMarkAllNotificationsRead.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
  })

  it('shows unread badge and renders notifications inside the panel', async () => {
    const user = userEvent.setup()

    render(<NotificationBell />)

    expect(screen.getByText('2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Notifications' }))

    expect(screen.getByRole('heading', { name: 'Notifications' })).toBeInTheDocument()
    expect(screen.getByText('Draft payroll approved')).toBeInTheDocument()
  })

  it('marks all notifications as read from the panel', async () => {
    const user = userEvent.setup()
    const markAll = vi.fn().mockResolvedValue(undefined)
    useMarkAllNotificationsRead.mockReturnValue({ isPending: false, mutateAsync: markAll })

    render(<NotificationBell />)

    await user.click(screen.getByRole('button', { name: 'Notifications' }))
    await user.click(screen.getByRole('button', { name: 'Mark all read' }))

    await waitFor(() => {
      expect(markAll).toHaveBeenCalledTimes(1)
    })
  })
})
