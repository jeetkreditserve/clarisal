import { useState } from 'react'
import { AuthShell } from '@/components/auth/AuthShell'
import { requestPasswordReset } from '@/lib/api/auth'

export function RequestPasswordResetPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await requestPasswordReset(email)
    } catch {
      // Always show success to prevent email enumeration
    } finally {
      setIsLoading(false)
      setSubmitted(true)
    }
  }

  return (
    <AuthShell
      title={submitted ? 'Check your inbox' : 'Reset your password'}
      description={
        submitted
          ? `If ${email} is registered, a password reset email has been sent.`
          : 'Enter your work email and we will send a secure password reset link.'
      }
      footer={<a href="/auth/login" className="font-medium text-[hsl(var(--primary))] hover:underline">Back to sign in</a>}
    >
      {submitted ? null : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="field-label" htmlFor="email">
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="field-input"
              placeholder="you@company.com"
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
