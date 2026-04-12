import api from '@/lib/api'
import type {
  PerformanceAppraisalCycle,
  PerformanceCalibrationSession,
  PerformanceFeedbackSummary,
  PerformanceGoal,
  PerformanceGoalCycle,
  PerformanceReview,
  PerformanceReviewCycleSummary,
} from '@/types/hr'

export async function fetchOrgGoalCycles() {
  const { data } = await api.get<PerformanceGoalCycle[]>('/org/performance/goal-cycles/')
  return data
}

export async function createOrgGoalCycle(payload: {
  name: string
  start_date: string
  end_date: string
  auto_create_review_cycle: boolean
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
  goal_cycle_id?: string | null
  self_assessment_deadline?: string | null
  peer_review_deadline?: string | null
  manager_review_deadline?: string | null
  calibration_deadline?: string | null
}) {
  const { data } = await api.post<PerformanceAppraisalCycle>('/org/performance/appraisal-cycles/', payload)
  return data
}

export async function activateOrgAppraisalCycle(cycleId: string) {
  const { data } = await api.post<PerformanceAppraisalCycle>(`/org/performance/appraisal-cycles/${cycleId}/activate/`)
  return data
}

export async function advanceOrgAppraisalCycle(cycleId: string) {
  const { data } = await api.post<PerformanceAppraisalCycle>(`/org/performance/appraisal-cycles/${cycleId}/advance/`)
  return data
}

export async function createOrgCalibrationSession(cycleId: string) {
  const { data } = await api.post<PerformanceCalibrationSession>(`/org/performance/appraisal-cycles/${cycleId}/calibration-sessions/`)
  return data
}

export async function adjustOrgCalibrationRating(sessionId: string, employeeId: string, payload: { rating: number; reason: string }) {
  const { data } = await api.patch(`/org/performance/calibration-sessions/${sessionId}/employees/${employeeId}/rating/`, payload)
  return data
}

export async function lockOrgCalibrationSession(sessionId: string) {
  const { data } = await api.post<PerformanceCalibrationSession>(`/org/performance/calibration-sessions/${sessionId}/lock/`)
  return data
}

export async function fetchOrgFeedbackSummary(cycleId: string, employeeId: string) {
  const { data } = await api.get<PerformanceFeedbackSummary>(`/org/performance/appraisal-cycles/${cycleId}/employees/${employeeId}/feedback-summary/`)
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

export async function fetchMyReviewCycles() {
  const { data } = await api.get<PerformanceReviewCycleSummary[]>('/me/performance/review-cycles/')
  return data
}

export async function fetchMySelfAssessment(cycleId: string) {
  const { data } = await api.get<PerformanceReview>(`/me/performance/review-cycles/${cycleId}/self-assessment/`)
  return data
}

export async function saveMySelfAssessment(cycleId: string, payload: { ratings: Record<string, number>; comments: string }) {
  const { data } = await api.put<PerformanceReview>(`/me/performance/review-cycles/${cycleId}/self-assessment/`, payload)
  return data
}

export async function submitMySelfAssessment(cycleId: string, payload?: { ratings?: Record<string, number>; comments?: string }) {
  const { data } = await api.post<PerformanceReview>(`/me/performance/review-cycles/${cycleId}/self-assessment/submit/`, payload ?? {})
  return data
}

export async function fetchMyFeedbackSummary(cycleId: string) {
  const { data } = await api.get<PerformanceFeedbackSummary>(`/me/performance/review-cycles/${cycleId}/feedback-summary/`)
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
