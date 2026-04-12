import { Check } from 'lucide-react'

import { cn } from '@/lib/utils'

type Step = {
  id: string
  title: string
  description: string
}

interface WizardProgressProps {
  steps: Step[]
  currentStep: number
  completedSteps: number[]
  onStepSelect: (stepIndex: number) => void
}

export function WizardProgress({ steps, currentStep, completedSteps, onStepSelect }: WizardProgressProps) {
  return (
    <aside className="surface-card rounded-[30px] p-5 lg:sticky lg:top-6">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[hsl(var(--muted-foreground))]">
        Wizard progress
      </p>
      <div className="mt-5 grid gap-3">
        {steps.map((step, index) => {
          const isActive = index === currentStep
          const isComplete = completedSteps.includes(index)
          const isClickable = isComplete || index < currentStep

          return (
            <button
              key={step.id}
              type="button"
              onClick={() => isClickable && onStepSelect(index)}
              disabled={!isClickable}
              className={cn(
                'flex items-start gap-3 rounded-[22px] border px-4 py-4 text-left transition',
                isActive
                  ? 'border-[hsl(var(--brand)_/_0.4)] bg-[hsl(var(--brand)_/_0.08)]'
                  : 'border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))]',
                isClickable && 'hover:border-[hsl(var(--brand)_/_0.32)] hover:bg-[hsl(var(--surface-subtle))]',
                !isClickable && 'cursor-not-allowed opacity-70',
              )}
            >
              <span
                className={cn(
                  'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold',
                  isComplete
                    ? 'border-[hsl(var(--brand))] bg-[hsl(var(--brand))] text-[hsl(var(--brand-foreground))]'
                    : isActive
                      ? 'border-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--brand))]'
                      : 'border-[hsl(var(--border-strong))] bg-[hsl(var(--surface))] text-[hsl(var(--muted-foreground))]',
                )}
              >
                {isComplete ? <Check className="h-4 w-4" /> : index + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-[hsl(var(--foreground-strong))]">
                  Step {index + 1}: {step.title}
                </span>
                <span className="mt-1 block text-xs leading-5 text-[hsl(var(--muted-foreground))]">
                  {step.description}
                </span>
              </span>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
