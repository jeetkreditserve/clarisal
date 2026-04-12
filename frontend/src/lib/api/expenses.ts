import api from '@/lib/api'
import type { ExpenseClaim, ExpenseClaimSummary, ExpensePolicy, ExpenseReceipt } from '@/types/hr'

export async function fetchMyExpensePolicies() {
  const { data } = await api.get<ExpensePolicy[]>('/me/expenses/policies/')
  return data
}

export async function fetchMyExpenseClaims() {
  const { data } = await api.get<ExpenseClaim[]>('/me/expenses/claims/')
  return data
}

export async function createMyExpenseClaim(payload: Record<string, unknown>) {
  const { data } = await api.post<ExpenseClaim>('/me/expenses/claims/', payload)
  return data
}

export async function updateMyExpenseClaim(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<ExpenseClaim>(`/me/expenses/claims/${id}/`, payload)
  return data
}

export async function uploadMyExpenseReceipt(claimId: string, lineId: string, file: File) {
  const formData = new FormData()
  formData.append('line_id', lineId)
  formData.append('file', file)
  const { data } = await api.post<ExpenseReceipt>(`/me/expenses/claims/${claimId}/receipts/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function submitMyExpenseClaim(id: string) {
  const { data } = await api.post<ExpenseClaim>(`/me/expenses/claims/${id}/submit/`)
  return data
}

export async function cancelMyExpenseClaim(id: string) {
  const { data } = await api.patch<ExpenseClaim>(`/me/expenses/claims/${id}/status/`, { status: 'CANCELLED' })
  return data
}

export async function fetchOrgExpensePolicies() {
  const { data } = await api.get<ExpensePolicy[]>('/org/expenses/policies/')
  return data
}

export async function createOrgExpensePolicy(payload: Record<string, unknown>) {
  const { data } = await api.post<ExpensePolicy>('/org/expenses/policies/', payload)
  return data
}

export async function updateOrgExpensePolicy(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<ExpensePolicy>(`/org/expenses/policies/${id}/`, payload)
  return data
}

export async function fetchOrgExpenseClaims(params?: {
  status?: string
  reimbursement_status?: string
  employee?: string
}) {
  const { data } = await api.get<ExpenseClaim[]>('/org/expenses/claims/', { params })
  return data
}

export async function fetchOrgExpenseClaimSummary() {
  const { data } = await api.get<ExpenseClaimSummary>('/org/expenses/claims/summary/')
  return data
}
