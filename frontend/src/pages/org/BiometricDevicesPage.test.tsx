import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BiometricDevicesPage } from '@/pages/org/BiometricDevicesPage'

const {
  toastSuccess,
  toastError,
  getBiometricDevices,
  createBiometricDevice,
  deleteBiometricDevice,
  getDeviceSyncLogs,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  getBiometricDevices: vi.fn(),
  createBiometricDevice: vi.fn(),
  deleteBiometricDevice: vi.fn(),
  getDeviceSyncLogs: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: toastSuccess,
    error: toastError,
  },
}))

vi.mock('@/lib/api/org-admin', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/org-admin')>('@/lib/api/org-admin')
  return {
    ...actual,
    getBiometricDevices,
    createBiometricDevice,
    deleteBiometricDevice,
    getDeviceSyncLogs,
  }
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BiometricDevicesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('BiometricDevicesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getBiometricDevices.mockResolvedValue([])
    getDeviceSyncLogs.mockResolvedValue([])
    createBiometricDevice.mockResolvedValue({
      id: 'device-1',
      name: 'HQ Main Gate',
      device_serial: 'SN-ADMS-001',
      protocol: 'ZK_ADMS',
      ip_address: null,
      port: 80,
      auth_username: '',
      oauth_client_id: '',
      location_id: null,
      is_active: true,
      last_sync_at: null,
      created_at: '2026-04-03T10:00:00Z',
    })
    deleteBiometricDevice.mockResolvedValue(undefined)
  })

  it('submits a new device registration', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('No biometric devices configured')
    await user.type(screen.getByLabelText('Device name'), 'HQ Main Gate')
    await user.type(screen.getByLabelText('Device serial'), 'SN-ADMS-001')
    await user.click(screen.getByRole('button', { name: 'Add device' }))

    await waitFor(() => {
      expect(createBiometricDevice).toHaveBeenCalled()
    })
    expect(createBiometricDevice.mock.calls[0][0]).toEqual({
        name: 'HQ Main Gate',
        device_serial: 'SN-ADMS-001',
        protocol: 'ZK_ADMS',
        ip_address: undefined,
        port: 80,
        auth_username: undefined,
        api_key: undefined,
        oauth_client_id: undefined,
        oauth_client_secret: undefined,
        is_active: true,
    })
    expect(toastSuccess).toHaveBeenCalled()
  })

  it('loads sync logs for the selected device', async () => {
    const user = userEvent.setup()
    getBiometricDevices.mockResolvedValue([
      {
        id: 'device-1',
        name: 'HQ Main Gate',
        device_serial: 'SN-ADMS-001',
        protocol: 'ZK_ADMS',
        ip_address: null,
        port: 80,
        auth_username: '',
        oauth_client_id: '',
        location_id: null,
        is_active: true,
        last_sync_at: '2026-04-03T10:00:00Z',
        created_at: '2026-04-03T09:00:00Z',
      },
    ])
    getDeviceSyncLogs.mockResolvedValue([
      {
        id: 'log-1',
        synced_at: '2026-04-03T10:05:00Z',
        records_fetched: 3,
        records_processed: 2,
        records_skipped: 1,
        errors: [],
        success: true,
      },
    ])

    renderPage()

    await screen.findByText('HQ Main Gate')
    await user.click(screen.getByRole('button', { name: 'Logs' }))

    await waitFor(() => {
      expect(getDeviceSyncLogs).toHaveBeenCalledWith('device-1')
    })
    expect(screen.getByText('Sync logs • HQ Main Gate')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('submits eSSL eBioserver devices as webhook-based integrations', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('No biometric devices configured')
    await user.type(screen.getByLabelText('Device name'), 'eSSL Web API')
    await user.selectOptions(screen.getByLabelText('Protocol'), 'ESSL_EBIOSERVER')
    await user.type(screen.getByLabelText('Shared secret'), 'shared-secret')
    await user.click(screen.getByRole('button', { name: 'Add device' }))

    await waitFor(() => {
      expect(createBiometricDevice).toHaveBeenCalled()
    })
    expect(createBiometricDevice.mock.calls[createBiometricDevice.mock.calls.length - 1]?.[0]).toEqual({
      name: 'eSSL Web API',
      device_serial: undefined,
      protocol: 'ESSL_EBIOSERVER',
      ip_address: undefined,
      port: 80,
      auth_username: undefined,
      api_key: 'shared-secret',
      oauth_client_id: undefined,
      oauth_client_secret: undefined,
      is_active: true,
    })
  })
})
