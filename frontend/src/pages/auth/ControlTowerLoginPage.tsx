import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { AuthShell } from '@/components/auth/AuthShell'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { useAuth } from '@/hooks/useAuth'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { getDefaultRoute } from '@/lib/rbac'

export function ControlTowerLoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(false)
  const { loginControlTower } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setFieldErrors({})
    setIsLoading(true)
    try {
      const user = await loginControlTower(email, password)
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname
      navigate(from || getDefaultRoute(user), { replace: true })
    } catch (err: unknown) {
      setFieldErrors(getFieldErrors(err))
      setError(getErrorMessage(err, 'Invalid Control Tower credentials.'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      variant="control-tower"
      title="Control Tower sign in"
      description="Separate secure access for Clarisal platform operators and Django admin users."
      footer={
        <div className="flex items-center justify-between gap-4">
          <a href="/ct/reset-password" className="auth-link">
            Forgot your password?
          </a>
          <a href="/auth/login" className="font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))] hover:underline">
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
            placeholder="operator@clarisal.com"
          />
          <FieldErrorText message={fieldErrors.email} />
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
          <FieldErrorText message={fieldErrors.password} />
        </div>

        {error ? (
          <div className="notice-error">{error}</div>
        ) : null}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading ? 'Signing in...' : 'Enter Control Tower'}
        </button>
      </form>
    </AuthShell>
  )
}
