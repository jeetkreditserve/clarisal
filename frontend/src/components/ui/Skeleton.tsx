import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-[22px] bg-[linear-gradient(110deg,var(--skeleton-base),var(--skeleton-highlight),var(--skeleton-base))] bg-[length:200%_100%] [animation:shimmer_1.7s_linear_infinite]',
        className
      )}
      {...props}
    />
  )
}

export function SkeletonMetricCard() {
  return (
    <div className="surface-card rounded-[28px] p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-10 w-24" />
        </div>
        <Skeleton className="h-12 w-12 rounded-2xl" />
      </div>
      <Skeleton className="mt-4 h-4 w-40" />
    </div>
  )
}

export function SkeletonPageHeader() {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-3">
        <Skeleton className="h-3 w-24 rounded-full" />
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-4 w-[30rem] max-w-full" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-11 w-32" />
        <Skeleton className="h-11 w-28" />
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-16" />
      ))}
    </div>
  )
}

export function SkeletonFormBlock({ rows = 6 }: { rows?: number }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-12 w-full" />
        </div>
      ))}
    </div>
  )
}
