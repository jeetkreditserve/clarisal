import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { AuthShell } from '@/components/auth/AuthShell'
import { useAuth } from '@/hooks/useAuth'
import { getErrorMessage } from '@/lib/errors'
import { getDefaultRoute } from '@/lib/rbac'

export function ControlTowerLoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { loginControlTower } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      const user = await loginControlTower(email, password)
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname
      navigate(from || getDefaultRoute(user), { replace: true })
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Invalid Control Tower credentials.'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title="Control Tower sign in"
      description="Separate secure access for Calrisal platform operators and Django admin users."
      footer={
        <div className="flex items-center justify-between gap-4">
          <a href="/ct/reset-password" className="font-medium text-[hsl(var(--primary))] hover:underline">
            Forgot your password?
          </a>
          <a href="/auth/login" className="font-medium text-slate-500 hover:text-slate-900 hover:underline">
            Workforce login
          </a>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="ct-email" className="field-label">
            Control Tower email
          </label>
          <input
            id="ct-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="field-input"
            placeholder="operator@calrisal.com"
          />
        </div>
        <div>
          <label htmlFor="ct-password" className="field-label">
            Password
          </label>
          <input
            id="ct-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="field-input"
            placeholder="Enter your password"
          />
        </div>

        {error ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
        ) : null}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading ? 'Signing in...' : 'Enter Control Tower'}
        </button>
      </form>
    </AuthShell>
  )
}
