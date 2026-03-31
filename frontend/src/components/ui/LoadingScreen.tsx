import { motion } from 'motion/react'
import { Skeleton } from '@/components/ui/Skeleton'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

interface LoadingScreenProps {
  message?: string
}

export function LoadingScreen({ message = 'Preparing your workspace' }: LoadingScreenProps) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,hsl(var(--brand)_/_0.14),transparent_26%),radial-gradient(circle_at_bottom_right,hsl(var(--accent)_/_0.12),transparent_22%)]" />
      <div className="absolute right-6 top-6 z-20">
        <ThemeToggle />
      </div>
      <motion.div
        initial={{ opacity: 0, y: 22 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, ease: 'easeOut' }}
        className="surface-card grid w-full max-w-6xl gap-8 rounded-[36px] p-8 lg:grid-cols-[320px_minmax(0,1fr)]"
      >
        <div className="sidebar-surface space-y-4 rounded-[30px] p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[hsl(var(--sidebar-muted))]">Calrisal</p>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Loading platform context</h1>
            <p className="mt-2 text-sm leading-6 text-[hsl(var(--sidebar-muted))]">{message}</p>
          </div>
          <Skeleton className="h-10 rounded-2xl opacity-80" />
          <Skeleton className="h-10 rounded-2xl opacity-75" />
          <Skeleton className="h-10 rounded-2xl opacity-70" />
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
      </motion.div>
    </div>
  )
}
