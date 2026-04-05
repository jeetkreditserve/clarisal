import { useState } from 'react'
import * as Popover from '@radix-ui/react-popover'
import { Bell } from 'lucide-react'

import type { NotificationRecord } from '@/lib/api/notifications'
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications } from '@/hooks/useNotifications'
import { NotificationPanel } from '@/components/ui/NotificationPanel'

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const notificationsQuery = useNotifications()
  const markReadMutation = useMarkNotificationRead()
  const markAllMutation = useMarkAllNotificationsRead()

  const unreadCount = notificationsQuery.data?.unread_count ?? 0
  const notifications = notificationsQuery.data?.results ?? []

  const handleMarkRead = async (notification: NotificationRecord) => {
    if (notification.is_read || markReadMutation.isPending) {
      return
    }
    await markReadMutation.mutateAsync(notification.id)
  }

  const handleMarkAllRead = async () => {
    if (unreadCount === 0 || markAllMutation.isPending) {
      return
    }
    await markAllMutation.mutateAsync()
  }

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="relative inline-flex h-11 w-11 items-center justify-center rounded-[18px] border border-[hsl(var(--border)_/_0.82)] bg-[hsl(var(--surface)_/_0.82)] text-[hsl(var(--foreground-strong))] transition hover:-translate-y-0.5 hover:bg-[hsl(var(--surface-elevated)_/_0.96)]"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 ? (
            <span className="absolute -right-1 -top-1 inline-flex min-w-[1.35rem] items-center justify-center rounded-full bg-[hsl(var(--brand))] px-1.5 py-0.5 text-[10px] font-bold text-[hsl(var(--brand-foreground))]">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          ) : null}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={12}
          className="z-50 outline-none"
        >
          <NotificationPanel
            notifications={notifications}
            unreadCount={unreadCount}
            isLoading={notificationsQuery.isLoading}
            isMarkingAll={markAllMutation.isPending}
            errorMessage={notificationsQuery.error instanceof Error ? notificationsQuery.error.message : undefined}
            onMarkAllRead={handleMarkAllRead}
            onMarkRead={handleMarkRead}
          />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
