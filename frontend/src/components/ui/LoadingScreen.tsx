import { Skeleton } from '@/components/ui/Skeleton'

interface LoadingScreenProps {
  message?: string
}

export function LoadingScreen({ message = 'Preparing your workspace' }: LoadingScreenProps) {
  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="surface-card grid w-full max-w-5xl gap-8 rounded-[36px] p-8 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div className="space-y-4 rounded-[28px] bg-[linear-gradient(180deg,rgba(13,25,41,0.98),rgba(20,42,66,0.95))] p-6 text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">Calrisal</p>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Loading platform context</h1>
            <p className="mt-2 text-sm leading-6 text-slate-300">{message}</p>
          </div>
          <Skeleton className="h-10 rounded-2xl bg-white/10" />
          <Skeleton className="h-10 rounded-2xl bg-white/10" />
          <Skeleton className="h-10 rounded-2xl bg-white/10" />
        </div>
        <div className="space-y-5">
          <Skeleton className="h-12 w-72" />
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
          <Skeleton className="h-80" />
        </div>
      </div>
    </div>
  )
}
