import axios, { type AxiosError } from 'axios'

const BASE_URL = import.meta.env.DEV ? '/api' : import.meta.env.VITE_API_BASE_URL || '/api'
let csrfPrimed = false

function getCookie(name: string): string | null {
  const match = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=')[1]) : null
}

export async function ensureCsrfCookie() {
  if (csrfPrimed) return
  await axios.get(`${BASE_URL}/auth/csrf/`, { withCredentials: true })
  csrfPrimed = true
}

export const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(async (config) => {
  const method = config.method?.toLowerCase()
  const safeMethod = !method || ['get', 'head', 'options'].includes(method)
  const csrfRequest = config.url?.includes('/auth/csrf/')

  if (!safeMethod && !csrfRequest) {
    await ensureCsrfCookie()
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
  }

  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const url = error.config?.url ?? ''
    const isAuthMutation = [
      '/auth/login/',
      '/auth/control-tower/login/',
      '/auth/workspace/',
      '/auth/invite/accept/',
      '/auth/password-reset/confirm/',
    ].some((path) => url.includes(path))

    if ((error.response?.status === 401 || error.response?.status === 403) && !isAuthMutation) {
      window.dispatchEvent(new Event('calrisal:auth-lost'))
    }

    return Promise.reject(error)
  }
)

export default api
