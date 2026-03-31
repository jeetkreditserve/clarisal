import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { AuthShell } from '@/components/auth/AuthShell'
import { confirmPasswordReset, validatePasswordResetToken } from '@/lib/api/auth'
import { getErrorMessage } from '@/lib/errors'
import { getDefaultRoute } from '@/lib/rbac'
import { useAuth } from '@/hooks/useAuth'

export function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { refreshUser } = useAuth()
  const [email, setEmail] = useState<string | null>(null)
  const [accountType, setAccountType] = useState<string | null>(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      setError('Password reset link is missing.')
      return
    }

    validatePasswordResetToken(token)
      .then((data) => {
        setEmail(data.email)
        setAccountType(data.account_type)
      })
      .catch((validationError) => setError(getErrorMessage(validationError, 'Password reset link is invalid or expired.')))
      .finally(() => setIsLoading(false))
  }, [token])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!token) return

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    setError('')
    try {
      const result = await confirmPasswordReset({
        token,
        password,
        confirm_password: confirmPassword,
      })
      await refreshUser()
      navigate(getDefaultRoute(result.user), { replace: true })
    } catch (submitError) {
      setError(getErrorMessage(submitError, 'Unable to reset password.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <AuthShell title="Validating reset link" description="Checking your secure password reset request.">
        <div className="space-y-4">
          <div className="h-14 rounded-[20px] bg-slate-100" />
          <div className="h-14 rounded-[20px] bg-slate-100" />
          <div className="h-14 rounded-[20px] bg-slate-100" />
        </div>
      </AuthShell>
    )
  }

  if (!email) {
    const backLink = location.pathname.startsWith('/ct/') ? '/ct/login' : '/auth/login'
    const requestLink = location.pathname.startsWith('/ct/') ? '/ct/reset-password' : '/auth/reset-password'
    return (
      <AuthShell
        title="Reset link unavailable"
        description={error || 'The reset link is invalid, expired, or already used.'}
        footer={<a href={requestLink} className="font-medium text-[hsl(var(--primary))] hover:underline">Request a new reset link</a>}
      >
        <a href={backLink} className="btn-secondary w-full">
          Return to sign in
        </a>
      </AuthShell>
    )
  }

  const backLink = accountType === 'CONTROL_TOWER' ? '/ct/login' : '/auth/login'

  return (
    <AuthShell
      title="Create a new password"
      description={`Resetting access for ${email}. Set a strong password to continue.`}
      footer={<a href={backLink} className="font-medium text-[hsl(var(--primary))] hover:underline">Back to sign in</a>}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="field-label" htmlFor="password">
            New password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="field-input"
            placeholder="Minimum 8 characters"
          />
        </div>
        <div>
          <label className="field-label" htmlFor="confirm-password">
            Confirm password
          </label>
          <input
            id="confirm-password"
            type="password"
            required
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="field-input"
            placeholder="Repeat your password"
          />
        </div>

        {error ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
        ) : null}

        <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
          {isSubmitting ? 'Updating password...' : 'Reset password'}
        </button>
      </form>
    </AuthShell>
  )
}
