import { useState } from 'react'
import api from '@/lib/api'
import { cn } from '@/lib/utils'

export function RequestPasswordResetPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await api.post('/auth/password-reset/request/', { email })
    } catch {
      // Always show success to prevent email enumeration
    } finally {
      setIsLoading(false)
      setSubmitted(true)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-tight">Calrisal</h1>
        </div>
        <div className="rounded-xl bg-white p-8 shadow-2xl">
          {submitted ? (
            <div className="text-center">
              <h2 className="text-xl font-semibold text-foreground">Check your email</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                If an account with <strong>{email}</strong> exists, we've sent a password reset link. Check your inbox.
              </p>
              <a href="/auth/login" className="mt-4 block text-sm text-primary hover:underline">
                Back to sign in
              </a>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-foreground">Reset your password</h2>
              <p className="mt-1 text-sm text-muted-foreground">Enter your email and we'll send a reset link.</p>
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Email address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    placeholder="you@company.com"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className={cn(
                    'w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                    'transition-opacity hover:opacity-90',
                    isLoading && 'opacity-60 cursor-not-allowed'
                  )}
                >
                  {isLoading ? 'Sending…' : 'Send reset link'}
                </button>
              </form>
              <div className="mt-4 text-center">
                <a href="/auth/login" className="text-sm text-muted-foreground hover:text-foreground">
                  Back to sign in
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
