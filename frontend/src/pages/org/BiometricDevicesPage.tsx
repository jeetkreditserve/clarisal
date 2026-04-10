import { useMemo, useState } from 'react'
import { Activity, Fingerprint, Network, RefreshCw, ShieldCheck } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { LiveAttendanceFeed } from '@/components/ui/LiveAttendanceFeed'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { getDeviceSyncLogs, getBiometricDevices, createBiometricDevice, deleteBiometricDevice } from '@/lib/api/org-admin'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'
import type { BiometricProtocol } from '@/types/hr'

const PROTOCOL_OPTIONS: Array<{ value: BiometricProtocol; label: string; note: string; vendor: string }> = [
  { value: 'ZK_ADMS', label: 'ZKTeco / eSSL ADMS', note: 'Push-based devices that post ATTLOG entries directly to Clarisal.', vendor: 'ZKTeco / eSSL' },
  { value: 'ESSL_EBIOSERVER', label: 'eSSL eBioserver', note: 'Webhook-based eSSL middleware integration secured with a shared secret.', vendor: 'eSSL' },
  { value: 'MATRIX_COSEC', label: 'Matrix COSEC', note: 'Pull-based sync using the device API key and a 5-minute poll interval.', vendor: 'Matrix COSEC' },
  { value: 'SUPREMA_BIOSTAR', label: 'Suprema BioStar 2', note: 'Pull-based sync using BioStar login credentials over HTTPS.', vendor: 'Suprema' },
  { value: 'HIKVISION_ISAPI', label: 'HikVision ISAPI', note: 'Pull-based sync using digest-auth credentials.', vendor: 'HikVision' },
  { value: 'MANTRA_AEBAS', label: 'Mantra / AEBAS', note: 'Mantra biometric devices linked to AEBAS government attendance system.', vendor: 'Mantra' },
  { value: 'CP_PLUS_EXPORT', label: 'CP PLUS Export', note: 'CP PLUS attendance devices with export-based integration.', vendor: 'CP PLUS' },
]

const PROTOCOL_LABELS: Record<BiometricProtocol, string> = {
  ZK_ADMS: 'ZKTeco / eSSL ADMS',
  ESSL_EBIOSERVER: 'eSSL eBioserver',
  MATRIX_COSEC: 'Matrix COSEC',
  SUPREMA_BIOSTAR: 'Suprema BioStar 2',
  HIKVISION_ISAPI: 'HikVision ISAPI',
  MANTRA_AEBAS: 'Mantra / AEBAS',
  CP_PLUS_EXPORT: 'CP PLUS Export',
}

const VENDOR_LABELS: Record<string, string> = {
  ZKTECO: 'ZKTeco',
  ESSL: 'eSSL',
  MATRIX: 'Matrix COSEC',
  HIKVISION: 'HikVision',
  SUPREMA: 'Suprema',
  MANTRA: 'Mantra',
  CP_PLUS: 'CP PLUS',
  OTHER: 'Other',
}

const HEALTH_STATUS_LABELS: Record<string, { label: string; tone: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  HEALTHY: { label: 'Healthy', tone: 'success' },
  DEGRADED: { label: 'Degraded', tone: 'warning' },
  FAILED: { label: 'Failed', tone: 'danger' },
  UNKNOWN: { label: 'Unknown', tone: 'neutral' },
}

const INITIAL_FORM = {
  name: '',
  device_serial: '',
  protocol: 'ZK_ADMS' as BiometricProtocol,
  vendor: '',
  product_family: '',
  ip_address: '',
  port: '80',
  auth_username: '',
  api_key: '',
  oauth_client_id: '',
  oauth_client_secret: '',
}

function isPullProtocol(protocol: BiometricProtocol) {
  return ['MATRIX_COSEC', 'SUPREMA_BIOSTAR', 'HIKVISION_ISAPI'].includes(protocol)
}

function isWebhookProtocol(protocol: BiometricProtocol) {
  return ['ZK_ADMS', 'ESSL_EBIOSERVER'].includes(protocol)
}

function buildPayload(form: typeof INITIAL_FORM) {
  const selectedProtocol = PROTOCOL_OPTIONS.find((p) => p.value === form.protocol)
  return {
    name: form.name.trim(),
    device_serial: form.device_serial.trim() || undefined,
    protocol: form.protocol,
    vendor: selectedProtocol?.vendor || '',
    product_family: form.product_family.trim() || undefined,
    ip_address: isPullProtocol(form.protocol) ? form.ip_address.trim() || undefined : undefined,
    port: isPullProtocol(form.protocol) ? Number(form.port || '80') : 80,
    auth_username: form.protocol === 'HIKVISION_ISAPI' ? form.auth_username.trim() || undefined : undefined,
    api_key:
      form.protocol === 'MATRIX_COSEC' || form.protocol === 'HIKVISION_ISAPI' || form.protocol === 'ESSL_EBIOSERVER'
        ? form.api_key.trim() || undefined
        : undefined,
    oauth_client_id: form.protocol === 'SUPREMA_BIOSTAR' ? form.oauth_client_id.trim() || undefined : undefined,
    oauth_client_secret: form.protocol === 'SUPREMA_BIOSTAR' ? form.oauth_client_secret.trim() || undefined : undefined,
    is_active: true,
  }
}

