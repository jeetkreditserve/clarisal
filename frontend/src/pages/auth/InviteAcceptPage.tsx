import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '@/lib/api'
import { cn } from '@/lib/utils'

export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [tokenValid, setTokenValid] = useState<boolean | null>(null)
  const [inviteInfo, setInviteInfo] = useState<{ email: string; role: string } | null>(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!token) return
    api.get(`/auth/invite/validate/${token}/`)
      .then((res) => {
        setTokenValid(true)
        setInviteInfo(res.data)
      })
      .catch(() => setTokenValid(false))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setError('')
    setIsLoading(true)
    try {
      await api.post('/auth/invite/accept/', { token, password, confirm_password: confirmPassword })
      navigate('/auth/login', { state: { message: 'Password set successfully. Please sign in.' } })
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: string } } }
      setError(axiosError.response?.data?.error || 'Failed to set password. The link may have expired.')
    } finally {
      setIsLoading(false)
    }
  }

  if (tokenValid === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-white border-t-transparent" />
      </div>
    )
  }

  if (tokenValid === false) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-2xl">
          <h2 className="text-xl font-semibold text-foreground">Invitation Expired</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            This invitation link is invalid or has expired. Please contact your administrator to resend the invite.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-tight">Calrisal</h1>
          <p className="mt-2 text-sm text-white/60">Set up your account</p>
        </div>
        <div className="rounded-xl bg-white p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-foreground">Create your password</h2>
          {inviteInfo && (
            <p className="mt-1 text-sm text-muted-foreground">
              Setting up account for <strong>{inviteInfo.email}</strong>
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">New password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Minimum 8 characters"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Confirm password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Repeat your password"
              />
            </div>

            {error && (
              <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                'transition-opacity hover:opacity-90',
                isLoading && 'opacity-60 cursor-not-allowed'
              )}
            >
              {isLoading ? 'Setting password…' : 'Set password & sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
