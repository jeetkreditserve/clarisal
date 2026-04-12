import api from '@/lib/api'
import type {
  RecruitmentApplication,
  RecruitmentCandidateConversionResponse,
  RecruitmentCandidateDetail,
  RecruitmentInterview,
  RecruitmentJobPosting,
  RecruitmentOfferLetter,
} from '@/types/hr'

export async function fetchRecruitmentJobPostings() {
  const { data } = await api.get<RecruitmentJobPosting[]>('/org/recruitment/jobs/')
  return data
}

export async function createRecruitmentJobPosting(payload: {
  title: string
  description?: string
  requirements?: string
  department_id?: string | null
  location_id?: string | null
  closes_at?: string | null
}) {
  const { data } = await api.post<RecruitmentJobPosting>('/org/recruitment/jobs/', payload)
  return data
}

export async function fetchRecruitmentApplications(stage?: string) {
  const { data } = await api.get<RecruitmentApplication[]>('/org/recruitment/applications/', {
    params: stage ? { stage } : undefined,
  })
  return data
}

export async function advanceRecruitmentApplicationStage(applicationId: string, stage: string) {
  const { data } = await api.post<RecruitmentApplication>(`/org/recruitment/applications/${applicationId}/stage/`, { stage })
  return data
}

export async function fetchRecruitmentCandidate(candidateId: string) {
  const { data } = await api.get<RecruitmentCandidateDetail>(`/org/recruitment/candidates/${candidateId}/`)
  return data
}

export async function scheduleRecruitmentInterview(
  applicationId: string,
  payload: {
    interviewer_id?: string | null
    scheduled_at: string
    format: string
    feedback?: string
    meet_link?: string
  },
) {
  const { data } = await api.post<RecruitmentInterview>(`/org/recruitment/applications/${applicationId}/interviews/`, payload)
  return data
}

export async function createRecruitmentOffer(
  applicationId: string,
  payload: {
    ctc_annual: string
    joining_date?: string | null
    template_text?: string
    expires_at?: string | null
  },
) {
  const { data } = await api.post<RecruitmentOfferLetter>(`/org/recruitment/applications/${applicationId}/offer/`, payload)
  return data
}

export async function acceptRecruitmentOffer(offerId: string) {
  const { data } = await api.post<{ employee_id: string; status: string }>(`/org/recruitment/offers/${offerId}/accept/`)
  return data
}

export async function convertRecruitmentCandidate(candidateId: string) {
  const { data } = await api.post<RecruitmentCandidateConversionResponse>(`/org/recruitment/candidates/${candidateId}/convert/`)
  return data
}
