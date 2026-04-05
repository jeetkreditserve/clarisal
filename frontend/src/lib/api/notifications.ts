import api from '@/lib/api'

export interface NotificationRecord {
  id: string
  kind: string
  title: string
  body: string
  is_read: boolean
  read_at: string | null
  created_at: string
  object_id: string | null
}

export interface NotificationListResponse {
  unread_count: number
  results: NotificationRecord[]
}

export async function getMyNotifications() {
  const { data } = await api.get<NotificationListResponse>('/me/notifications/')
  return data
}

export async function markNotificationRead(id: string) {
  const { data } = await api.patch<NotificationRecord>(`/me/notifications/${id}/read/`)
  return data
}

export async function markAllNotificationsRead() {
  const { data } = await api.post<{ marked_read: number }>('/me/notifications/mark-all-read/')
  return data
}
