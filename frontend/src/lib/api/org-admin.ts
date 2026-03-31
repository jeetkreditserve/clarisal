import api from '@/lib/api'
import type {
  OrgDashboardStats,
  OrganisationAddress,
  OrganisationDetail,
  PaginatedResponse,
} from '@/types/organisation'
import type {
  Department,
  DocumentRecord,
  EmployeeDetail,
  EmployeeListItem,
  Location,
} from '@/types/hr'

export async function fetchOrgDashboard() {
  const { data } = await api.get<OrgDashboardStats>('/org/dashboard/')
  return data
}

export async function fetchOrgProfile() {
  const { data } = await api.get<OrganisationDetail>('/org/profile/')
  return data
}

export async function updateOrgProfile(payload: Partial<{
  name: string
  pan_number: string
  phone: string
  email: string
  country_code: string
  currency: string
  logo_url: string
}>) {
  const { data } = await api.patch<OrganisationDetail>('/org/profile/', payload)
  return data
}

export async function createOrgAddress(payload: {
  address_type: string
  label?: string
  line1: string
  line2?: string
  city: string
  state: string
  country?: string
  pincode: string
  gstin?: string | null
}) {
  const { data } = await api.post<OrganisationAddress>('/org/profile/addresses/', payload)
  return data
}

export async function updateOrgAddress(addressId: string, payload: Partial<{
  address_type: string
  label: string
  line1: string
  line2: string
  city: string
  state: string
  country: string
  pincode: string
  gstin: string | null
}>) {
  const { data } = await api.patch<OrganisationAddress>(`/org/profile/addresses/${addressId}/`, payload)
  return data
}

export async function deactivateOrgAddress(addressId: string) {
  const { data } = await api.delete<OrganisationAddress>(`/org/profile/addresses/${addressId}/`)
  return data
}

export async function fetchLocations(includeInactive = false) {
  const { data } = await api.get<Location[]>('/org/locations/', {
    params: { include_inactive: includeInactive },
  })
  return data
}

export async function createLocation(payload: {
  name: string
  organisation_address_id: string
  is_remote?: boolean
}) {
  const { data } = await api.post<Location>('/org/locations/', payload)
  return data
}

export async function updateLocation(id: string, payload: Partial<{
  name: string
  organisation_address_id: string
  is_remote: boolean
}>) {
  const { data } = await api.patch<Location>(`/org/locations/${id}/`, payload)
  return data
}

export async function deactivateLocation(id: string) {
  const { data } = await api.post<Location>(`/org/locations/${id}/deactivate/`)
  return data
}

export async function fetchDepartments(includeInactive = false) {
  const { data } = await api.get<Department[]>('/org/departments/', {
    params: { include_inactive: includeInactive },
  })
  return data
}

export async function createDepartment(payload: {
  name: string
  description?: string
  parent_department_id?: string | null
}) {
  const { data } = await api.post<Department>('/org/departments/', payload)
  return data
}

export async function updateDepartment(
  id: string,
  payload: Partial<{ name: string; description: string; parent_department_id: string | null }>
) {
  const { data } = await api.patch<Department>(`/org/departments/${id}/`, payload)
  return data
}

export async function deactivateDepartment(id: string) {
  const { data } = await api.post<Department>(`/org/departments/${id}/deactivate/`)
  return data
}

export async function fetchEmployees(params?: {
  status?: string
  search?: string
  page?: number
}) {
  const { data } = await api.get<PaginatedResponse<EmployeeListItem>>('/org/employees/', { params })
  return data
}

export async function inviteEmployee(payload: {
  first_name: string
  last_name: string
  company_email: string
  designation?: string
  employment_type?: string
  date_of_joining?: string | null
  department_id?: string | null
  office_location_id?: string | null
}) {
  const { data } = await api.post<{
    employee: EmployeeDetail
    invitation: { email: string; expires_at: string }
  }>('/org/employees/', payload)
  return data
}

export async function fetchEmployeeDetail(id: string) {
  const { data } = await api.get<EmployeeDetail>(`/org/employees/${id}/`)
  return data
}

export async function updateEmployee(
  id: string,
  payload: Partial<{
    designation: string
    employment_type: string
    date_of_joining: string | null
    department_id: string | null
    office_location_id: string | null
  }>
) {
  const { data } = await api.patch<EmployeeDetail>(`/org/employees/${id}/`, payload)
  return data
}

export async function markEmployeeJoined(id: string, payload: { employee_code: string; date_of_joining: string }) {
  const { data } = await api.post<EmployeeDetail>(`/org/employees/${id}/mark-joined/`, payload)
  return data
}

export async function endEmployeeEmployment(
  id: string,
  payload: { status: 'RESIGNED' | 'RETIRED' | 'TERMINATED'; date_of_exit: string }
) {
  const { data } = await api.post<EmployeeDetail>(`/org/employees/${id}/end-employment/`, payload)
  return data
}

export async function deleteEmployee(id: string) {
  const { data } = await api.delete<EmployeeDetail>(`/org/employees/${id}/delete/`)
  return data
}

export async function fetchEmployeeDocuments(employeeId: string) {
  const { data } = await api.get<DocumentRecord[]>(`/org/employees/${employeeId}/documents/`)
  return data
}

export async function verifyEmployeeDocument(employeeId: string, documentId: string) {
  const { data } = await api.post<DocumentRecord>(`/org/employees/${employeeId}/documents/${documentId}/verify/`)
  return data
}

export async function rejectEmployeeDocument(employeeId: string, documentId: string, note: string) {
  const { data } = await api.post<DocumentRecord>(`/org/employees/${employeeId}/documents/${documentId}/reject/`, {
    note,
  })
  return data
}

export async function getEmployeeDocumentDownloadUrl(employeeId: string, documentId: string) {
  const { data } = await api.get<{ url: string }>(`/org/employees/${employeeId}/documents/${documentId}/download/`)
  return data
}
