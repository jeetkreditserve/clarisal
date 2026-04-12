import api from '@/lib/api'
import type {
  ApprovalActionItem,
  AttendanceDayRecord,
  AttendancePolicy,
  AttendanceRegularization,
  BankAccount,
  CalendarMonthView,
  DocumentRecord,
  EmployeeDocumentRequest,
  EmployeeEvent,
  EmergencyContact,
  EducationRecord,
  EmployeeDashboard,
  EmployeeAttendanceCalendar,
  EmployeeAttendanceSummary,
  FamilyMember,
  GovernmentId,
  InvestmentDeclaration,
  LeaveEncashmentRequest,
  LeaveOverview,
  LeaveRequestRecord,
  MyOnboardingResponse,
  MyProfileResponse,
  NoticeItem,
  OffboardingProcess,
  OnDutyPolicy,
  OnDutyRequestRecord,
  Payslip,
  TeamMemberSummary,
} from '@/types/hr'

export async function fetchMyDashboard() {
  const { data } = await api.get<EmployeeDashboard>('/me/dashboard/')
  return data
}

export async function fetchMyProfile() {
  const { data } = await api.get<MyProfileResponse>('/me/profile/')
  return data
}

export async function fetchMyOffboarding() {
  const { data } = await api.get<OffboardingProcess | null>('/me/offboarding/')
  return data
}

export async function fetchMyOnboarding() {
  const { data } = await api.get<MyOnboardingResponse>('/me/onboarding/')
  return data
}

export async function updateMyOnboarding(payload: Record<string, unknown>) {
  const { data } = await api.patch<{ profile: MyProfileResponse['profile']; summary: MyOnboardingResponse['summary'] }>(
    '/me/onboarding/',
    payload
  )
  return data
}

export async function updateMyProfile(payload: Record<string, unknown>) {
  const { data } = await api.patch<Pick<MyProfileResponse, 'profile' | 'profile_completion'>>('/me/profile/', payload)
  return data
}

export async function fetchEducation() {
  const { data } = await api.get<EducationRecord[]>('/me/education/')
  return data
}

export async function createFamilyMember(payload: Omit<FamilyMember, 'id' | 'created_at' | 'modified_at'>) {
  const { data } = await api.post<FamilyMember>('/me/family-members/', payload)
  return data
}

export async function updateFamilyMember(id: string, payload: Partial<Omit<FamilyMember, 'id' | 'created_at' | 'modified_at'>>) {
  const { data } = await api.patch<FamilyMember>(`/me/family-members/${id}/`, payload)
  return data
}

export async function deleteFamilyMember(id: string) {
  await api.delete(`/me/family-members/${id}/`)
}

export async function createEmergencyContact(payload: Omit<EmergencyContact, 'id' | 'created_at' | 'modified_at'>) {
  const { data } = await api.post<EmergencyContact>('/me/emergency-contacts/', payload)
  return data
}

export async function updateEmergencyContact(
  id: string,
  payload: Partial<Omit<EmergencyContact, 'id' | 'created_at' | 'modified_at'>>
) {
  const { data } = await api.patch<EmergencyContact>(`/me/emergency-contacts/${id}/`, payload)
  return data
}

export async function deleteEmergencyContact(id: string) {
  await api.delete(`/me/emergency-contacts/${id}/`)
}

export async function createEducation(payload: Omit<EducationRecord, 'id' | 'created_at' | 'modified_at'>) {
  const { data } = await api.post<EducationRecord>('/me/education/', payload)
  return data
}

export async function updateEducation(id: string, payload: Partial<Omit<EducationRecord, 'id' | 'created_at' | 'modified_at'>>) {
  const { data } = await api.patch<EducationRecord>(`/me/education/${id}/`, payload)
  return data
}

export async function deleteEducation(id: string) {
  await api.delete(`/me/education/${id}/`)
}

export async function fetchGovernmentIds() {
  const { data } = await api.get<GovernmentId[]>('/me/government-ids/')
  return data
}

export async function upsertGovernmentId(payload: {
  id_type: string
  identifier: string
  name_on_id?: string
  metadata?: Record<string, unknown>
}) {
  const { data } = await api.post<GovernmentId>('/me/government-ids/', payload)
  return data
}

export async function fetchBankAccounts() {
  const { data } = await api.get<BankAccount[]>('/me/bank-accounts/')
  return data
}

export async function createBankAccount(payload: {
  account_holder_name: string
  bank_name?: string
  account_number: string
  ifsc: string
  account_type?: string
  branch_name?: string
  is_primary?: boolean
}) {
  const { data } = await api.post<BankAccount>('/me/bank-accounts/', payload)
  return data
}

export async function updateBankAccount(
  id: string,
  payload: Partial<{
    account_holder_name: string
    bank_name: string
    account_number: string
    ifsc: string
    account_type: string
    branch_name: string
    is_primary: boolean
  }>
) {
  const { data } = await api.patch<BankAccount>(`/me/bank-accounts/${id}/`, payload)
  return data
}

