import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { acceptInvite, validateInviteToken } from '@/lib/api/invitations'
import { getDefaultRoute } from '@/lib/rbac'
import { AuthShell } from '@/components/auth/AuthShell'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { Skeleton } from '@/components/ui/Skeleton'
import { useAuth } from '@/hooks/useAuth'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'

export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const [tokenValid, setTokenValid] = useState<boolean | null>(null)
  const [inviteInfo, setInviteInfo] = useState<{
    email: string
    role: string
    organisation_name: string | null
    requires_password_setup: boolean
  } | null>(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!token) return
    validateInviteToken(token)
      .then((data) => {
        setTokenValid(true)
        setInviteInfo(data)
      })
      .catch(() => setTokenValid(false))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (inviteInfo?.requires_password_setup && password !== confirmPassword) {
      setFieldErrors({ confirm_password: 'Passwords do not match.' })
      setError('Passwords do not match')
      return
    }
    if (inviteInfo?.requires_password_setup && password.length < 8) {
      setFieldErrors({ password: 'Password must be at least 8 characters.' })
      setError('Password must be at least 8 characters')
      return
    }
    setFieldErrors({})
    setError('')
    setIsLoading(true)
    try {
      const result = await acceptInvite(
        inviteInfo?.requires_password_setup
          ? { token: token!, password, confirm_password: confirmPassword }
          : { token: token! }
      )
      await refreshUser()
      navigate(getDefaultRoute(result.user), { replace: true })
    } catch (err: unknown) {
      setFieldErrors(getFieldErrors(err))
      setError(getErrorMessage(err, 'Failed to accept the invitation. The link may have expired.'))
    } finally {
      setIsLoading(false)
    }
  }

  if (tokenValid === null) {
    return (
      <AuthShell variant="setup" title="Verifying your invitation" description="Checking that your secure setup link is still valid.">
        <div className="space-y-4">
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
        </div>
      </AuthShell>
    )
  }

  if (tokenValid === false) {
    return (
      <AuthShell
        variant="setup"
        title="Invitation no longer available"
        description="This invite is invalid, already used, or has expired. Ask your administrator to send a fresh setup email."
      >
        <a href="/auth/login" className="btn-secondary w-full">
          Return to sign in
        </a>
      </AuthShell>
    )
  }

  return (
    <AuthShell
      variant="setup"
      title={inviteInfo?.requires_password_setup ? 'Set your password' : 'Accept your access'}
      description={
        inviteInfo
          ? inviteInfo.requires_password_setup
            ? `${inviteInfo.email} was invited to ${inviteInfo.organisation_name || 'Calrisal'}. Create a password to activate the account.`
            : `${inviteInfo.email} already has a workforce account. Accept access to join ${inviteInfo.organisation_name || 'Calrisal'}.`
          : 'Create a password to finish your account setup.'
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {inviteInfo?.requires_password_setup ? (
          <>
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
              <FieldErrorText message={fieldErrors.password} />
            </div>
            <div>
              <label className="field-label" htmlFor="confirmPassword">
                Confirm password
              </label>
              <input
                id="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="field-input"
                placeholder="Repeat your password"
              />
              <FieldErrorText message={fieldErrors.confirm_password} />
            </div>
          </>
        ) : (
          <div className="notice-info">
            This invitation will add the organisation access to your existing workforce account.
          </div>
        )}

        {error ? (
          <div className="notice-error">{error}</div>
        ) : null}

        <button type="submit" disabled={isLoading} className="btn-primary w-full">
          {isLoading
            ? 'Creating secure session...'
            : inviteInfo?.requires_password_setup
              ? 'Set password and continue'
              : 'Accept access and continue'}
        </button>
      </form>
    </AuthShell>
  )
}
