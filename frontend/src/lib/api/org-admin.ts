import api from '@/lib/api'
import type {
  OrgDashboardStats,
  OrganisationEntityType,
  OrganisationAddress,
  OrganisationDetail,
  PaginatedResponse,
} from '@/types/organisation'
import type { OrgAdminSetupState } from '@/types/organisation'
import type {
  ApprovalActionItem,
  ApprovalWorkflowConfig,
  Department,
  DocumentRecord,
  EmployeeDocumentRequest,
  EmployeeDetail,
  EmployeeListItem,
  HolidayCalendar,
  LeaveCycle,
  LeavePlan,
  LeaveRequestRecord,
  Location,
  NoticeItem,
  OnDutyPolicy,
  OnDutyRequestRecord,
  OnboardingDocumentType,
} from '@/types/hr'

export async function fetchOrgDashboard() {
  const { data } = await api.get<OrgDashboardStats>('/org/dashboard/')
  return data
}

export async function fetchOrgSetup() {
  const { data } = await api.get<OrgAdminSetupState>('/org/setup/')
  return data
}

export async function updateOrgSetup(payload: { current_step?: string; completed?: boolean }) {
  const { data } = await api.patch<OrgAdminSetupState>('/org/setup/', payload)
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
  entity_type: OrganisationEntityType
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
  state_code?: string
  country?: string
  country_code?: string
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
  state_code: string
  country: string
  country_code: string
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
  required_document_type_ids?: string[]
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
    leave_approval_workflow_id: string | null
    on_duty_approval_workflow_id: string | null
    attendance_regularization_approval_workflow_id: string | null
  }>
) {
  const { data } = await api.patch<EmployeeDetail>(`/org/employees/${id}/`, payload)
  return data
}

export async function markEmployeeJoined(
  id: string,
  payload: {
    employee_code: string
    date_of_joining: string
    designation: string
    reporting_to_employee_id: string
  }
) {
  const { data } = await api.post<EmployeeDetail>(`/org/employees/${id}/mark-joined/`, payload)
  return data
}

export async function fetchOnboardingDocumentTypes() {
  const { data } = await api.get<OnboardingDocumentType[]>('/org/document-types/')
  return data
}

export async function fetchEmployeeDocumentRequests(employeeId: string) {
  const { data } = await api.get<EmployeeDocumentRequest[]>(`/org/employees/${employeeId}/document-requests/`)
  return data
}

export async function assignEmployeeDocumentRequests(employeeId: string, documentTypeIds: string[]) {
  const { data } = await api.post<EmployeeDocumentRequest[]>(
    `/org/employees/${employeeId}/document-requests/`,
    { document_type_ids: documentTypeIds }
  )
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

export async function fetchApprovalWorkflows() {
  const { data } = await api.get<ApprovalWorkflowConfig[]>('/org/approvals/workflows/')
  return data
}

export async function fetchApprovalWorkflow(id: string) {
  const { data } = await api.get<ApprovalWorkflowConfig>(`/org/approvals/workflows/${id}/`)
  return data
}

export async function createApprovalWorkflow(payload: Record<string, unknown>) {
  const { data } = await api.post<ApprovalWorkflowConfig>('/org/approvals/workflows/', payload)
  return data
}

export async function updateApprovalWorkflow(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<ApprovalWorkflowConfig>(`/org/approvals/workflows/${id}/`, payload)
  return data
}

export async function fetchApprovalInbox() {
  const { data } = await api.get<ApprovalActionItem[]>('/org/approvals/inbox/')
  return data
}

export async function approveApprovalAction(actionId: string, comment = '') {
  const { data } = await api.post<ApprovalActionItem>(`/org/approvals/actions/${actionId}/approve/`, { comment })
  return data
}

export async function rejectApprovalAction(actionId: string, comment = '') {
  const { data } = await api.post<ApprovalActionItem>(`/org/approvals/actions/${actionId}/reject/`, { comment })
  return data
}

export async function fetchHolidayCalendars() {
  const { data } = await api.get<HolidayCalendar[]>('/org/holiday-calendars/')
  return data
}

export async function createHolidayCalendar(payload: Record<string, unknown>) {
  const { data } = await api.post<HolidayCalendar>('/org/holiday-calendars/', payload)
  return data
}

export async function updateHolidayCalendar(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<HolidayCalendar>(`/org/holiday-calendars/${id}/`, payload)
  return data
}

export async function publishHolidayCalendar(id: string) {
  const { data } = await api.post<HolidayCalendar>(`/org/holiday-calendars/${id}/publish/`)
  return data
}

export async function fetchLeaveCycles() {
  const { data } = await api.get<LeaveCycle[]>('/org/leave-cycles/')
  return data
}

export async function createLeaveCycle(payload: Record<string, unknown>) {
  const { data } = await api.post<LeaveCycle>('/org/leave-cycles/', payload)
  return data
}

export async function updateLeaveCycle(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<LeaveCycle>(`/org/leave-cycles/${id}/`, payload)
  return data
}

export async function fetchLeavePlans() {
  const { data } = await api.get<LeavePlan[]>('/org/leave-plans/')
  return data
}

export async function fetchLeavePlan(id: string) {
  const { data } = await api.get<LeavePlan>(`/org/leave-plans/${id}/`)
  return data
}

export async function createLeavePlan(payload: Record<string, unknown>) {
  const { data } = await api.post<LeavePlan>('/org/leave-plans/', payload)
  return data
}

export async function updateLeavePlan(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<LeavePlan>(`/org/leave-plans/${id}/`, payload)
  return data
}

export async function fetchOnDutyPolicies() {
  const { data } = await api.get<OnDutyPolicy[]>('/org/on-duty-policies/')
  return data
}

export async function fetchOnDutyPolicy(id: string) {
  const { data } = await api.get<OnDutyPolicy>(`/org/on-duty-policies/${id}/`)
  return data
}

export async function createOnDutyPolicy(payload: Record<string, unknown>) {
  const { data } = await api.post<OnDutyPolicy>('/org/on-duty-policies/', payload)
  return data
}

export async function updateOnDutyPolicy(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<OnDutyPolicy>(`/org/on-duty-policies/${id}/`, payload)
  return data
}

export async function fetchOrgLeaveRequests() {
  const { data } = await api.get<LeaveRequestRecord[]>('/org/leave-requests/')
  return data
}

export async function fetchOrgOnDutyRequests() {
  const { data } = await api.get<OnDutyRequestRecord[]>('/org/on-duty-requests/')
  return data
}

export async function fetchNotices(params?: { status?: string; audience_type?: string; search?: string }) {
  const { data } = await api.get<NoticeItem[]>('/org/notices/', { params })
  return data
}

export async function fetchNotice(id: string) {
  const { data } = await api.get<NoticeItem>(`/org/notices/${id}/`)
  return data
}

export async function createNotice(payload: Record<string, unknown>) {
  const { data } = await api.post<NoticeItem>('/org/notices/', payload)
  return data
}

export async function updateNotice(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<NoticeItem>(`/org/notices/${id}/`, payload)
  return data
}

export async function publishNotice(id: string) {
  const { data } = await api.post<NoticeItem>(`/org/notices/${id}/publish/`)
  return data
}
