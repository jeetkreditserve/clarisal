import type { ReactNode } from 'react'

import { SectionCard } from '@/components/ui/SectionCard'

interface WizardStepProps {
  title: string
  description: string
  children: ReactNode
  onBack?: () => void
  onNext?: () => void
  nextLabel?: string
  backLabel?: string
  canProceed?: boolean
  isLoading?: boolean
  error?: string | null
  footer?: ReactNode
}

export function WizardStep({
  title,
  description,
  children,
  onBack,
  onNext,
  nextLabel = 'Next',
  backLabel = 'Back',
  canProceed = true,
  isLoading = false,
  error,
  footer,
}: WizardStepProps) {
  return (
    <SectionCard title={title} description={description}>
      <div className="space-y-6">
        {children}
        {error ? <div className="notice-error">{error}</div> : null}
        {footer ?? (
          <div className="flex flex-wrap gap-3">
            <button type="button" className="btn-secondary" onClick={onBack} disabled={!onBack || isLoading}>
              {backLabel}
            </button>
            <button type="button" className="btn-primary" onClick={onNext} disabled={!canProceed || isLoading}>
              {isLoading ? 'Saving...' : nextLabel}
            </button>
          </div>
        )}
      </div>
    </SectionCard>
  )
}
