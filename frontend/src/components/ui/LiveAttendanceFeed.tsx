import { useEffect, useRef, useState } from 'react'
import { Wifi, WifiOff } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

import { StatusBadge } from '@/components/ui/StatusBadge'
import { checkDeviceHealth } from '@/lib/api/org-admin'
import { formatDateTime } from '@/lib/format'

interface PunchEvent {
  type: string
  punch_id: string
  employee_code: string
  direction: 'IN' | 'OUT'
  punch_time: string
  device_id: string
  source: string
}

interface DeviceHealthEvent {
  type: string
  device_id: string
  device_name: string
  health_status: string
  last_sync_at: string | null
  error_message?: string
}

interface SyncEvent {
  type: string
  device_id: string
  device_name: string
  records_processed: number
  records_skipped: number
  success: boolean
  errors: string[]
}

interface StreamEnvelope<TPayload> {
  type: string
  organisation_id: string
  timestamp: string
  payload: TPayload
}

interface LiveAttendanceFeedProps {
  organisationId?: string
  deviceId?: string
  onPunch?: (event: PunchEvent) => void
  onDeviceHealth?: (event: DeviceHealthEvent) => void
}

export function LiveAttendanceFeed({ organisationId, deviceId, onPunch, onDeviceHealth }: LiveAttendanceFeedProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [events, setEvents] = useState<Array<PunchEvent | DeviceHealthEvent | SyncEvent>>([])
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const healthQuery = useQuery({
    queryKey: ['org', 'biometric-devices', deviceId, 'health'],
    queryFn: () => checkDeviceHealth(deviceId!),
    enabled: !!deviceId,
    refetchInterval: 30000,
  })

  useEffect(() => {
    if (!organisationId && !deviceId) return

    const endpoint = deviceId
      ? `/api/org/biometrics/devices/${deviceId}/events/`
      : '/api/org/biometrics/events/'

    let isClosed = false

    const pushEvent = (nextEvent: PunchEvent | DeviceHealthEvent | SyncEvent) => {
      setEvents((prev) => [nextEvent, ...prev].slice(0, 50))
    }

    const parseEnvelope = <TPayload,>(raw: string): StreamEnvelope<TPayload> | null => {
      try {
        return JSON.parse(raw) as StreamEnvelope<TPayload>
      } catch {
        return null
      }
    }

    const connect = () => {
      const eventSource = new EventSource(endpoint)
      eventSourceRef.current = eventSource

      eventSource.addEventListener('connected', () => {
        setIsConnected(true)
      })

      eventSource.addEventListener('punch_created', (e) => {
        const envelope = parseEnvelope<Omit<PunchEvent, 'type'>>(e.data)
        if (!envelope) return
        const data: PunchEvent = {
          type: envelope.type,
          ...envelope.payload,
        }
        pushEvent(data)
        onPunch?.(data)
      })

      eventSource.addEventListener('device_health_update', (e) => {
        const envelope = parseEnvelope<Omit<DeviceHealthEvent, 'type'>>(e.data)
        if (!envelope) return
        const data: DeviceHealthEvent = {
          type: envelope.type,
          ...envelope.payload,
        }
        pushEvent(data)
        onDeviceHealth?.(data)
      })

      eventSource.addEventListener('device_sync_complete', (e) => {
        const envelope = parseEnvelope<Omit<SyncEvent, 'type'>>(e.data)
        if (!envelope) return
        const data: SyncEvent = {
          type: envelope.type,
          ...envelope.payload,
        }
        pushEvent(data)
      })

      eventSource.addEventListener('error', () => {
        setIsConnected(false)
        eventSource.close()
        if (isClosed) return
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, 5000)
      })
    }

    connect()

    return () => {
      isClosed = true
      eventSourceRef.current?.close()
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [organisationId, deviceId, onPunch, onDeviceHealth])

  const getEventIcon = (event: PunchEvent | DeviceHealthEvent | SyncEvent) => {
    if ('punch_id' in event) {
      return event.direction === 'IN' ? '→' : '←'
    }
    if ('records_processed' in event) {
      return event.success ? '✓' : '!'
    }
    return '●'
  }

  const getEventColor = (event: PunchEvent | DeviceHealthEvent | SyncEvent) => {
    if ('punch_id' in event) {
      return event.direction === 'IN' ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--warning))]'
    }
    if ('records_processed' in event) {
      return event.success ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--danger))]'
    }
    if (event.health_status === 'HEALTHY') return 'text-[hsl(var(--success))]'
    if (event.health_status === 'FAILED') return 'text-[hsl(var(--danger))]'
    return 'text-[hsl(var(--muted-foreground))]'
  }

  const formatEventMessage = (event: PunchEvent | DeviceHealthEvent | SyncEvent) => {
    if ('punch_id' in event) {
      return `${event.employee_code} ${event.direction} at ${formatDateTime(event.punch_time)}`
    }
    if ('records_processed' in event) {
      return `${event.device_name}: ${event.records_processed} processed, ${event.records_skipped} skipped`
    }
    if (event.error_message) {
      return `${event.device_name}: ${event.error_message}`
    }
    return `${event.device_name} is ${event.health_status}`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Live Events</h3>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-[hsl(var(--success))]" />
              <StatusBadge tone="success" className="text-xs">Connected</StatusBadge>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
              <StatusBadge tone="neutral" className="text-xs">Disconnected</StatusBadge>
            </>
          )}
        </div>
      </div>

      {healthQuery.data && (
        <div className="rounded-[18px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))] p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[hsl(var(--muted-foreground))]">Device Health:</span>
            <StatusBadge
              tone={
                healthQuery.data.health_status === 'HEALTHY'
                  ? 'success'
                  : healthQuery.data.health_status === 'FAILED'
                    ? 'danger'
                    : healthQuery.data.health_status === 'DEGRADED'
                      ? 'warning'
                      : 'neutral'
              }
            >
              {healthQuery.data.health_status}
            </StatusBadge>
          </div>
          {healthQuery.data.last_sync_at && (
            <div className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              Last sync: {formatDateTime(healthQuery.data.last_sync_at)}
            </div>
          )}
        </div>
      )}

      <div className="max-h-64 space-y-2 overflow-y-auto">
        {events.length === 0 ? (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Waiting for events...</p>
        ) : (
          events.map((event, index) => (
            <div
              key={`${'punch_id' in event ? event.punch_id : event.device_id}-${index}`}
              className="flex items-start gap-2 text-sm"
            >
              <span className={`mt-0.5 font-mono ${getEventColor(event)}`}>
                {getEventIcon(event)}
              </span>
              <span className="text-[hsl(var(--foreground))]">{formatEventMessage(event)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default LiveAttendanceFeed
