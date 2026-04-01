import api from '@/lib/api'
import type { PaginatedResponse } from '@/types/organisation'
import type { AuditLogEntry } from '@/types/audit'

export async function fetchCtAuditLogs(organisationId?: string) {
  const { data } = await api.get<PaginatedResponse<AuditLogEntry>>('/ct/audit/', {
    params: organisationId ? { organisation_id: organisationId } : undefined,
  })
  return data
}

export async function fetchOrgAuditLogs() {
  const { data } = await api.get<PaginatedResponse<AuditLogEntry>>('/org/audit/')
  return data
}
