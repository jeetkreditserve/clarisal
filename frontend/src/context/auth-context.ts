import { createContext } from 'react'
import type { AuthUser } from '@/types/auth'

export interface AuthContextType {
  user: AuthUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<AuthUser>
  loginControlTower: (email: string, password: string) => Promise<AuthUser>
  switchWorkspace: (payload: { workspace_kind: 'ADMIN' | 'EMPLOYEE'; organisation_id: string }) => Promise<AuthUser>
  logout: () => Promise<void>
  refreshUser: () => Promise<AuthUser | null>
}

export const AuthContext = createContext<AuthContextType | null>(null)
