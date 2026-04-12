import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  activateOrgAppraisalCycle,
  advanceOrgAppraisalCycle,
  createOrgAppraisalCycle,
  fetchOrgAppraisalCycles,
  fetchOrgGoalCycles,
} from '@/lib/api/performance'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = {
  name: '',
  review_type: '360',
  goal_cycle_id: '',
  start_date: '',
  end_date: '',
  self_assessment_deadline: '',
  peer_review_deadline: '',
  manager_review_deadline: '',
  calibration_deadline: '',
}

function getCycleTone(status: string) {
  if (status === 'COMPLETED' || status === 'CLOSED') return 'neutral'
  if (status === 'CALIBRATION') return 'info'
  if (status === 'MANAGER_REVIEW' || status === 'PEER_REVIEW' || status === 'SELF_ASSESSMENT') return 'success'
  if (status === 'ACTIVE') return 'success'
  return 'warning'
}

function formatPhaseLabel(status: string) {
  return status.replace(/_/g, ' ')
}

function formatCompletionLine(cycle: Awaited<ReturnType<typeof fetchOrgAppraisalCycles>>[number]) {
  const stats = cycle.completion_stats
  return `${stats.self_submitted}/${stats.self_total} self • ${stats.manager_submitted}/${stats.manager_total} manager • ${stats.feedback_submitted}/${stats.feedback_total} feedback`
}

export function AppraisalCyclesPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(emptyForm)

  const goalCyclesQuery = useQuery({
    queryKey: ['performance', 'org', 'goal-cycles'],
    queryFn: fetchOrgGoalCycles,
  })
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

  const activateMutation = useMutation({
    mutationFn: activateOrgAppraisalCycle,
    onSuccess: () => {
      toast.success('Appraisal cycle activated.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'org', 'appraisal-cycles'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to activate the appraisal cycle.'))
    },
  })

  const advanceMutation = useMutation({
    mutationFn: advanceOrgAppraisalCycle,
    onSuccess: () => {
      toast.success('Appraisal cycle advanced.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'org', 'appraisal-cycles'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to advance the appraisal cycle.'))
    },
  })

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void createMutation.mutateAsync({
      ...form,
      goal_cycle_id: form.goal_cycle_id || null,
      self_assessment_deadline: form.self_assessment_deadline || null,
      peer_review_deadline: form.peer_review_deadline || null,
      manager_review_deadline: form.manager_review_deadline || null,
      calibration_deadline: form.calibration_deadline || null,
    })
  }

  if (cyclesQuery.isLoading || goalCyclesQuery.isLoading) {
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
        description="Build review windows from goal cycles, move them through each performance phase, and hand off calibration once manager ratings are in."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <SectionCard title="New appraisal cycle" description="Create the review cycle with all phase deadlines up front so the daily automation and admin controls stay aligned.">
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
              <label className="field-label" htmlFor="appraisal-cycle-goal-cycle">Linked goal cycle</label>
              <select
                id="appraisal-cycle-goal-cycle"
                className="field-input"
                value={form.goal_cycle_id}
                onChange={(event) => setForm((current) => ({ ...current, goal_cycle_id: event.target.value }))}
              >
                <option value="">No linked goal cycle</option>
                {goalCyclesQuery.data?.map((cycle) => (
                  <option key={cycle.id} value={cycle.id}>
                    {cycle.name}
                  </option>
                ))}
              </select>
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
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="self-assessment-deadline">Self-assessment deadline</label>
                <input
                  id="self-assessment-deadline"
                  className="field-input"
                  type="date"
                  value={form.self_assessment_deadline}
                  onChange={(event) => setForm((current) => ({ ...current, self_assessment_deadline: event.target.value }))}
                />
              </div>
              <div>
                <label className="field-label" htmlFor="peer-review-deadline">Peer-review deadline</label>
                <input
                  id="peer-review-deadline"
                  className="field-input"
                  type="date"
                  value={form.peer_review_deadline}
                  onChange={(event) => setForm((current) => ({ ...current, peer_review_deadline: event.target.value }))}
                />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="manager-review-deadline">Manager-review deadline</label>
                <input
                  id="manager-review-deadline"
                  className="field-input"
                  type="date"
                  value={form.manager_review_deadline}
                  onChange={(event) => setForm((current) => ({ ...current, manager_review_deadline: event.target.value }))}
                />
              </div>
              <div>
                <label className="field-label" htmlFor="calibration-deadline">Calibration deadline</label>
                <input
                  id="calibration-deadline"
                  className="field-input"
                  type="date"
                  value={form.calibration_deadline}
                  onChange={(event) => setForm((current) => ({ ...current, calibration_deadline: event.target.value }))}
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create appraisal cycle'}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Existing appraisal cycles" description="Activate drafts, advance due phases, and enter calibration once manager reviews are complete.">
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
                  <div className="flex flex-col gap-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{cycle.name}</p>
                        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                          {cycle.review_type} • {cycle.start_date} to {cycle.end_date}
                        </p>
                        <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                          {formatCompletionLine(cycle)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {cycle.is_probation_review ? <StatusBadge tone="info">Probation</StatusBadge> : null}
                        <StatusBadge tone={getCycleTone(cycle.status)}>{formatPhaseLabel(cycle.status)}</StatusBadge>
                      </div>
                    </div>

                    <div className="grid gap-2 text-sm text-[hsl(var(--muted-foreground))] md:grid-cols-2">
                      <p>Self: {cycle.self_assessment_deadline || 'Not set'}</p>
                      <p>Peer: {cycle.peer_review_deadline || 'Not set'}</p>
                      <p>Manager: {cycle.manager_review_deadline || 'Not set'}</p>
                      <p>Calibration: {cycle.calibration_deadline || 'Not set'}</p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {cycle.status === 'DRAFT' ? (
                        <button
                          type="button"
                          className="btn-primary"
                          onClick={() => void activateMutation.mutateAsync(cycle.id)}
                          disabled={activateMutation.isPending}
                        >
                          Activate cycle
                        </button>
                      ) : null}
                      {['ACTIVE', 'SELF_ASSESSMENT', 'PEER_REVIEW', 'MANAGER_REVIEW'].includes(cycle.status) ? (
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => void advanceMutation.mutateAsync(cycle.id)}
                          disabled={advanceMutation.isPending}
                        >
                          Advance phase
                        </button>
                      ) : null}
                      {cycle.status === 'CALIBRATION' ? (
                        <Link className="btn-primary" to={`/org/performance/appraisals/${cycle.id}/calibration`}>
                          Open calibration
                        </Link>
                      ) : null}
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
