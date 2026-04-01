import { isAxiosError } from 'axios'

function firstValue(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return null
}

function collectFieldErrors(
  value: unknown,
  currentPath: string,
  fieldErrors: Record<string, string>
) {
  const message = firstValue(value)
  if (message && currentPath) {
    fieldErrors[currentPath] = message
    return
  }

  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return
  }

  for (const [key, nestedValue] of Object.entries(value as Record<string, unknown>)) {
    if (key === 'error' || key === 'detail') continue
    const nextPath = currentPath ? `${currentPath}.${key}` : key
    collectFieldErrors(nestedValue, nextPath, fieldErrors)
  }
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

export function getFieldErrors(error: unknown) {
  if (!isAxiosError(error)) return {}

  const data = error.response?.data
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return {}
  }

  const fieldErrors: Record<string, string> = {}
  for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
    if (key === 'error' || key === 'detail') continue
    collectFieldErrors(value, key, fieldErrors)
  }
  return fieldErrors
}
