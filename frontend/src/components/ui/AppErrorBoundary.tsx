import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface AppErrorBoundaryProps {
  children: ReactNode
}

interface AppErrorBoundaryState {
  hasError: boolean
}

function ErrorFallback() {
  const pathname = window.location.pathname
  const isAuthSurface =
    pathname.startsWith('/auth') ||
    pathname === '/ct/login' ||
    pathname.startsWith('/ct/reset-password')
  const fallbackHref = pathname.startsWith('/ct') && !isAuthSurface ? '/ct/dashboard' : isAuthSurface ? '/auth/login' : '/me/dashboard'
  const fallbackLabel = pathname.startsWith('/ct') && !isAuthSurface ? 'Go to Control Tower' : isAuthSurface ? 'Go to login' : 'Go to dashboard'

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="surface-card max-w-xl rounded-[32px] p-8 text-center shadow-[var(--shadow-strong)]">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[hsl(var(--warning)_/_0.16)] text-[hsl(var(--warning))]">
          <AlertTriangle className="h-7 w-7" />
        </div>
        <h1 className="mt-5 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">This page hit an unexpected problem.</h1>
        <p className="mt-3 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
          The application is still running, but this screen failed to render. Reload the page or move back to a stable workspace.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
            Reload page
          </button>
          <a className="btn-secondary" href={fallbackHref}>
            {fallbackLabel}
          </a>
        </div>
      </div>
    </div>
  )
}

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Frontend render error', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />
    }

    return this.props.children
  }
}
