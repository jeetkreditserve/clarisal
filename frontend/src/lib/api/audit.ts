import api from '@/lib/api'
import type { PaginatedResponse } from '@/types/organisation'
import type { AuditLogEntry } from '@/types/audit'

interface AuditLogParams {
  organisation_id?: string
  module?: string
  action?: string
  actor?: string
  target_type?: string
  search?: string
  date_from?: string
  date_to?: string
  page?: number
}

export async function fetchCtAuditLogs(params?: AuditLogParams | string) {
  const normalisedParams = typeof params === 'string' ? { organisation_id: params } : params
  const { data } = await api.get<PaginatedResponse<AuditLogEntry>>('/ct/audit/', {
    params: normalisedParams,
  })
  return data
}

export async function fetchOrgAuditLogs(params?: Omit<AuditLogParams, 'organisation_id'>) {
  const { data } = await api.get<PaginatedResponse<AuditLogEntry>>('/org/audit/', { params })
  return data
}
