import api from '@/lib/api'
import type { LoginResponse } from '@/types/auth'

export async function loginWorkforce(email: string, password: string) {
  const { data } = await api.post<LoginResponse>('/auth/login/', { email, password })
  return data
}

export async function loginControlTower(email: string, password: string) {
  const { data } = await api.post<LoginResponse>('/auth/control-tower/login/', { email, password })
  return data
}

export async function switchWorkspace(payload: {
  workspace_kind: 'ADMIN' | 'EMPLOYEE'
  organisation_id: string
}) {
  const { data } = await api.post<LoginResponse>('/auth/workspace/', payload)
  return data
}

export async function requestPasswordReset(email: string) {
  const { data } = await api.post<{ detail: string }>('/auth/password-reset/request/', { email })
  return data
}

export async function requestControlTowerPasswordReset(email: string) {
  const { data } = await api.post<{ detail: string }>('/auth/control-tower/password-reset/request/', { email })
  return data
}

export async function validatePasswordResetToken(token: string) {
  const { data } = await api.get<{ email: string; account_type: string }>(`/auth/password-reset/validate/${token}/`)
  return data
}

export async function confirmPasswordReset(payload: {
  token: string
  password: string
  confirm_password: string
}) {
  const { data } = await api.post<LoginResponse>('/auth/password-reset/confirm/', payload)
  return data
}
