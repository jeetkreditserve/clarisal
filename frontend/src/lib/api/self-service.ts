import api from '@/lib/api'
import type {
  BankAccount,
  DocumentRecord,
  EducationRecord,
  EmployeeDashboard,
  GovernmentId,
  MyProfileResponse,
} from '@/types/hr'

export async function fetchMyDashboard() {
  const { data } = await api.get<EmployeeDashboard>('/me/dashboard/')
  return data
}

export async function fetchMyProfile() {
  const { data } = await api.get<MyProfileResponse>('/me/profile/')
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

export async function createEducation(payload: Omit<EducationRecord, 'id' | 'created_at' | 'updated_at'>) {
  const { data } = await api.post<EducationRecord>('/me/education/', payload)
  return data
}

export async function updateEducation(id: string, payload: Partial<Omit<EducationRecord, 'id' | 'created_at' | 'updated_at'>>) {
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

export async function uploadMyDocument(payload: {
  document_type: string
  file: File
  metadata?: Record<string, unknown>
}) {
  const formData = new FormData()
  formData.append('document_type', payload.document_type)
  formData.append('file', payload.file)
  if (payload.metadata) {
    formData.append('metadata', JSON.stringify(payload.metadata))
  }
  const { data } = await api.post<DocumentRecord>('/me/documents/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getMyDocumentDownloadUrl(documentId: string) {
  const { data } = await api.get<{ url: string }>(`/me/documents/${documentId}/download/`)
  return data
}
