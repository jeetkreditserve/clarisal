import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { fetchEmployees } from '@/lib/api/org-admin'
import {
  acceptRecruitmentOffer,
  createRecruitmentOffer,
  fetchRecruitmentCandidate,
  scheduleRecruitmentInterview,
} from '@/lib/api/recruitment'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime, startCase } from '@/lib/format'

const DEFAULT_INTERVIEW_FORM = {
  interviewer_id: '',
  scheduled_at: '',
  format: 'VIDEO',
  meet_link: '',
}

const DEFAULT_OFFER_FORM = {
  ctc_annual: '',
  joining_date: '',
  template_text: '',
}

export function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [interviewForms, setInterviewForms] = useState<Record<string, typeof DEFAULT_INTERVIEW_FORM>>({})
  const [offerForms, setOfferForms] = useState<Record<string, typeof DEFAULT_OFFER_FORM>>({})

  const candidateQuery = useQuery({
    queryKey: ['recruitment', 'candidate', id],
    queryFn: () => fetchRecruitmentCandidate(id!),
    enabled: Boolean(id),
  })

  const interviewersQuery = useQuery({
    queryKey: ['org', 'employees', 'active'],
    queryFn: () => fetchEmployees({ status: 'ACTIVE', page: 1 }),
  })

  const interviewMutation = useMutation({
    mutationFn: ({ applicationId, payload }: { applicationId: string; payload: typeof DEFAULT_INTERVIEW_FORM }) =>
      scheduleRecruitmentInterview(applicationId, payload),
    onSuccess: () => {
      toast.success('Interview scheduled.')
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'candidate', id] })
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'applications'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to schedule the interview.'))
    },
  })

  const offerMutation = useMutation({
    mutationFn: ({ applicationId, payload }: { applicationId: string; payload: typeof DEFAULT_OFFER_FORM }) =>
      createRecruitmentOffer(applicationId, payload),
    onSuccess: () => {
      toast.success('Offer letter created.')
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'candidate', id] })
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'applications'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to create the offer letter.'))
    },
  })

  const acceptMutation = useMutation({
    mutationFn: acceptRecruitmentOffer,
    onSuccess: () => {
      toast.success('Offer accepted and onboarding handoff created.')
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'candidate', id] })
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'applications'] })
      void queryClient.invalidateQueries({ queryKey: ['employees'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to accept the offer.'))
    },
  })

  if (candidateQuery.isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  if (!id || !candidateQuery.data) {
    return <EmptyState title="Candidate not found" description="The selected candidate could not be loaded from the recruitment workspace." />
  }

  const activeEmployees = interviewersQuery.data?.results ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Recruitment"
        title={candidateQuery.data.full_name}
        description={`${candidateQuery.data.email}${candidateQuery.data.source ? ` • ${candidateQuery.data.source}` : ''}`}
      />

      {!candidateQuery.data.applications.length ? (
        <EmptyState title="No applications for this candidate" description="This candidate record exists, but there are no job applications attached yet." />
      ) : (
        <div className="space-y-6">
          {candidateQuery.data.applications.map((application) => {
            const interviewForm = interviewForms[application.id] ?? DEFAULT_INTERVIEW_FORM
            const offerForm = offerForms[application.id] ?? DEFAULT_OFFER_FORM

            return (
              <SectionCard
                key={application.id}
                title={application.job_posting_title}
                description="Use this timeline to schedule interviews, issue offers, and confirm the onboarding handoff after acceptance."
              >
                <div className="grid gap-4 lg:grid-cols-3">
                  <div className="surface-muted rounded-[22px] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Stage</p>
                    <div className="mt-3">
                      <StatusBadge tone={application.stage === 'HIRED' ? 'success' : application.stage === 'REJECTED' ? 'danger' : 'info'}>
                        {application.stage}
                      </StatusBadge>
                    </div>
                    <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">Applied {formatDateTime(application.applied_at)}</p>
                  </div>
                  <div className="surface-muted rounded-[22px] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Interviews</p>
                    <div className="mt-3 space-y-3">
                      {application.interviews.length ? application.interviews.map((interview) => (
                        <div key={interview.id} className="rounded-[18px] border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-3 py-3">
                          <p className="font-semibold text-[hsl(var(--foreground-strong))]">{startCase(interview.format)}</p>
                          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{formatDateTime(interview.scheduled_at)}</p>
                          <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">{interview.interviewer_name || 'Interviewer not assigned'}</p>
                        </div>
                      )) : (
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">No interviews scheduled yet.</p>
                      )}
                    </div>
                  </div>
                  <div className="surface-muted rounded-[22px] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Offer</p>
                    {application.offer_letter ? (
                      <div className="mt-3 space-y-3">
                        <StatusBadge tone={application.offer_letter.status === 'ACCEPTED' ? 'success' : 'warning'}>
                          {application.offer_letter.status}
                        </StatusBadge>
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">CTC {application.offer_letter.ctc_annual}</p>
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">
                          Joining {application.offer_letter.joining_date || 'Not set'}
                        </p>
                        {application.offer_letter.status !== 'ACCEPTED' ? (
                          <button
                            type="button"
                            className="btn-primary"
                            disabled={acceptMutation.isPending}
                            onClick={() => void acceptMutation.mutateAsync(application.offer_letter!.id)}
                          >
                            Accept offer
                          </button>
                        ) : null}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">No offer letter has been created yet.</p>
                    )}
                  </div>
                </div>

                <div className="mt-6 grid gap-6 xl:grid-cols-2">
                  <form
                    className="grid gap-4"
                    onSubmit={(event) => {
                      event.preventDefault()
                      void interviewMutation.mutateAsync({
                        applicationId: application.id,
                        payload: interviewForm,
                      })
                    }}
                  >
                    <div>
                      <label className="field-label" htmlFor={`interviewer-${application.id}`}>Interviewer</label>
                      <select
                        id={`interviewer-${application.id}`}
                        className="field-input"
                        value={interviewForm.interviewer_id}
                        onChange={(event) =>
                          setInterviewForms((current) => ({
                            ...current,
                            [application.id]: { ...interviewForm, interviewer_id: event.target.value },
                          }))
                        }
                      >
                        <option value="">Select interviewer</option>
                        {activeEmployees.map((employee) => (
                          <option key={employee.id} value={employee.id}>{employee.full_name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="field-label" htmlFor={`scheduled-at-${application.id}`}>Scheduled at</label>
                      <input
                        id={`scheduled-at-${application.id}`}
                        className="field-input"
                        type="datetime-local"
                        value={interviewForm.scheduled_at}
                        onChange={(event) =>
                          setInterviewForms((current) => ({
                            ...current,
                            [application.id]: { ...interviewForm, scheduled_at: event.target.value },
                          }))
                        }
                        required
                      />
                    </div>
                    <div>
                      <label className="field-label" htmlFor={`interview-format-${application.id}`}>Format</label>
                      <select
                        id={`interview-format-${application.id}`}
                        className="field-input"
                        value={interviewForm.format}
                        onChange={(event) =>
                          setInterviewForms((current) => ({
                            ...current,
                            [application.id]: { ...interviewForm, format: event.target.value },
                          }))
                        }
                      >
                        <option value="PHONE">Phone</option>
                        <option value="VIDEO">Video</option>
                        <option value="IN_PERSON">In person</option>
                        <option value="TECHNICAL">Technical</option>
                      </select>
                    </div>
                    <div>
                      <label className="field-label" htmlFor={`meet-link-${application.id}`}>Meet link</label>
                      <input
                        id={`meet-link-${application.id}`}
                        className="field-input"
                        value={interviewForm.meet_link}
                        onChange={(event) =>
                          setInterviewForms((current) => ({
                            ...current,
                            [application.id]: { ...interviewForm, meet_link: event.target.value },
                          }))
                        }
                        placeholder="https://meet.example.com/round-1"
                      />
                    </div>
                    <button type="submit" className="btn-secondary" disabled={interviewMutation.isPending}>
                      {interviewMutation.isPending ? 'Scheduling…' : 'Schedule interview'}
                    </button>
                  </form>

                  <form
                    className="grid gap-4"
                    onSubmit={(event) => {
                      event.preventDefault()
                      void offerMutation.mutateAsync({
                        applicationId: application.id,
                        payload: offerForm,
                      })
                    }}
                  >
                    <div>
                      <label className="field-label" htmlFor={`offer-ctc-${application.id}`}>Annual CTC</label>
                      <input
                        id={`offer-ctc-${application.id}`}
                        className="field-input"
                        value={offerForm.ctc_annual}
                        onChange={(event) =>
                          setOfferForms((current) => ({
                            ...current,
                            [application.id]: { ...offerForm, ctc_annual: event.target.value },
                          }))
                        }
                        placeholder="1450000.00"
                        required
                      />
                    </div>
                    <div>
                      <label className="field-label" htmlFor={`offer-joining-${application.id}`}>Joining date</label>
                      <input
                        id={`offer-joining-${application.id}`}
                        className="field-input"
                        type="date"
                        value={offerForm.joining_date}
                        onChange={(event) =>
                          setOfferForms((current) => ({
                            ...current,
                            [application.id]: { ...offerForm, joining_date: event.target.value },
                          }))
                        }
                      />
                    </div>
                    <div>
                      <label className="field-label" htmlFor={`offer-template-${application.id}`}>Offer notes</label>
                      <textarea
                        id={`offer-template-${application.id}`}
                        className="field-input min-h-28"
                        value={offerForm.template_text}
                        onChange={(event) =>
                          setOfferForms((current) => ({
                            ...current,
                            [application.id]: { ...offerForm, template_text: event.target.value },
                          }))
                        }
                        placeholder="Compensation summary and joining notes."
                      />
                    </div>
                    <button type="submit" className="btn-primary" disabled={offerMutation.isPending || Boolean(application.offer_letter)}>
                      {offerMutation.isPending ? 'Creating…' : application.offer_letter ? 'Offer already created' : 'Create offer'}
                    </button>
                  </form>
                </div>
              </SectionCard>
            )
          })}
        </div>
      )}
    </div>
  )
}