export async function deleteBankAccount(id: string) {
  await api.delete(`/me/bank-accounts/${id}/`)
}

export async function fetchMyDocuments() {
  const { data } = await api.get<DocumentRecord[]>('/me/documents/')
  return data
}

export async function fetchMyDocumentRequests() {
  const { data } = await api.get<EmployeeDocumentRequest[]>('/me/document-requests/')
  return data
}

export async function uploadRequestedDocument(payload: {
  request_id: string
  file: File
  metadata?: Record<string, unknown>
  expiry_date?: string | null
  alert_days_before?: number
  onUploadProgress?: (progress: number) => void
}) {
  const formData = new FormData()
  formData.append('file', payload.file)
  if (payload.metadata) {
    formData.append('metadata', JSON.stringify(payload.metadata))
  }
  if (payload.expiry_date) {
    formData.append('expiry_date', payload.expiry_date)
  }
  if (payload.alert_days_before) {
    formData.append('alert_days_before', String(payload.alert_days_before))
  }
  const { data } = await api.post<DocumentRecord>(`/me/document-requests/${payload.request_id}/upload/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (!payload.onUploadProgress || !event.total) return
      payload.onUploadProgress(Math.round((event.loaded / event.total) * 100))
    },
  })
  return data
}

export async function uploadMyDocument(payload: {
  document_type: string
  file: File
  metadata?: Record<string, unknown>
  expiry_date?: string | null
  alert_days_before?: number
  onUploadProgress?: (progress: number) => void
}) {
  const formData = new FormData()
  formData.append('document_type', payload.document_type)
  formData.append('file', payload.file)
  if (payload.metadata) {
    formData.append('metadata', JSON.stringify(payload.metadata))
  }
  if (payload.expiry_date) {
    formData.append('expiry_date', payload.expiry_date)
  }
  if (payload.alert_days_before) {
    formData.append('alert_days_before', String(payload.alert_days_before))
  }
  const { data } = await api.post<DocumentRecord>('/me/documents/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (!payload.onUploadProgress || !event.total) return
      payload.onUploadProgress(Math.round((event.loaded / event.total) * 100))
    },
  })
  return data
}

export async function getMyDocumentDownloadUrl(documentId: string) {
  const { data } = await api.get<{ url: string }>(`/me/documents/${documentId}/download/`)
  return data
}

export async function fetchMyNotices() {
  const { data } = await api.get<NoticeItem[]>('/me/notices/')
  return data
}

export async function fetchMyEvents() {
  const { data } = await api.get<EmployeeEvent[]>('/me/events/')
  return data
}

export async function fetchMyApprovalInbox(scope?: 'my_team') {
  const { data } = await api.get<ApprovalActionItem[]>('/me/approvals/inbox/', {
    params: scope ? { scope } : undefined,
  })
  return data
}

export async function fetchMyTeam() {
  const { data } = await api.get<TeamMemberSummary[]>('/me/my-team/')
  return data
}

export async function fetchMyTeamLeave(filters?: {
  status?: string
  fromDate?: string
  toDate?: string
  includeIndirect?: boolean
}) {
  const params: Record<string, string | boolean> = {}
  if (filters?.status) params.status = filters.status
  if (filters?.fromDate) params.from_date = filters.fromDate
  if (filters?.toDate) params.to_date = filters.toDate
  if (filters?.includeIndirect) params.include_indirect = true
  const { data } = await api.get<LeaveRequestRecord[]>('/me/my-team/leave/', {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}

export async function fetchMyTeamAttendance(targetDate?: string, includeIndirect = false) {
  const params: Record<string, string | boolean> = {}
  if (targetDate) params.date = targetDate
  if (includeIndirect) params.include_indirect = true
  const { data } = await api.get<AttendanceDayRecord[]>('/me/my-team/attendance/', {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}

export async function approveMyApprovalAction(actionId: string, comment = '') {
  const { data } = await api.post<ApprovalActionItem>(`/me/approvals/actions/${actionId}/approve/`, { comment })
  return data
}

export async function rejectMyApprovalAction(actionId: string, comment = '') {
  const { data } = await api.post<ApprovalActionItem>(`/me/approvals/actions/${actionId}/reject/`, { comment })
  return data
}

export async function fetchMyLeaveOverview() {
  const { data } = await api.get<LeaveOverview>('/me/leave/')
  return data
}

export async function createMyLeaveRequest(payload: Record<string, unknown>) {
  const { data } = await api.post<LeaveRequestRecord>('/me/leave/requests/', payload)
  return data
}

export async function withdrawMyLeaveRequest(id: string) {
  const { data } = await api.post<LeaveRequestRecord>(`/me/leave/requests/${id}/withdraw/`)
  return data
}

export async function fetchMyLeaveEncashments() {
  const { data } = await api.get<LeaveEncashmentRequest[]>('/me/leave-encashments/')
  return data
}

export async function createMyLeaveEncashment(payload: {
  leave_type_id: string
  cycle_start: string
  cycle_end: string
  days_to_encash: string
}) {
  const { data } = await api.post<LeaveEncashmentRequest>('/me/leave-encashments/', payload)
  return data
}

export async function fetchMyOnDutyPolicies() {
  const { data } = await api.get<OnDutyPolicy[]>('/me/on-duty/policies/')
  return data
}

export async function fetchMyOnDutyRequests() {
  const { data } = await api.get<OnDutyRequestRecord[]>('/me/on-duty/requests/')
  return data
}

export async function fetchMyPayslips(params?: { fiscal_year?: string; search?: string }) {
  const { data } = await api.get<Payslip[]>('/me/payroll/payslips/', { params })
  return data
}

export async function fetchMyPayslip(id: string) {
  const { data } = await api.get<Payslip>(`/me/payroll/payslips/${id}/`)
  return data
}

export async function downloadMyPayslip(id: string) {
  const response = await api.get<Blob>(`/me/payroll/payslips/${id}/download/`, {
    responseType: 'blob',
  })
  return response.data
}

export async function downloadMyPayslipsForFiscalYear(fiscalYear: string) {
  const response = await api.get<Blob>(`/me/payroll/payslips/fiscal-year/${fiscalYear}/download/`, {
    responseType: 'blob',
  })
  return response.data
}

export async function createMyOnDutyRequest(payload: Record<string, unknown>) {
  const { data } = await api.post<OnDutyRequestRecord>('/me/on-duty/requests/', payload)
  return data
}

export async function withdrawMyOnDutyRequest(id: string) {
  const { data } = await api.post<OnDutyRequestRecord>(`/me/on-duty/requests/${id}/withdraw/`)
  return data
}

export async function fetchMyCalendar(month?: string) {
  const { data } = await api.get<CalendarMonthView>('/me/calendar/', {
    params: month ? { month } : undefined,
  })
  return data
}

export async function fetchMyAttendanceSummary() {
  const { data } = await api.get<EmployeeAttendanceSummary>('/me/attendance/summary/')
  return data
}

export async function fetchMyAttendanceHistory(month?: string) {
  const { data } = await api.get<AttendanceDayRecord[]>('/me/attendance/history/', {
    params: month ? { month } : undefined,
  })
  return data
}

export async function fetchMyAttendanceCalendar(month?: string) {
  const { data } = await api.get<EmployeeAttendanceCalendar>('/me/attendance/calendar/', {
    params: month ? { month } : undefined,
  })
  return data
}

export async function fetchMyAttendancePolicy() {
  const { data } = await api.get<AttendancePolicy>('/me/attendance/policy/')
  return data
}

export async function punchIn(payload?: { latitude?: number | null; longitude?: number | null }) {
  const { data } = await api.post<AttendanceDayRecord>('/me/attendance/punch-in/', payload ?? {})
  return data
}

export async function punchOut(payload?: { latitude?: number | null; longitude?: number | null }) {
  const { data } = await api.post<AttendanceDayRecord>('/me/attendance/punch-out/', payload ?? {})
  return data
}

export async function fetchMyAttendanceRegularizations() {
  const { data } = await api.get<AttendanceRegularization[]>('/me/attendance/regularizations/')
  return data
}

export async function createMyAttendanceRegularization(payload: {
  attendance_date: string
  requested_check_in?: string | null
  requested_check_out?: string | null
  reason: string
}) {
  const { data } = await api.post<AttendanceRegularization>('/me/attendance/regularizations/', payload)
  return data
}

export async function updateMyAttendanceRegularization(
  id: string,
  payload: { requested_check_in?: string | null; requested_check_out?: string | null; reason?: string }
) {
  const { data } = await api.patch<AttendanceRegularization>(`/me/attendance/regularizations/${id}/`, payload)
  return data
}

export async function withdrawMyAttendanceRegularization(id: string) {
  const { data } = await api.post<AttendanceRegularization>(`/me/attendance/regularizations/${id}/withdraw/`)
  return data
}

export async function downloadMyForm12BB(fiscalYear: string): Promise<Blob> {
  const response = await api.get<Blob>(`/me/payroll/form-12bb/${fiscalYear}/`, {
    responseType: 'blob',
  })
  return response.data
}

export async function fetchMyInvestmentDeclarations(params?: { fiscal_year?: string }) {
  const { data } = await api.get<InvestmentDeclaration[]>('/me/payroll/investment-declarations/', { params })
  return data
}

export async function createMyInvestmentDeclaration(payload: {
  fiscal_year: string
  section: string
  description: string
  declared_amount: string
  proof_document_id?: string | null
}) {
  const { data } = await api.post<InvestmentDeclaration>('/me/payroll/investment-declarations/', payload)
  return data
}

export async function updateMyInvestmentDeclaration(
  id: string,
  payload: Partial<{
    fiscal_year: string
    section: string
    description: string
    declared_amount: string
    proof_document_id: string | null
  }>
) {
  const { data } = await api.patch<InvestmentDeclaration>(`/me/payroll/investment-declarations/${id}/`, payload)
  return data
}

export async function deleteMyInvestmentDeclaration(id: string) {
  await api.delete(`/me/payroll/investment-declarations/${id}/`)
}
