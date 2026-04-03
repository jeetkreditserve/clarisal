import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardCheck, Target } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { fetchMyGoals, fetchMyReviews, submitMyReview, updateMyGoalProgress } from '@/lib/api/performance'
import { getErrorMessage } from '@/lib/errors'

function getGoalTone(status: string) {
  if (status === 'COMPLETED') return 'success'
  if (status === 'IN_PROGRESS') return 'info'
  return 'warning'
}

function getReviewTone(status: string) {
  if (status === 'SUBMITTED') return 'success'
  if (status === 'IN_PROGRESS') return 'info'
  return 'warning'
}

export function PerformancePage() {
  const queryClient = useQueryClient()
  const [progressDrafts, setProgressDrafts] = useState<Record<string, string>>({})
  const [reviewComments, setReviewComments] = useState<Record<string, string>>({})

  const goalsQuery = useQuery({
    queryKey: ['performance', 'me', 'goals'],
    queryFn: fetchMyGoals,
  })
  const reviewsQuery = useQuery({
    queryKey: ['performance', 'me', 'reviews'],
    queryFn: fetchMyReviews,
  })

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

  const submitReviewMutation = useMutation({
    mutationFn: ({ reviewId, comments }: { reviewId: string; comments: string }) =>
      submitMyReview(reviewId, { ratings: {}, comments }),
    onSuccess: () => {
      toast.success('Review submitted.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'me', 'reviews'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to submit the review.'))
    },
  })

  const pendingReviews = useMemo(
    () => (reviewsQuery.data ?? []).filter((review) => review.status !== 'SUBMITTED'),
    [reviewsQuery.data],
  )

  if (goalsQuery.isLoading || reviewsQuery.isLoading) {
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
        description="Track assigned goals, keep progress current, and complete any pending appraisal reviews from the same workspace."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
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

        <SectionCard title="Pending reviews" description="Submit the reviews assigned to you. Submitted reviews remain visible here until the appraisal cycle closes.">
          {!pendingReviews.length ? (
            <EmptyState
              icon={ClipboardCheck}
              title="No pending reviews"
              description="Any self or manager reviews assigned to you will appear here."
            />
          ) : (
            <div className="space-y-3">
              {pendingReviews.map((review) => (
                <div key={review.id} className="surface-muted rounded-[22px] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{review.relationship} review</p>
                    <StatusBadge tone={getReviewTone(review.status)}>{review.status}</StatusBadge>
                  </div>
                  <textarea
                    className="field-textarea mt-4"
                    value={reviewComments[review.id] ?? review.comments ?? ''}
                    onChange={(event) => setReviewComments((current) => ({ ...current, [review.id]: event.target.value }))}
                    placeholder="Write your appraisal comments"
                  />
                  <button
                    type="button"
                    className="btn-primary mt-3"
                    onClick={() =>
                      void submitReviewMutation.mutateAsync({
                        reviewId: review.id,
                        comments: reviewComments[review.id] ?? review.comments ?? '',
                      })
                    }
                    disabled={submitReviewMutation.isPending}
                  >
                    Submit review
                  </button>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
