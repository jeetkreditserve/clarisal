import api from '@/lib/api'
import type {
  ApprovalActionItem,
  BankAccount,
  CalendarMonthView,
  DocumentRecord,
  EmployeeDocumentRequest,
  EmployeeEvent,
  EmergencyContact,
  EducationRecord,
  EmployeeDashboard,
  FamilyMember,
  GovernmentId,
  LeaveOverview,
  LeaveRequestRecord,
  MyOnboardingResponse,
  MyProfileResponse,
  NoticeItem,
  OnDutyPolicy,
  OnDutyRequestRecord,
  Payslip,
} from '@/types/hr'

export async function fetchMyDashboard() {
  const { data } = await api.get<EmployeeDashboard>('/me/dashboard/')
  return data
}

export async function fetchMyProfile() {
  const { data } = await api.get<MyProfileResponse>('/me/profile/')
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
  onUploadProgress?: (progress: number) => void
}) {
  const formData = new FormData()
  formData.append('file', payload.file)
  if (payload.metadata) {
    formData.append('metadata', JSON.stringify(payload.metadata))
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
  onUploadProgress?: (progress: number) => void
}) {
  const formData = new FormData()
  formData.append('document_type', payload.document_type)
  formData.append('file', payload.file)
  if (payload.metadata) {
    formData.append('metadata', JSON.stringify(payload.metadata))
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

export async function fetchMyApprovalInbox() {
  const { data } = await api.get<ApprovalActionItem[]>('/me/approvals/inbox/')
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

export async function fetchMyOnDutyPolicies() {
  const { data } = await api.get<OnDutyPolicy[]>('/me/on-duty/policies/')
  return data
}

export async function fetchMyOnDutyRequests() {
  const { data } = await api.get<OnDutyRequestRecord[]>('/me/on-duty/requests/')
  return data
}

export async function fetchMyPayslips() {
  const { data } = await api.get<Payslip[]>('/me/payroll/payslips/')
  return data
}

export async function fetchMyPayslip(id: string) {
  const { data } = await api.get<Payslip>(`/me/payroll/payslips/${id}/`)
  return data
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
