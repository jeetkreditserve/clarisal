import api from '@/lib/api'
import type { OrgDashboardStats, PaginatedResponse } from '@/types/organisation'
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

export async function fetchLocations(includeInactive = false) {
  const { data } = await api.get<Location[]>('/org/locations/', {
    params: { include_inactive: includeInactive },
  })
  return data
}

export async function createLocation(payload: {
  name: string
  address?: string
  city?: string
  state?: string
  country?: string
  pincode?: string
}) {
  const { data } = await api.post<Location>('/org/locations/', payload)
  return data
}

export async function updateLocation(id: string, payload: Partial<{
  name: string
  address: string
  city: string
  state: string
  country: string
  pincode: string
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

export async function createDepartment(payload: { name: string; description?: string }) {
  const { data } = await api.post<Department>('/org/departments/', payload)
  return data
}

export async function updateDepartment(id: string, payload: Partial<{ name: string; description: string }>) {
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
  email: string
  first_name: string
  last_name: string
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
    status: string
  }>
) {
  const { data } = await api.patch<EmployeeDetail>(`/org/employees/${id}/`, payload)
  return data
}

export async function terminateEmployee(id: string) {
  const { data } = await api.post<EmployeeDetail>(`/org/employees/${id}/terminate/`)
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
