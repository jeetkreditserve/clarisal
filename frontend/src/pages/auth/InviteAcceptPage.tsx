import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { acceptInvite, validateInviteToken } from '@/lib/api/invitations'
import { getDefaultRoute } from '@/lib/rbac'
import { getErrorMessage } from '@/lib/errors'
import { AuthShell } from '@/components/auth/AuthShell'
import { useAuth } from '@/hooks/useAuth'

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
      setError('Passwords do not match')
      return
    }
    if (inviteInfo?.requires_password_setup && password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
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
      setError(getErrorMessage(err, 'Failed to accept the invitation. The link may have expired.'))
    } finally {
      setIsLoading(false)
    }
  }

  if (tokenValid === null) {
    return <AuthShell title="Verifying your invitation" description="Checking that your secure setup link is still valid."><div className="space-y-4"><div className="h-14 rounded-[20px] bg-slate-100" /><div className="h-14 rounded-[20px] bg-slate-100" /><div className="h-14 rounded-[20px] bg-slate-100" /></div></AuthShell>
  }

  if (tokenValid === false) {
    return (
      <AuthShell
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
            </div>
          </>
        ) : (
          <div className="rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            This invitation will add the organisation access to your existing workforce account.
          </div>
        )}

        {error ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
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
