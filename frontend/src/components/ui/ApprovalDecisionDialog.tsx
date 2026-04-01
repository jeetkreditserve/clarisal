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
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,38rem)] -translate-x-1/2 -translate-y-1/2 rounded-[28px] border border-[hsl(var(--border)_/_0.85)] bg-[hsl(var(--surface))] p-6 shadow-[var(--shadow-strong)]">
          <Dialog.Title className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{title}</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
            {description}
          </Dialog.Description>

          <form onSubmit={handleSubmit} className="mt-5 grid gap-4">
            <div>
              <label className="field-label" htmlFor="approval-comment">
                {isCommentRequired ? 'Decision note' : 'Decision note (optional)'}
              </label>
              <textarea
                id="approval-comment"
                className="field-textarea"
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder={isCommentRequired ? 'Explain why this request is being rejected.' : 'Add context for the requester or the audit trail.'}
              />
              <FieldErrorText message={localError || error} />
            </div>
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
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
