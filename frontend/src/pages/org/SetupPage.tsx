import { useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useOrgSetup, useUpdateOrgSetup } from '@/hooks/useOrgAdmin'
import { getOrgSetupRoute } from '@/lib/orgSetup'

export function OrgSetupPage() {
  const navigate = useNavigate()
  const { data: setup, isLoading } = useOrgSetup()
  const updateSetup = useUpdateOrgSetup()

  if (isLoading || !setup) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={5} />
      </div>
    )
  }

  const currentStep = setup.steps.find((step) => step.key === setup.current_step) ?? setup.steps[0]

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Guided setup"
        title="Set up this organisation workspace"
        description="This guided flow walks the first organisation admin through the core masters and configuration needed before everyday use."
        actions={
          <button
            type="button"
            className="btn-primary"
            onClick={async () => {
              await updateSetup.mutateAsync({ current_step: currentStep.key })
              navigate(getOrgSetupRoute(currentStep.key))
            }}
          >
            {setup.started_at ? 'Resume current step' : 'Start setup'}
          </button>
        }
      />

      <SectionCard
        title={`Step ${setup.current_step_index} of ${setup.total_steps}`}
        description="You can move step by step, go back, or skip sections and return later. The dashboard becomes the default landing page once setup is completed."
      >
        <div className="grid gap-4">
          {setup.steps.map((step) => (
            <div
              key={step.key}
              className="surface-muted flex flex-col gap-3 rounded-[24px] p-5 lg:flex-row lg:items-center lg:justify-between"
            >
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                  Step {step.sequence}
                </p>
                <p className="mt-2 text-base font-semibold text-[hsl(var(--foreground-strong))]">{step.label}</p>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                  {step.is_complete ? 'Configured already.' : 'Still pending in this organisation.'}
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  className={step.key === setup.current_step ? 'btn-primary' : 'btn-secondary'}
                  onClick={async () => {
                    await updateSetup.mutateAsync({ current_step: step.key })
                    navigate(getOrgSetupRoute(step.key))
                  }}
                >
                  {step.key === setup.current_step ? 'Open current step' : 'Open step'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
