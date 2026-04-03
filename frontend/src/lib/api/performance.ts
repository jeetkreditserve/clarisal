import api from '@/lib/api'
import type {
  PerformanceAppraisalCycle,
  PerformanceGoal,
  PerformanceGoalCycle,
  PerformanceReview,
} from '@/types/hr'

export async function fetchOrgGoalCycles() {
  const { data } = await api.get<PerformanceGoalCycle[]>('/org/performance/goal-cycles/')
  return data
}

export async function createOrgGoalCycle(payload: {
  name: string
  start_date: string
  end_date: string
}) {
  const { data } = await api.post<PerformanceGoalCycle>('/org/performance/goal-cycles/', payload)
  return data
}

export async function fetchOrgAppraisalCycles() {
  const { data } = await api.get<PerformanceAppraisalCycle[]>('/org/performance/appraisal-cycles/')
  return data
}

export async function createOrgAppraisalCycle(payload: {
  name: string
  review_type: string
  start_date: string
  end_date: string
}) {
  const { data } = await api.post<PerformanceAppraisalCycle>('/org/performance/appraisal-cycles/', payload)
  return data
}

export async function fetchMyGoals() {
  const { data } = await api.get<PerformanceGoal[]>('/me/performance/goals/')
  return data
}

export async function updateMyGoalProgress(goalId: string, progressPercent: number) {
  const { data } = await api.patch<PerformanceGoal>(`/me/performance/goals/${goalId}/progress/`, {
    progress_percent: progressPercent,
  })
  return data
}

export async function fetchMyReviews() {
  const { data } = await api.get<PerformanceReview[]>('/me/performance/reviews/')
  return data
}

export async function submitMyReview(reviewId: string, payload: { ratings: Record<string, number>; comments: string }) {
  const { data } = await api.post<PerformanceReview>(`/me/performance/reviews/${reviewId}/submit/`, payload)
  return data
}
