import api from '@/lib/api'

export async function validateInviteToken(token: string): Promise<{
  email: string
  role: string
  organisation_name: string | null
}> {
  const { data } = await api.get(`/auth/invite/validate/${token}/`)
  return data
}

export async function acceptInvite(payload: {
  token: string
  password: string
  confirm_password: string
}): Promise<{
  access: string
  refresh: string
  user: { id: string; email: string; role: string; org_id: string | null }
}> {
  const { data } = await api.post('/auth/invite/accept/', payload)
  return data
}
