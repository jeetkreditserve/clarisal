import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-[22px] bg-[linear-gradient(110deg,rgba(217,225,236,0.6),rgba(243,247,250,0.95),rgba(217,225,236,0.6))] bg-[length:200%_100%] [animation:shimmer_1.7s_linear_infinite]',
        className
      )}
      {...props}
    />
  )
}
