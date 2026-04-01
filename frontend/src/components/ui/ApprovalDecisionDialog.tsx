import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'

import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { getErrorMessage } from '@/lib/errors'

interface ApprovalDecisionDialogProps {
  actionLabel: string
  triggerClassName: string
  triggerLabel: string
  title: string
  description: string
  confirmLabel: string
  confirmTone?: 'primary' | 'danger'
  defaultComment?: string
  isCommentRequired?: boolean
  isPending?: boolean
  error?: string
  submitErrorFallback?: string
  onSubmit: (comment: string) => Promise<unknown> | unknown
}

export function ApprovalDecisionDialog({
  actionLabel,
  triggerClassName,
  triggerLabel,
  title,
  description,
  confirmLabel,
  confirmTone = 'primary',
  defaultComment = '',
  isCommentRequired = false,
  isPending = false,
  error,
  submitErrorFallback = 'Unable to record this decision.',
  onSubmit,
}: ApprovalDecisionDialogProps) {
  const [open, setOpen] = useState(false)
  const [comment, setComment] = useState(defaultComment)
  const [localError, setLocalError] = useState('')

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (isCommentRequired && !comment.trim()) {
      setLocalError('A rejection note is required.')
      return
    }
    setLocalError('')
    try {
      await onSubmit(comment.trim())
      setOpen(false)
    } catch (submitError) {
      setLocalError(getErrorMessage(submitError, submitErrorFallback))
    }
  }

  const confirmClassName = confirmTone === 'danger' ? 'btn-danger' : 'btn-primary'
  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (!nextOpen) {
      setComment(defaultComment)
      setLocalError('')
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={handleOpenChange}>
      <Dialog.Trigger asChild>
        <button type="button" className={triggerClassName} aria-label={actionLabel}>
          {triggerLabel}
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[hsl(var(--background)_/_0.62)] backdrop-blur-sm" />
        <Dialog.Content className="fixed inset-x-3 bottom-3 top-3 z-50 flex max-h-[calc(100svh-1.5rem)] flex-col overflow-hidden rounded-[28px] border border-[hsl(var(--border)_/_0.85)] bg-[hsl(var(--surface))] shadow-[var(--shadow-strong)] sm:left-1/2 sm:top-1/2 sm:bottom-auto sm:max-h-[min(80svh,32rem)] sm:w-[min(92vw,38rem)] sm:-translate-x-1/2 sm:-translate-y-1/2">
          <div className="shrink-0 border-b border-[hsl(var(--border)_/_0.84)] px-5 pb-4 pt-5 sm:px-6 sm:pt-6">
            <Dialog.Title className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{title}</Dialog.Title>
            <Dialog.Description className="mt-2 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
              {description}
            </Dialog.Description>
          </div>

          <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
              <div>
                <label className="field-label" htmlFor="approval-comment">
                  {isCommentRequired ? 'Decision note' : 'Decision note (optional)'}
                </label>
                <textarea
                  id="approval-comment"
                  className="field-textarea min-h-[9rem]"
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  placeholder={isCommentRequired ? 'Explain why this request is being rejected.' : 'Add context for the requester or the audit trail.'}
                />
                <FieldErrorText message={localError || error} />
              </div>
            </div>
            <div className="shrink-0 border-t border-[hsl(var(--border)_/_0.84)] px-5 py-4 sm:px-6">
              <div className="flex flex-wrap justify-end gap-3">
                <Dialog.Close asChild>
                  <button type="button" className="btn-secondary" disabled={isPending}>
                    Cancel
                  </button>
                </Dialog.Close>
                <button type="submit" className={confirmClassName} disabled={isPending}>
                  {isPending ? 'Saving...' : confirmLabel}
                </button>
              </div>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
