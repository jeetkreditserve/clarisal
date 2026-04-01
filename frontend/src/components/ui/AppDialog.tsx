import type { ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'

import { cn } from '@/lib/utils'

interface AppDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children: ReactNode
  contentClassName?: string
}

export function AppDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  contentClassName,
}: AppDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[hsl(var(--background)_/_0.62)] backdrop-blur-sm" />
        <Dialog.Content
          className={cn(
            'fixed inset-x-3 bottom-3 top-3 z-50 overflow-y-auto rounded-[28px] border border-[hsl(var(--border)_/_0.85)] bg-[hsl(var(--surface))] p-5 shadow-[var(--shadow-strong)] sm:left-1/2 sm:top-1/2 sm:bottom-auto sm:w-[min(92vw,42rem)] sm:-translate-x-1/2 sm:-translate-y-1/2 sm:p-6',
            contentClassName,
          )}
        >
          <div className="space-y-2 border-b border-[hsl(var(--border)_/_0.84)] pb-4">
            <Dialog.Title className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{title}</Dialog.Title>
            {description ? (
              <Dialog.Description className="text-sm leading-6 text-[hsl(var(--muted-foreground))]">
                {description}
              </Dialog.Description>
            ) : null}
          </div>
          <div className="pt-5">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
