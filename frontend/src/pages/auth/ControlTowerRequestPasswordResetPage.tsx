import { useState } from 'react'

import { AuthShell } from '@/components/auth/AuthShell'
import { requestControlTowerPasswordReset } from '@/lib/api/auth'

export function ControlTowerRequestPasswordResetPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setIsLoading(true)
    try {
      await requestControlTowerPasswordReset(email)
    } catch {
      // Always show success to prevent email enumeration.
    } finally {
      setIsLoading(false)
      setSubmitted(true)
    }
  }

  return (
    <AuthShell
      variant="control-tower"
      title={submitted ? 'Check your inbox' : 'Reset Control Tower password'}
      description={
        submitted
          ? `If ${email} is registered for Control Tower, a password reset email has been sent.`
          : 'Enter your Control Tower email and we will send a secure password reset link.'
      }
      footer={<a href="/ct/login" className="auth-link">Back to Control Tower sign in</a>}
    >
      {submitted ? null : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="field-label" htmlFor="ct-reset-email">
              Control Tower email
            </label>
            <input
              id="ct-reset-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="field-input"
              placeholder="operator@clarisal.com"
            />
          </div>
          <button type="submit" disabled={isLoading} className="btn-primary w-full">
            {isLoading ? 'Sending reset email...' : 'Send reset link'}
          </button>
        </form>
      )}
    </AuthShell>
  )
}
