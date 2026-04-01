import api from '@/lib/api'
import type {
  CtDashboardStats,
  LicenceBatch,
  OrganisationNote,
  OrgAdmin,
  OrganisationEntityType,
  OrganisationAddress,
  OrganisationDetail,
  OrganisationListItem,
  PaginatedResponse,
} from '@/types/organisation'
import type {
  ApprovalWorkflowConfig,
  Department,
  EmployeeDetail,
  EmployeeListItem,
  HolidayCalendar,
  LeaveCycle,
  LeavePlan,
  Location,
  NoticeItem,
  OnDutyPolicy,
} from '@/types/hr'

export interface OrganisationAddressInput {
  address_type: 'REGISTERED' | 'BILLING' | 'HEADQUARTERS' | 'WAREHOUSE' | 'CUSTOM'
  label?: string
  line1: string
  line2?: string
  city: string
  state: string
  state_code?: string
  country?: string
  country_code?: string
  pincode: string
  gstin?: string | null
}

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
  pan_number: string
  country_code?: string
  currency?: string
  entity_type: OrganisationEntityType
  billing_same_as_registered?: boolean
  primary_admin: {
    first_name: string
    last_name: string
    email: string
    phone?: string
  }
  addresses: OrganisationAddressInput[]
}): Promise<OrganisationDetail> {
  const { data } = await api.post('/ct/organisations/', payload)
  return data
}

export async function updateOrganisation(id: string, payload: {
  name?: string
  pan_number?: string
  phone?: string
  email?: string
  country_code?: string
  currency?: string
  entity_type?: OrganisationEntityType
  logo_url?: string
}): Promise<OrganisationDetail> {
  const { data } = await api.patch(`/ct/organisations/${id}/`, payload)
  return data
}

export async function createOrganisationAddress(id: string, payload: OrganisationAddressInput): Promise<OrganisationAddress> {
  const { data } = await api.post(`/ct/organisations/${id}/addresses/`, payload)
  return data
}

export async function updateOrganisationAddress(
  id: string,
  addressId: string,
  payload: Partial<OrganisationAddressInput>
): Promise<OrganisationAddress> {
  const { data } = await api.patch(`/ct/organisations/${id}/addresses/${addressId}/`, payload)
  return data
}

export async function deactivateOrganisationAddress(id: string, addressId: string): Promise<OrganisationAddress> {
  const { data } = await api.delete(`/ct/organisations/${id}/addresses/${addressId}/`)
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
  overage_count: number
  utilisation_percent: number
}> {
  const { data } = await api.get(`/ct/organisations/${id}/licences/`)
  return data
}

export async function fetchLicenceBatches(id: string): Promise<LicenceBatch[]> {
  const { data } = await api.get(`/ct/organisations/${id}/licence-batches/`)
  return data
}

export async function createLicenceBatch(
  id: string,
  payload: {
    quantity: number
    price_per_licence_per_month: string
    start_date: string
    end_date: string
    note?: string
  }
): Promise<LicenceBatch> {
  const { data } = await api.post(`/ct/organisations/${id}/licence-batches/`, payload)
  return data
}

export async function updateLicenceBatch(
  id: string,
  batchId: string,
  payload: Partial<{
    quantity: number
    price_per_licence_per_month: string
    start_date: string
    end_date: string
    note: string
  }>
): Promise<LicenceBatch> {
  const { data } = await api.patch(`/ct/organisations/${id}/licence-batches/${batchId}/`, payload)
  return data
}

export async function markLicenceBatchPaid(
  id: string,
  batchId: string,
  payload?: { paid_at?: string }
): Promise<LicenceBatch> {
  const { data } = await api.post(`/ct/organisations/${id}/licence-batches/${batchId}/mark-paid/`, payload ?? {})
  return data
}

export async function fetchOrgAdmins(id: string): Promise<OrgAdmin[]> {
  const { data } = await api.get(`/ct/organisations/${id}/admins/`)
  return data
}

export async function fetchCtOrgEmployees(
  id: string,
  params?: { status?: string; search?: string; page?: number }
): Promise<PaginatedResponse<EmployeeListItem>> {
  const { data } = await api.get(`/ct/organisations/${id}/employees/`, { params })
  return data
}

export async function fetchCtOrgEmployeeDetail(id: string, employeeId: string): Promise<EmployeeDetail> {
  const { data } = await api.get(`/ct/organisations/${id}/employees/${employeeId}/`)
  return data
}

export async function fetchCtHolidayCalendars(id: string): Promise<HolidayCalendar[]> {
  const { data } = await api.get(`/ct/organisations/${id}/holiday-calendars/`)
  return data
}

export async function createCtHolidayCalendar(id: string, payload: Record<string, unknown>): Promise<HolidayCalendar> {
  const { data } = await api.post(`/ct/organisations/${id}/holiday-calendars/`, payload)
  return data
}

export async function updateCtHolidayCalendar(
  id: string,
  calendarId: string,
  payload: Record<string, unknown>
): Promise<HolidayCalendar> {
  const { data } = await api.patch(`/ct/organisations/${id}/holiday-calendars/${calendarId}/`, payload)
  return data
}

export async function publishCtHolidayCalendar(id: string, calendarId: string): Promise<HolidayCalendar> {
  const { data } = await api.post(`/ct/organisations/${id}/holiday-calendars/${calendarId}/publish/`)
  return data
}

export async function fetchCtOrgConfiguration(id: string): Promise<{
  locations: Location[]
  departments: Department[]
  leave_cycles: LeaveCycle[]
  leave_plans: LeavePlan[]
  on_duty_policies: OnDutyPolicy[]
  approval_workflows: ApprovalWorkflowConfig[]
  notices: NoticeItem[]
}> {
  const { data } = await api.get(`/ct/organisations/${id}/configuration/`)
  return data
}

export async function fetchCtOrgNotes(id: string): Promise<OrganisationNote[]> {
  const { data } = await api.get(`/ct/organisations/${id}/notes/`)
  return data
}

export async function createCtOrgNote(id: string, body: string): Promise<OrganisationNote> {
  const { data } = await api.post(`/ct/organisations/${id}/notes/`, { body })
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
