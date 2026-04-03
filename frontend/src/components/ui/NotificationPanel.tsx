import type { NotificationRecord } from '@/lib/api/notifications'

interface NotificationPanelProps {
  notifications: NotificationRecord[]
  unreadCount: number
  isLoading: boolean
  isMarkingAll: boolean
  errorMessage?: string
  onMarkAllRead: () => void | Promise<void>
  onMarkRead: (notification: NotificationRecord) => void | Promise<void>
}

const timestampFormatter = new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function formatNotificationTimestamp(value: string) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return timestampFormatter.format(parsed)
}

export function NotificationPanel({
  notifications,
  unreadCount,
  isLoading,
  isMarkingAll,
  errorMessage,
  onMarkAllRead,
  onMarkRead,
}: NotificationPanelProps) {
  return (
    <div className="w-[min(24rem,calc(100vw-2rem))] rounded-[28px] border border-[hsl(var(--border)_/_0.82)] bg-[hsl(var(--surface-elevated)_/_0.98)] p-4 shadow-[0_30px_80px_rgba(15,23,42,0.18)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Inbox</p>
          <h2 className="mt-2 text-lg font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">Notifications</h2>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
          </p>
        </div>
        <button
          type="button"
          className="text-sm font-semibold text-[hsl(var(--brand))] disabled:cursor-not-allowed disabled:opacity-50"
          onClick={() => void onMarkAllRead()}
          disabled={isLoading || isMarkingAll || unreadCount === 0}
        >
          Mark all read
        </button>
      </div>

      {errorMessage ? (
        <div className="mt-4 rounded-[20px] border border-[hsl(var(--danger)_/_0.24)] bg-[hsl(var(--danger)_/_0.08)] px-4 py-3 text-sm text-[hsl(var(--foreground-strong))]">
          {errorMessage}
        </div>
      ) : null}

      <div className="mt-4 max-h-[24rem] space-y-3 overflow-y-auto pr-1">
        {isLoading ? (
          <div className="rounded-[22px] border border-dashed border-[hsl(var(--border)_/_0.7)] px-4 py-5 text-sm text-[hsl(var(--muted-foreground))]">
            Loading notifications…
          </div>
        ) : null}

        {!isLoading && notifications.length === 0 ? (
          <div className="rounded-[22px] border border-dashed border-[hsl(var(--border)_/_0.7)] px-4 py-5 text-sm text-[hsl(var(--muted-foreground))]">
            New approvals, payroll updates, and reminders will appear here.
          </div>
        ) : null}

        {!isLoading
          ? notifications.map((notification) => (
              <article
                key={notification.id}
                className={`rounded-[24px] border px-4 py-4 transition ${
                  notification.is_read
                    ? 'border-[hsl(var(--border)_/_0.74)] bg-[hsl(var(--surface)_/_0.86)]'
                    : 'border-[hsl(var(--brand)_/_0.28)] bg-[linear-gradient(180deg,hsl(var(--brand)_/_0.12),hsl(var(--surface)_/_0.96))]'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      {!notification.is_read ? <span className="h-2.5 w-2.5 rounded-full bg-[hsl(var(--brand))]" aria-hidden="true" /> : null}
                      <p className="truncate text-sm font-semibold text-[hsl(var(--foreground-strong))]">{notification.title}</p>
                    </div>
                    {notification.body ? (
                      <p className="mt-2 text-sm leading-6 text-[hsl(var(--muted-foreground))]">{notification.body}</p>
                    ) : null}
                  </div>
                  {!notification.is_read ? (
                    <button
                      type="button"
                      className="shrink-0 text-xs font-semibold text-[hsl(var(--brand))]"
                      onClick={() => void onMarkRead(notification)}
                    >
                      Mark read
                    </button>
                  ) : null}
                </div>
                <p className="mt-3 text-xs uppercase tracking-[0.18em] text-[hsl(var(--muted-foreground))]">
                  {formatNotificationTimestamp(notification.created_at)}
                </p>
              </article>
            ))
          : null}
      </div>
    </div>
  )
}
