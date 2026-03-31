import { isAxiosError } from 'axios'

function firstValue(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return null
}

export function getErrorMessage(error: unknown, fallback = 'Something went wrong.') {
  if (!isAxiosError(error)) return fallback

  const data = error.response?.data
  if (!data || typeof data !== 'object') {
    return fallback
  }

  for (const key of ['error', 'detail', 'token', 'password', 'confirm_password', 'email']) {
    const message = firstValue((data as Record<string, unknown>)[key])
    if (message) return message
  }

  for (const value of Object.values(data as Record<string, unknown>)) {
    const message = firstValue(value)
    if (message) return message
  }

  return fallback
}
