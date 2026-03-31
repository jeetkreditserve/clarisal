import { useEffect, useState, type ReactNode } from 'react'
import type { AuthUser } from '@/types/auth'
import api, { ensureCsrfCookie } from '@/lib/api'
import { loginControlTower, loginWorkforce, switchWorkspace as switchWorkspaceRequest } from '@/lib/api/auth'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = async () => {
    try {
      await ensureCsrfCookie()
      const response = await api.get<AuthUser>('/auth/me/')
      setUser(response.data)
      return response.data
    } catch {
      setUser(null)
      return null
    }
  }

  useEffect(() => {
    let active = true

    async function bootstrap() {
      setIsLoading(true)
      const currentUser = await refreshUser()
      if (!active) return
      setUser(currentUser)
      setIsLoading(false)
    }

    void bootstrap()

    const handleAuthLoss = () => {
      setUser(null)
    }

    window.addEventListener('calrisal:auth-lost', handleAuthLoss)
    return () => {
      active = false
      window.removeEventListener('calrisal:auth-lost', handleAuthLoss)
    }
  }, [])

  const login = async (email: string, password: string) => {
    await ensureCsrfCookie()
    const response = await loginWorkforce(email, password)
    setUser(response.user)
    return response.user
  }

  const loginControlTowerAccount = async (email: string, password: string) => {
    await ensureCsrfCookie()
    const response = await loginControlTower(email, password)
    setUser(response.user)
    return response.user
  }

  const switchWorkspace = async (payload: { workspace_kind: 'ADMIN' | 'EMPLOYEE'; organisation_id: string }) => {
    const response = await switchWorkspaceRequest(payload)
    setUser(response.user)
    return response.user
  }

  const logout = async () => {
    try {
      await api.post('/auth/logout/', {})
    } catch {
      // Ignore logout failures when the session is already gone.
    }
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        loginControlTower: loginControlTowerAccount,
        switchWorkspace,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
