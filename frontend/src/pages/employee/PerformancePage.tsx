import { useMemo, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardCheck, MessageSquareMore, Target } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  fetchMyFeedbackSummary,
  fetchMyGoals,
  fetchMyReviewCycles,
  fetchMyReviews,
  saveMySelfAssessment,
  submitMySelfAssessment,
  updateMyGoalProgress,
} from '@/lib/api/performance'
import { getErrorMessage } from '@/lib/errors'

function getGoalTone(status: string) {
  if (status === 'COMPLETED') return 'success'
  if (status === 'IN_PROGRESS') return 'info'
  return 'warning'
}

function getReviewTone(status: string) {
  if (status === 'SUBMITTED') return 'success'
  if (status === 'IN_PROGRESS') return 'info'
  if (status === 'COMPLETED') return 'neutral'
  return 'warning'
}

function getOverallRating(review: { ratings: Record<string, number> } | null) {
  if (!review) return ''
  if (typeof review.ratings.overall === 'number') return String(review.ratings.overall)
  const numericValue = Object.values(review.ratings).find((value) => typeof value === 'number')
  return typeof numericValue === 'number' ? String(numericValue) : ''
}

export function PerformancePage() {
  const queryClient = useQueryClient()
  const [progressDrafts, setProgressDrafts] = useState<Record<string, string>>({})
  const [reviewComments, setReviewComments] = useState<Record<string, string>>({})
  const [reviewRatings, setReviewRatings] = useState<Record<string, string>>({})

  const goalsQuery = useQuery({
    queryKey: ['performance', 'me', 'goals'],
    queryFn: fetchMyGoals,
  })
  const reviewCyclesQuery = useQuery({
    queryKey: ['performance', 'me', 'review-cycles'],
    queryFn: fetchMyReviewCycles,
  })
  const historicalReviewsQuery = useQuery({
    queryKey: ['performance', 'me', 'reviews'],
    queryFn: fetchMyReviews,
  })

  const feedbackSummaryQueries = useQueries({
    queries: (reviewCyclesQuery.data ?? [])
      .filter((cycle) => cycle.feedback_summary_visible)
      .map((cycle) => ({
        queryKey: ['performance', 'me', 'feedback-summary', cycle.id],
        queryFn: () => fetchMyFeedbackSummary(cycle.id),
      })),
  })

  const feedbackSummaryByCycle = useMemo(
    () =>
      Object.fromEntries(
        (reviewCyclesQuery.data ?? [])
          .filter((cycle) => cycle.feedback_summary_visible)
          .map((cycle, index) => [cycle.id, feedbackSummaryQueries[index]?.data]),
      ),
    [feedbackSummaryQueries, reviewCyclesQuery.data],
  )

  const updateGoalMutation = useMutation({
    mutationFn: ({ goalId, progressPercent }: { goalId: string; progressPercent: number }) =>
      updateMyGoalProgress(goalId, progressPercent),
    onSuccess: () => {
      toast.success('Goal progress updated.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'me', 'goals'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to update goal progress.'))
    },
  })

  const saveSelfAssessmentMutation = useMutation({
    mutationFn: ({ cycleId, rating, comments }: { cycleId: string; rating: number; comments: string }) =>
      saveMySelfAssessment(cycleId, { ratings: { overall: rating }, comments }),
    onSuccess: () => {
      toast.success('Self-assessment saved.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'me', 'review-cycles'] })
      void queryClient.invalidateQueries({ queryKey: ['performance', 'me', 'reviews'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to save the self-assessment.'))
    },
  })

  const submitSelfAssessmentMutation = useMutation({
    mutationFn: ({ cycleId, rating, comments }: { cycleId: string; rating: number; comments: string }) =>
      submitMySelfAssessment(cycleId, { ratings: { overall: rating }, comments }),
    onSuccess: () => {
      toast.success('Self-assessment submitted.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'me', 'review-cycles'] })
      void queryClient.invalidateQueries({ queryKey: ['performance', 'me', 'reviews'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to submit the self-assessment.'))
    },
  })

  const historicalReviews = useMemo(
    () => (historicalReviewsQuery.data ?? []).filter((review) => review.status === 'SUBMITTED'),
    [historicalReviewsQuery.data],
  )

  if (goalsQuery.isLoading || reviewCyclesQuery.isLoading || historicalReviewsQuery.isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Performance"
        title="My performance"
        description="Track assigned goals, complete the active self-assessment cycle, and review 360 feedback once the manager phase opens."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.04fr)_minmax(0,0.96fr)]">
        <SectionCard title="My goals" description="Update progress as work moves forward so managers see the latest delivery picture.">
          {!goalsQuery.data?.length ? (
            <EmptyState
              icon={Target}
              title="No goals assigned"
              description="Goals will appear here once your manager creates them in an active cycle."
            />
          ) : (
            <div className="space-y-3">
              {goalsQuery.data.map((goal) => (
                <div key={goal.id} className="surface-muted rounded-[22px] px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{goal.title}</p>
                      {goal.description ? <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{goal.description}</p> : null}
                    </div>
                    <StatusBadge tone={getGoalTone(goal.status)}>{goal.status}</StatusBadge>
                  </div>
                  <div className="mt-4 flex items-center justify-between text-sm text-[hsl(var(--muted-foreground))]">
                    <span>Progress</span>
                    <span>{goal.progress_percent}%</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-[hsl(var(--border)_/_0.9)]">
                    <div
                      className="h-2 rounded-full bg-[hsl(var(--brand))]"
                      style={{ width: `${goal.progress_percent}%` }}
                      role="progressbar"
                      aria-valuenow={goal.progress_percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    />
                  </div>
                  <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center">
                    <input
                      className="field-input md:max-w-[10rem]"
                      type="number"
                      min="0"
                      max="100"
                      value={progressDrafts[goal.id] ?? String(goal.progress_percent)}
                      onChange={(event) => setProgressDrafts((current) => ({ ...current, [goal.id]: event.target.value }))}
                      aria-label={`Progress for ${goal.title}`}
                    />
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() =>
                        void updateGoalMutation.mutateAsync({
                          goalId: goal.id,
                          progressPercent: Number(progressDrafts[goal.id] ?? goal.progress_percent),
                        })
                      }
                      disabled={updateGoalMutation.isPending}
                    >
                      Save progress
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Active review cycles" description="Save your self-assessment as you draft it, then submit it once you are ready.">
          {!reviewCyclesQuery.data?.length ? (
            <EmptyState
              icon={ClipboardCheck}
              title="No active review cycles"
              description="Any self-assessment cycles assigned to you will appear here."
            />
          ) : (
            <div className="space-y-3">
              {reviewCyclesQuery.data.map((cycle) => {
                const currentReview = cycle.self_assessment
                const ratingValue = reviewRatings[cycle.id] ?? getOverallRating(currentReview)
                const commentValue = reviewComments[cycle.id] ?? currentReview?.comments ?? ''
                const feedbackSummary = feedbackSummaryByCycle[cycle.id]

                return (
                  <div key={cycle.id} className="surface-muted rounded-[22px] px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{cycle.name}</p>
                        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                          {cycle.review_type} • {cycle.status.replace(/_/g, ' ')}
                        </p>
                      </div>
                      <StatusBadge tone={getReviewTone(currentReview?.status ?? cycle.status)}>
                        {currentReview?.status ?? cycle.status}
                      </StatusBadge>
                    </div>

                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div>
                        <label className="field-label" htmlFor={`review-rating-${cycle.id}`}>Overall rating</label>
                        <input
                          id={`review-rating-${cycle.id}`}
                          className="field-input"
                          type="number"
                          min="1"
                          max="5"
                          step="0.5"
                          value={ratingValue}
                          onChange={(event) => setReviewRatings((current) => ({ ...current, [cycle.id]: event.target.value }))}
                        />
                      </div>
                      <div className="rounded-[18px] border border-[hsl(var(--border)_/_0.85)] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
                        <p className="font-medium text-[hsl(var(--foreground-strong))]">Deadlines</p>
                        <p className="mt-2">Self: {cycle.self_assessment_deadline || 'Not set'}</p>
                        <p>Manager: {cycle.manager_review_deadline || 'Not set'}</p>
                      </div>
                    </div>

                    <textarea
                      className="field-textarea mt-4"
                      value={commentValue}
                      onChange={(event) => setReviewComments((current) => ({ ...current, [cycle.id]: event.target.value }))}
                      placeholder="Write your self-assessment comments"
                    />

                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() =>
                          void saveSelfAssessmentMutation.mutateAsync({
                            cycleId: cycle.id,
                            rating: Number(ratingValue || 0),
                            comments: commentValue,
                          })
                        }
                        disabled={saveSelfAssessmentMutation.isPending || currentReview?.status === 'SUBMITTED'}
                      >
                        Save draft
                      </button>
                      <button
                        type="button"
                        className="btn-primary"
                        onClick={() =>
                          void submitSelfAssessmentMutation.mutateAsync({
                            cycleId: cycle.id,
                            rating: Number(ratingValue || 0),
                            comments: commentValue,
                          })
                        }
                        disabled={submitSelfAssessmentMutation.isPending || currentReview?.status === 'SUBMITTED'}
                      >
                        Submit self-assessment
                      </button>
                    </div>

                    {feedbackSummary ? (
                      <div className="mt-4 rounded-[18px] border border-[hsl(var(--border)_/_0.82)] bg-white/50 px-4 py-4">
                        <div className="flex items-center gap-2 text-[hsl(var(--foreground-strong))]">
                          <MessageSquareMore className="h-4 w-4" />
                          <p className="font-medium">360 feedback summary</p>
                        </div>
                        <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                          {feedbackSummary.response_count} anonymous response{feedbackSummary.response_count === 1 ? '' : 's'}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {Object.entries(feedbackSummary.dimensions).map(([dimension, value]) => (
                            <StatusBadge key={dimension} tone="info">
                              {dimension}: {value.avg.toFixed(1)}
                            </StatusBadge>
                          ))}
                        </div>
                        {feedbackSummary.comments.length ? (
                          <div className="mt-3 space-y-2">
                            {feedbackSummary.comments.map((comment, index) => (
                              <p key={`${cycle.id}-comment-${index}`} className="rounded-[16px] bg-[hsl(var(--background))] px-3 py-2 text-sm text-[hsl(var(--muted-foreground))]">
                                {comment}
                              </p>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                )
              })}
            </div>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Review history" description="Submitted reviews remain visible for reference after each cycle moves forward.">
        {!historicalReviews.length ? (
          <EmptyState
            icon={ClipboardCheck}
            title="No submitted reviews yet"
            description="Completed self and manager reviews will appear here once they are submitted."
          />
        ) : (
          <div className="space-y-3">
            {historicalReviews.map((review) => (
              <div key={review.id} className="surface-muted rounded-[22px] px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{review.cycle_name}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      {review.relationship} • {review.cycle_status.replace(/_/g, ' ')}
                    </p>
                  </div>
                  <StatusBadge tone={getReviewTone(review.status)}>{review.status}</StatusBadge>
                </div>
                {review.comments ? <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">{review.comments}</p> : null}
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  )
}