export function BiometricDevicesPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(INITIAL_FORM)
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)

  const devicesQuery = useQuery({
    queryKey: ['org', 'biometric-devices'],
    queryFn: getBiometricDevices,
  })

  const selectedDevice = useMemo(
    () => devicesQuery.data?.find((device) => device.id === selectedDeviceId) ?? null,
    [devicesQuery.data, selectedDeviceId],
  )

  const syncLogsQuery = useQuery({
    queryKey: ['org', 'biometric-devices', 'logs', selectedDeviceId],
    queryFn: () => getDeviceSyncLogs(selectedDeviceId!),
    enabled: !!selectedDeviceId,
  })

  const createMutation = useMutation({
    mutationFn: createBiometricDevice,
    onSuccess: (device) => {
      toast.success(device.endpoint_path ? `${device.name} added. Webhook endpoint is ready.` : `${device.name} added to biometric sync.`)
      setForm(INITIAL_FORM)
      setSelectedDeviceId(device.id)
      void queryClient.invalidateQueries({ queryKey: ['org', 'biometric-devices'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to register the biometric device.'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteBiometricDevice,
    onSuccess: () => {
      toast.success('Device deactivated.')
      setSelectedDeviceId((current) => {
        if (!current) return current
        return devicesQuery.data?.some((device) => device.id === current && device.is_active) ? current : null
      })
      void queryClient.invalidateQueries({ queryKey: ['org', 'biometric-devices'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to deactivate the biometric device.'))
    },
  })

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void createMutation.mutateAsync(buildPayload(form))
  }

  const activeCount = devicesQuery.data?.filter((device) => device.is_active).length ?? 0
  const selectedProtocol = PROTOCOL_OPTIONS.find((option) => option.value === form.protocol)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Attendance Devices"
        title="Biometric Devices"
        description="Register push or pull biometric endpoints so raw punches land in the same attendance engine as web punch and spreadsheet imports."
        actions={<StatusBadge tone="info">{activeCount} active</StatusBadge>}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)]">
        <SectionCard title="Register device" description="Store the device connection details and the credentials needed for recurring sync.">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="biometric-name">Device name</label>
                <input
                  id="biometric-name"
                  className="field-input"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="HQ Main Gate"
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="biometric-protocol">Protocol</label>
                <select
                  id="biometric-protocol"
                  className="field-input"
                  value={form.protocol}
                  onChange={(event) => setForm((current) => ({ ...current, protocol: event.target.value as BiometricProtocol }))}
                >
                  {PROTOCOL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <p className="rounded-[18px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              {selectedProtocol?.note}
            </p>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="biometric-serial">Device serial</label>
                <input
                  id="biometric-serial"
                  className="field-input"
                  value={form.device_serial}
                  onChange={(event) => setForm((current) => ({ ...current, device_serial: event.target.value }))}
                  placeholder={form.protocol === 'ZK_ADMS' ? 'Required for ADMS push' : form.protocol === 'ESSL_EBIOSERVER' ? 'Optional eSSL reference' : 'Optional reference'}
                  required={form.protocol === 'ZK_ADMS'}
                />
              </div>
              {isPullProtocol(form.protocol) ? (
                <div>
                  <label className="field-label" htmlFor="biometric-ip">Device IP</label>
                  <input
                    id="biometric-ip"
                    className="field-input"
                    value={form.ip_address}
                    onChange={(event) => setForm((current) => ({ ...current, ip_address: event.target.value }))}
                    placeholder="192.168.1.100"
                    required
                  />
                </div>
              ) : null}
            </div>

            {isPullProtocol(form.protocol) ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="field-label" htmlFor="biometric-port">Port</label>
                  <input
                    id="biometric-port"
                    className="field-input"
                    type="number"
                    min="1"
                    max="65535"
                    value={form.port}
                    onChange={(event) => setForm((current) => ({ ...current, port: event.target.value }))}
                    required
                  />
                </div>
                {form.protocol === 'HIKVISION_ISAPI' ? (
                  <div>
                    <label className="field-label" htmlFor="biometric-username">Username</label>
                    <input
                      id="biometric-username"
                      className="field-input"
                      value={form.auth_username}
                      onChange={(event) => setForm((current) => ({ ...current, auth_username: event.target.value }))}
                      placeholder="admin"
                      required
                    />
                  </div>
                ) : null}
              </div>
            ) : null}

            {form.protocol === 'MATRIX_COSEC' || form.protocol === 'HIKVISION_ISAPI' || form.protocol === 'ESSL_EBIOSERVER' ? (
              <div>
                <label className="field-label" htmlFor="biometric-api-key">
                  {form.protocol === 'MATRIX_COSEC' ? 'API key' : form.protocol === 'ESSL_EBIOSERVER' ? 'Shared secret' : 'Password'}
                </label>
                <input
                  id="biometric-api-key"
                  className="field-input"
                  type="password"
                  value={form.api_key}
                  onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))}
                  placeholder={form.protocol === 'MATRIX_COSEC' ? 'Paste the device API key' : form.protocol === 'ESSL_EBIOSERVER' ? 'Webhook shared secret' : 'Digest auth password'}
                  required
                />
              </div>
            ) : null}

            {form.protocol === 'SUPREMA_BIOSTAR' ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="field-label" htmlFor="biometric-login-id">Login ID</label>
                  <input
                    id="biometric-login-id"
                    className="field-input"
                    value={form.oauth_client_id}
                    onChange={(event) => setForm((current) => ({ ...current, oauth_client_id: event.target.value }))}
                    placeholder="api-user"
                    required
                  />
                </div>
                <div>
                  <label className="field-label" htmlFor="biometric-login-secret">Password</label>
                  <input
                    id="biometric-login-secret"
                    className="field-input"
                    type="password"
                    value={form.oauth_client_secret}
                    onChange={(event) => setForm((current) => ({ ...current, oauth_client_secret: event.target.value }))}
                    placeholder="BioStar password"
                    required
                  />
                </div>
              </div>
            ) : null}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[hsl(var(--border))] pt-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Pull protocols sync every 5 minutes. ADMS devices push attendance in real time to the endpoint shown after setup.
              </p>
              <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Saving...' : 'Add device'}
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard title="Protocol checklist" description="Use the integration requirements below when handing setup details to the implementation team or the vendor.">
          <div className="space-y-3 text-sm text-[hsl(var(--muted-foreground))]">
            <div className="rounded-[20px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
              <div className="flex items-center gap-2 font-medium text-[hsl(var(--foreground-strong))]">
                <Fingerprint className="h-4 w-4" />
                ZK ADMS
              </div>
              <p className="mt-2">Configure the device to push `ATTLOG` rows to `/api/v1/biometric/adms/iclock/cdata?SN=&lt;serial&gt;`.</p>
            </div>
            <div className="rounded-[20px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
              <div className="flex items-center gap-2 font-medium text-[hsl(var(--foreground-strong))]">
                <Fingerprint className="h-4 w-4" />
                eSSL eBioserver
              </div>
              <p className="mt-2">Use this when the installation sits behind eSSL/CAMS middleware and can POST real-time punch events to a webhook secured with a shared secret.</p>
            </div>
            <div className="rounded-[20px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
              <div className="flex items-center gap-2 font-medium text-[hsl(var(--foreground-strong))]">
                <Network className="h-4 w-4" />
                Pull sync
              </div>
              <p className="mt-2">Matrix, Suprema, and HikVision devices are polled every 5 minutes and deduplicated within a one-minute punch window.</p>
            </div>
            <div className="rounded-[20px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
              <div className="flex items-center gap-2 font-medium text-[hsl(var(--foreground-strong))]">
                <ShieldCheck className="h-4 w-4" />
                Credential handling
              </div>
              <p className="mt-2">Secrets are stored encrypted server-side. The page only accepts fresh values when you register or rotate a device.</p>
            </div>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Configured devices" description="Review sync status, inspect recent logs, and deactivate integrations that should stop feeding attendance punches.">
        {devicesQuery.isLoading ? (
          <SkeletonTable rows={4} />
        ) : !devicesQuery.data?.length ? (
          <EmptyState
            icon={Activity}
            title="No biometric devices configured"
            description="Register the first device to bring biometric attendance into the organisation workspace."
          />
        ) : (
            <div className="table-shell overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-[hsl(var(--muted-foreground))]">
                  <tr className="border-b border-[hsl(var(--border))]">
                    <th className="px-4 py-3 font-medium">Device</th>
                    <th className="px-4 py-3 font-medium">Protocol</th>
                    <th className="px-4 py-3 font-medium">Vendor</th>
                    <th className="px-4 py-3 font-medium">Serial / IP</th>
                    <th className="px-4 py-3 font-medium">Last sync</th>
                    <th className="px-4 py-3 font-medium">Health</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {devicesQuery.data.map((device) => (
                    <tr key={device.id} className="border-b border-[hsl(var(--border))] last:border-b-0">
                      <td className="px-4 py-4">
                        <div className="font-medium text-[hsl(var(--foreground-strong))]">{device.name}</div>
                        {device.auth_username ? <div className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">User: {device.auth_username}</div> : null}
                        {device.endpoint_path ? <div className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">Endpoint: {device.endpoint_path}</div> : null}
                        {device.secret_preview ? <div className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">Secret: {device.secret_preview}</div> : null}
                      </td>
                      <td className="px-4 py-4 text-[hsl(var(--muted-foreground))]">{PROTOCOL_LABELS[device.protocol]}</td>
                      <td className="px-4 py-4 text-[hsl(var(--muted-foreground))]">
                        {device.vendor ? VENDOR_LABELS[device.vendor] || device.vendor : '-'}
                        {device.product_family ? <div className="text-xs">{device.product_family}</div> : null}
                      </td>
                      <td className="px-4 py-4 text-[hsl(var(--muted-foreground))]">{device.device_serial || device.ip_address || 'Not set'}</td>
                      <td className="px-4 py-4 text-[hsl(var(--muted-foreground))]">
                        {device.last_sync_at ? formatDateTime(device.last_sync_at) : 'Never'}
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge tone={HEALTH_STATUS_LABELS[device.health_status]?.tone || 'neutral'}>
                          {HEALTH_STATUS_LABELS[device.health_status]?.label || 'Unknown'}
                        </StatusBadge>
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge tone={device.is_active ? 'success' : 'neutral'}>
                          {device.is_active ? 'Active' : 'Inactive'}
                        </StatusBadge>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => setSelectedDeviceId(device.id)}
                          >
                            Logs
                          </button>
                          <ConfirmDialog
                            trigger={<button type="button" className="btn-secondary">Deactivate</button>}
                            title={`Deactivate ${device.name}?`}
                            description="The device will stop syncing new attendance punches, but the existing punch history will stay intact."
                            confirmLabel="Deactivate"
                            onConfirm={() => deleteMutation.mutateAsync(device.id)}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
        )}
      </SectionCard>

      {selectedDevice ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard
            title={`Sync logs • ${selectedDevice.name}`}
            description="Recent sync attempts for the selected device. Errors are preserved so vendor-side issues are easy to trace."
          >
            {syncLogsQuery.isLoading ? (
              <SkeletonTable rows={3} />
            ) : !syncLogsQuery.data?.length ? (
              <EmptyState
                icon={RefreshCw}
                title="No sync logs yet"
                description={isWebhookProtocol(selectedDevice.protocol) ? 'The device is registered. Logs will appear after the first webhook delivery.' : 'The device is registered. Logs will appear after the first push or scheduled pull cycle.'}
              />
            ) : (
              <div className="table-shell overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-[hsl(var(--muted-foreground))]">
                    <tr className="border-b border-[hsl(var(--border))]">
                      <th className="px-4 py-3 font-medium">Synced at</th>
                      <th className="px-4 py-3 font-medium">Fetched</th>
                      <th className="px-4 py-3 font-medium">Processed</th>
                      <th className="px-4 py-3 font-medium">Skipped</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncLogsQuery.data.map((log) => (
                      <tr key={log.id} className="border-b border-[hsl(var(--border))] last:border-b-0">
                        <td className="px-4 py-4 text-[hsl(var(--muted-foreground))]">{formatDateTime(log.synced_at)}</td>
                        <td className="px-4 py-4 text-[hsl(var(--foreground-strong))]">{log.records_fetched}</td>
                        <td className="px-4 py-4 text-[hsl(var(--foreground-strong))]">{log.records_processed}</td>
                        <td className="px-4 py-4 text-[hsl(var(--foreground-strong))]">{log.records_skipped}</td>
                        <td className="px-4 py-4">
                          <StatusBadge tone={log.success ? 'success' : 'danger'}>
                            {log.success ? 'OK' : 'Failed'}
                          </StatusBadge>
                          {!log.success && log.errors.length ? (
                            <p className="mt-2 max-w-xl text-xs leading-6 text-[hsl(var(--danger))]">{log.errors.join(' | ')}</p>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Live Feed"
            description="Real-time events from this device. Requires Redis and SSE support."
          >
            <LiveAttendanceFeed deviceId={selectedDevice.id} />
          </SectionCard>
        </div>
      ) : null}
    </div>
  )
}

export default BiometricDevicesPage
