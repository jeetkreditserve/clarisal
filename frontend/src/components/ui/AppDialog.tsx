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
  bodyClassName?: string
  footer?: ReactNode
}

export function AppDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  contentClassName,
  bodyClassName,
  footer,
}: AppDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[hsl(var(--background)_/_0.62)] backdrop-blur-sm" />
        <Dialog.Content
          aria-describedby={description ? undefined : undefined}
          className={cn(
            'fixed inset-x-3 bottom-3 top-3 z-50 flex max-h-[calc(100svh-1.5rem)] flex-col overflow-hidden rounded-[28px] border border-[hsl(var(--border)_/_0.85)] bg-[hsl(var(--surface))] shadow-[var(--shadow-strong)] sm:left-1/2 sm:top-1/2 sm:bottom-auto sm:max-h-[min(86svh,56rem)] sm:w-[min(92vw,42rem)] sm:-translate-x-1/2 sm:-translate-y-1/2',
            contentClassName,
          )}
        >
          <div className="shrink-0 space-y-2 border-b border-[hsl(var(--border)_/_0.84)] px-5 pb-4 pt-5 sm:px-6 sm:pt-6">
            <Dialog.Title className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{title}</Dialog.Title>
            {description ? (
              <Dialog.Description className="text-sm leading-6 text-[hsl(var(--muted-foreground))]">
                {description}
              </Dialog.Description>
            ) : null}
          </div>
          <div className={cn('min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6', bodyClassName)}>{children}</div>
          {footer ? (
            <div className="shrink-0 border-t border-[hsl(var(--border)_/_0.84)] px-5 py-4 sm:px-6">
              {footer}
            </div>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
