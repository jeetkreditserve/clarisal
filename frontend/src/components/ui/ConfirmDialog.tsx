import {
  cloneElement,
  isValidElement,
  useMemo,
  useState,
  type MouseEvent,
  type ReactElement,
  type ReactNode,
} from 'react'

import { AppDialog } from '@/components/ui/AppDialog'

interface ConfirmDialogProps {
  trigger: ReactNode
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'primary'
  onConfirm: () => void | Promise<void>
}

interface TriggerElementProps {
  onClick?: (event: MouseEvent<HTMLElement>) => void
}

export function ConfirmDialog({
  trigger,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  onConfirm,
}: ConfirmDialogProps) {
  const [open, setOpen] = useState(false)
  const [isPending, setIsPending] = useState(false)

  const handleConfirm = async () => {
    setIsPending(true)
    try {
      await onConfirm()
      setOpen(false)
    } finally {
      setIsPending(false)
    }
  }

  const triggerNode = useMemo(() => {
    if (!isValidElement<TriggerElementProps>(trigger)) {
      return (
        <button type="button" className="btn-secondary" onClick={() => setOpen(true)}>
          {trigger}
        </button>
      )
    }

    const element = trigger as ReactElement<TriggerElementProps>
    return cloneElement(element, {
      onClick: (event: MouseEvent<HTMLElement>) => {
        element.props.onClick?.(event)
        if (!event.defaultPrevented) {
          setOpen(true)
        }
      },
    })
  }, [trigger])

  return (
    <>
      {triggerNode}
      <AppDialog
        open={open}
        onOpenChange={setOpen}
        title={title}
        description={description}
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)} disabled={isPending}>
              {cancelLabel}
            </button>
            <button
              type="button"
              className={variant === 'danger' ? 'btn-danger' : 'btn-primary'}
              onClick={() => void handleConfirm()}
              disabled={isPending}
              aria-label={confirmLabel}
            >
              {isPending ? 'Processing...' : confirmLabel}
            </button>
          </div>
        }
      >
        {description ? null : (
          <p className="text-sm leading-6 text-[hsl(var(--muted-foreground))]">
            Confirm this action to continue.
          </p>
        )}
      </AppDialog>
    </>
  )
}
