import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Target } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { createOrgGoalCycle, fetchOrgGoalCycles } from '@/lib/api/performance'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = {
  name: '',
  start_date: '',
  end_date: '',
  auto_create_review_cycle: true,
}

function getCycleTone(status: string) {
  if (status === 'ACTIVE') return 'success'
  if (status === 'CLOSED') return 'neutral'
  return 'warning'
}

export function GoalCyclesPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(emptyForm)

  const cyclesQuery = useQuery({
    queryKey: ['performance', 'org', 'goal-cycles'],
    queryFn: fetchOrgGoalCycles,
  })

  const createMutation = useMutation({
    mutationFn: createOrgGoalCycle,
    onSuccess: () => {
      toast.success('Goal cycle created.')
      setForm(emptyForm)
      void queryClient.invalidateQueries({ queryKey: ['performance', 'org', 'goal-cycles'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to create the goal cycle.'))
    },
  })

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void createMutation.mutateAsync(form)
  }

  if (cyclesQuery.isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={5} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Performance"
        title="Goal cycles"
        description="Define quarterly or annual goal windows before managers assign and track employee goals."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <SectionCard title="New goal cycle" description="Create the cycle first. Goals can then be assigned against it from follow-up workflow screens.">
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <div>
              <label className="field-label" htmlFor="goal-cycle-name">Cycle name</label>
              <input
                id="goal-cycle-name"
                className="field-input"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Q2 2026"
                required
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="goal-cycle-start">Start date</label>
                <input
                  id="goal-cycle-start"
                  className="field-input"
                  type="date"
                  value={form.start_date}
                  onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="goal-cycle-end">End date</label>
                <input
                  id="goal-cycle-end"
                  className="field-input"
                  type="date"
                  value={form.end_date}
                  onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))}
                  required
                />
              </div>
            </div>
            <label className="flex items-start gap-3 rounded-[18px] border border-[hsl(var(--border)_/_0.85)] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
              <input
                className="mt-1 h-4 w-4"
                type="checkbox"
                checked={form.auto_create_review_cycle}
                onChange={(event) => setForm((current) => ({ ...current, auto_create_review_cycle: event.target.checked }))}
              />
              <span>
                Auto-create a review cycle when this goal cycle ends.
              </span>
            </label>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create goal cycle'}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Existing cycles" description="Draft cycles are ready for goal setup. Activation and closeout can be added once the appraisal workflow expands.">
          {!cyclesQuery.data?.length ? (
            <EmptyState
              icon={Target}
              title="No goal cycles yet"
              description="Create the first cycle to start structuring performance goals."
            />
          ) : (
            <div className="space-y-3">
              {cyclesQuery.data.map((cycle) => (
                <div key={cycle.id} className="surface-muted rounded-[22px] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{cycle.name}</p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        {cycle.start_date} to {cycle.end_date}
                      </p>
                      {cycle.auto_create_review_cycle ? (
                        <p className="mt-2 text-xs font-medium uppercase tracking-[0.16em] text-[hsl(var(--brand))]">
                          Review cycle auto-trigger enabled
                        </p>
                      ) : null}
                    </div>
                    <StatusBadge tone={getCycleTone(cycle.status)}>{cycle.status}</StatusBadge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
