import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardCheck } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { createOrgAppraisalCycle, fetchOrgAppraisalCycles } from '@/lib/api/performance'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = {
  name: '',
  review_type: 'SELF',
  start_date: '',
  end_date: '',
}

function getCycleTone(status: string) {
  if (status === 'ACTIVE') return 'success'
  if (status === 'CLOSED') return 'neutral'
  return 'warning'
}

export function AppraisalCyclesPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(emptyForm)

  const cyclesQuery = useQuery({
    queryKey: ['performance', 'org', 'appraisal-cycles'],
    queryFn: fetchOrgAppraisalCycles,
  })

  const createMutation = useMutation({
    mutationFn: createOrgAppraisalCycle,
    onSuccess: () => {
      toast.success('Appraisal cycle created.')
      setForm(emptyForm)
      void queryClient.invalidateQueries({ queryKey: ['performance', 'org', 'appraisal-cycles'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to create the appraisal cycle.'))
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
        title="Appraisal cycles"
        description="Create self, manager, or 360 review windows and track which cycles are probation-specific."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <SectionCard title="New appraisal cycle" description="Use one cycle per review window. Probation cycles are auto-created by the scheduler when applicable.">
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <div>
              <label className="field-label" htmlFor="appraisal-cycle-name">Cycle name</label>
              <input
                id="appraisal-cycle-name"
                className="field-input"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="FY 2026 Appraisal"
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="appraisal-cycle-review-type">Review type</label>
              <select
                id="appraisal-cycle-review-type"
                className="field-input"
                value={form.review_type}
                onChange={(event) => setForm((current) => ({ ...current, review_type: event.target.value }))}
              >
                <option value="SELF">Self Review</option>
                <option value="MANAGER">Manager Review</option>
                <option value="360">360 Review</option>
              </select>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="appraisal-cycle-start">Start date</label>
                <input
                  id="appraisal-cycle-start"
                  className="field-input"
                  type="date"
                  value={form.start_date}
                  onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="appraisal-cycle-end">End date</label>
                <input
                  id="appraisal-cycle-end"
                  className="field-input"
                  type="date"
                  value={form.end_date}
                  onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))}
                  required
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create appraisal cycle'}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Existing appraisal cycles" description="These cycles feed review assignment and employee self-service review submission.">
          {!cyclesQuery.data?.length ? (
            <EmptyState
              icon={ClipboardCheck}
              title="No appraisal cycles yet"
              description="Create the first cycle to open reviews for managers and employees."
            />
          ) : (
            <div className="space-y-3">
              {cyclesQuery.data.map((cycle) => (
                <div key={cycle.id} className="surface-muted rounded-[22px] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{cycle.name}</p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        {cycle.review_type} • {cycle.start_date} to {cycle.end_date}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {cycle.is_probation_review ? <StatusBadge tone="info">Probation</StatusBadge> : null}
                      <StatusBadge tone={getCycleTone(cycle.status)}>{cycle.status}</StatusBadge>
                    </div>
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
