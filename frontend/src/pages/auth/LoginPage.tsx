import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { getDefaultRoute } from '@/lib/rbac'
import { getErrorMessage } from '@/lib/errors'
import { AuthShell } from '@/components/auth/AuthShell'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      const user = await login(email, password)
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname
      navigate(from || getDefaultRoute(user), { replace: true })
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Invalid email or password.'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title="Sign in to your workplace"
      description="Default sign-in for organisation admins and employees. Access your collated admin workspace or employee self-service."
      footer={
        <div className="flex items-center justify-between gap-4">
          <a href="/auth/reset-password" className="font-medium text-[hsl(var(--primary))] hover:underline">
            Forgot your password?
          </a>
          <a href="/ct/login" className="font-medium text-slate-500 hover:text-slate-900 hover:underline">
            Control Tower login
          </a>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="email" className="field-label">
            Email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="field-input"
            placeholder="you@company.com"
          />
        </div>
        <div>
          <label htmlFor="password" className="field-label">
            Password
          </label>
          <input
            id="password"
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
          {isLoading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </AuthShell>
  )
}
