import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LiveAttendanceFeed } from '@/components/ui/LiveAttendanceFeed'

const { checkDeviceHealth } = vi.hoisted(() => ({
  checkDeviceHealth: vi.fn(),
}))

vi.mock('@/lib/api/org-admin', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/org-admin')>('@/lib/api/org-admin')
  return {
    ...actual,
    checkDeviceHealth,
  }
})

class EventSourceMock {
  static instances: EventSourceMock[] = []

  readonly url: string
  private readonly listeners = new Map<string, Array<(event: MessageEvent) => void>>()
  close = vi.fn()

  constructor(url: string) {
    this.url = url
    EventSourceMock.instances.push(this)
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    const existing = this.listeners.get(type) ?? []
    existing.push(listener)
    this.listeners.set(type, existing)
  }

  dispatch(type: string, data: unknown = {}) {
    const event = { data: JSON.stringify(data) } as MessageEvent
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event)
    }
  }
}

function renderFeed(deviceId = 'device-1') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <LiveAttendanceFeed deviceId={deviceId} />
    </QueryClientProvider>,
  )
}

describe('LiveAttendanceFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    EventSourceMock.instances = []
    checkDeviceHealth.mockResolvedValue({
      id: 'device-1',
      name: 'HQ Main Gate',
      vendor: 'ZKTECO',
      product_family: 'SpeedFace',
      health_status: 'HEALTHY',
      last_sync_at: '2026-04-07T12:00:00Z',
      last_health_check_at: '2026-04-07T12:00:10Z',
      is_active: true,
    })
    vi.stubGlobal('EventSource', EventSourceMock)
  })

  it('uses the API SSE endpoint and renders wrapped device events', async () => {
    renderFeed()

    await waitFor(() => {
      expect(checkDeviceHealth).toHaveBeenCalledWith('device-1')
    })
    expect(EventSourceMock.instances[0]?.url).toBe('/api/v1/org/biometrics/devices/device-1/events/')

    EventSourceMock.instances[0]?.dispatch('connected')
    EventSourceMock.instances[0]?.dispatch('device_health_update', {
      type: 'device_health_update',
      organisation_id: 'org-1',
      timestamp: '2026-04-07T12:01:00Z',
      payload: {
        device_id: 'device-1',
        device_name: 'HQ Main Gate',
        health_status: 'FAILED',
        last_sync_at: '2026-04-07T12:00:00Z',
        error_message: 'Connection timed out',
      },
    })

    expect(await screen.findByText('HQ Main Gate: Connection timed out')).toBeInTheDocument()
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })
})
