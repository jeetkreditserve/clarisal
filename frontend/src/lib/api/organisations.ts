import api from '@/lib/api'
import type {
  CtDashboardStats,
  OrgAdmin,
  OrganisationDetail,
  OrganisationListItem,
  PaginatedResponse,
} from '@/types/organisation'

export async function fetchCtStats(): Promise<CtDashboardStats> {
  const { data } = await api.get('/ct/dashboard/')
  return data
}

export async function fetchOrganisations(params?: {
  search?: string
  status?: string
  page?: number
}): Promise<PaginatedResponse<OrganisationListItem>> {
  const { data } = await api.get('/ct/organisations/', { params })
  return data
}

export async function fetchOrganisation(id: string): Promise<OrganisationDetail> {
  const { data } = await api.get(`/ct/organisations/${id}/`)
  return data
}

export async function createOrganisation(payload: {
  name: string
  licence_count: number
  address?: string
  phone?: string
  email?: string
  country_code?: string
  currency?: string
}): Promise<OrganisationDetail> {
  const { data } = await api.post('/ct/organisations/', payload)
  return data
}

export async function updateOrganisation(id: string, payload: {
  name?: string
  address?: string
  phone?: string
  email?: string
  country_code?: string
  currency?: string
}): Promise<OrganisationDetail> {
  const { data } = await api.patch(`/ct/organisations/${id}/`, payload)
  return data
}

export async function markOrganisationPaid(id: string, note?: string): Promise<OrganisationDetail> {
  const { data } = await api.post(`/ct/organisations/${id}/activate/`, { note: note ?? '' })
  return data
}

export async function suspendOrganisation(id: string, note?: string): Promise<OrganisationDetail> {
  const { data } = await api.post(`/ct/organisations/${id}/suspend/`, { note: note ?? '' })
  return data
}

export async function restoreOrganisation(id: string, note?: string): Promise<OrganisationDetail> {
  const { data } = await api.post(`/ct/organisations/${id}/restore/`, { note: note ?? '' })
  return data
}

export async function fetchOrgLicences(id: string): Promise<{
  total_count: number
  used_count: number
  available_count: number
  utilisation_percent: number
}> {
  const { data } = await api.get(`/ct/organisations/${id}/licences/`)
  return data
}

export async function updateOrgLicences(id: string, licence_count: number, note = ''): Promise<{
  total_count: number
  used_count: number
  available_count: number
  utilisation_percent: number
}> {
  const { data } = await api.patch(`/ct/organisations/${id}/licences/`, { licence_count, note })
  return data
}

export async function fetchOrgAdmins(id: string): Promise<OrgAdmin[]> {
  const { data } = await api.get(`/ct/organisations/${id}/admins/`)
  return data
}

export async function inviteOrgAdmin(id: string, payload: {
  email: string
  first_name: string
  last_name: string
}): Promise<{ user_id: string; email: string; status: string; expires_at: string }> {
  const { data } = await api.post(`/ct/organisations/${id}/admins/invite/`, payload)
  return data
}

export async function resendOrgAdminInvite(orgId: string, userId: string): Promise<void> {
  await api.post(`/ct/organisations/${orgId}/admins/${userId}/resend-invite/`)
}
