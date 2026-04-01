import { useNavigate } from 'react-router-dom'

import { useOrgSetup, useUpdateOrgSetup } from '@/hooks/useOrgAdmin'
import { getNextOrgSetupStep, getOrgSetupRoute, getPreviousOrgSetupStep } from '@/lib/orgSetup'

export function OrgSetupBanner() {
  const navigate = useNavigate()
  const { data: setup } = useOrgSetup()
  const updateSetup = useUpdateOrgSetup()

  if (!setup?.required) {
    return null
  }

  const previousStep = getPreviousOrgSetupStep(setup)
  const nextStep = getNextOrgSetupStep(setup)
  const currentStep = setup.steps.find((step) => step.key === setup.current_step)

  const handleMove = async (step: typeof setup.current_step | null) => {
    if (!step) return
    await updateSetup.mutateAsync({ current_step: step })
    navigate(getOrgSetupRoute(step))
  }

  return (
    <div className="mb-6 rounded-[26px] border border-[hsl(var(--brand)_/_0.24)] bg-[hsl(var(--brand)_/_0.08)] px-5 py-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[hsl(var(--brand))]">
            Guided setup
          </p>
          <h2 className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
            Step {setup.current_step_index} of {setup.total_steps}: {currentStep?.label}
          </h2>
          <p className="mt-2 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
            Finish the first-time organisation setup to unlock the normal dashboard experience. You can move forward,
            go back, or skip a step and return later.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="btn-secondary" disabled={!previousStep || updateSetup.isPending} onClick={() => void handleMove(previousStep)}>
            Previous
          </button>
          {nextStep ? (
            <button type="button" className="btn-secondary" disabled={updateSetup.isPending} onClick={() => void handleMove(nextStep)}>
              Skip
            </button>
          ) : (
            <button
              type="button"
              className="btn-secondary"
              disabled={updateSetup.isPending}
              onClick={async () => {
                await updateSetup.mutateAsync({ completed: true })
                navigate('/org/dashboard')
              }}
            >
              Finish for now
            </button>
          )}
          {nextStep ? (
            <button type="button" className="btn-primary" disabled={updateSetup.isPending} onClick={() => void handleMove(nextStep)}>
              Next
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary"
              disabled={updateSetup.isPending}
              onClick={async () => {
                await updateSetup.mutateAsync({ completed: true })
                navigate('/org/dashboard')
              }}
            >
              Complete setup
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
