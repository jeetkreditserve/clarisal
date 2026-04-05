import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/hooks/useAuth'
import { getMyNotifications, markAllNotificationsRead, markNotificationRead } from '@/lib/api/notifications'

function useNotificationScope() {
  const { user } = useAuth()
  return user
}

export function useNotifications() {
  const user = useNotificationScope()

  return useQuery({
    queryKey: ['notifications', user?.id],
    queryFn: getMyNotifications,
    enabled: user?.account_type === 'WORKFORCE',
    refetchInterval: 30_000,
    staleTime: 25_000,
  })
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}
