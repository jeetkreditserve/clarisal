import api from '@/lib/api'
import type { AcceptInviteResponse } from '@/types/auth'

export async function validateInviteToken(token: string): Promise<{
  email: string
  role: string
  organisation_name: string | null
  requires_password_setup: boolean
}> {
  const { data } = await api.get(`/auth/invite/validate/${token}/`)
  return data
}

export async function acceptInvite(payload: {
  token: string
  password?: string
  confirm_password?: string
}): Promise<AcceptInviteResponse> {
  const { data } = await api.post<AcceptInviteResponse>('/auth/invite/accept/', payload)
  return data
}
