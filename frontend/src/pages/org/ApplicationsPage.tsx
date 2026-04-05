import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { advanceRecruitmentApplicationStage, fetchRecruitmentApplications } from '@/lib/api/recruitment'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime, startCase } from '@/lib/format'

const STAGES = ['APPLIED', 'SCREENING', 'INTERVIEW', 'OFFER', 'HIRED', 'REJECTED', 'WITHDRAWN'] as const

function getStageTone(stage: string) {
  if (stage === 'HIRED') return 'success'
  if (stage === 'REJECTED' || stage === 'WITHDRAWN') return 'danger'
  if (stage === 'OFFER' || stage === 'INTERVIEW') return 'warning'
  return 'info'
}

export function ApplicationsPage() {
  const queryClient = useQueryClient()
  const [filterStage, setFilterStage] = useState('')
  const [draftStages, setDraftStages] = useState<Record<string, string>>({})

  const applicationsQuery = useQuery({
    queryKey: ['recruitment', 'applications', filterStage],
    queryFn: () => fetchRecruitmentApplications(filterStage || undefined),
  })

  const stageMutation = useMutation({
    mutationFn: ({ applicationId, stage }: { applicationId: string; stage: string }) =>
      advanceRecruitmentApplicationStage(applicationId, stage),
    onSuccess: () => {
      toast.success('Application stage updated.')
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'applications'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to update the application stage.'))
    },
  })

  if (applicationsQuery.isLoading) {
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
        eyebrow="Recruitment"
        title="Applications"
        description="Track candidate progress across screening, interviews, offers, and hire conversion."
      />

      <SectionCard title="Pipeline" description="Filter by stage, move candidates forward, and jump into the detailed candidate timeline when you need interview or offer actions.">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <label className="grid gap-2 lg:max-w-xs">
            <span className="field-label">Filter by stage</span>
            <select className="field-input" value={filterStage} onChange={(event) => setFilterStage(event.target.value)}>
              <option value="">All stages</option>
              {STAGES.map((stage) => (
                <option key={stage} value={stage}>{startCase(stage)}</option>
              ))}
            </select>
          </label>
        </div>

        {!applicationsQuery.data?.length ? (
          <EmptyState title="No applications yet" description="Candidate applications will appear here once recruiters start adding talent against job postings." />
        ) : (
          <div className="table-shell overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Candidate</th>
                  <th className="pb-3 pr-4 font-semibold">Role</th>
                  <th className="pb-3 pr-4 font-semibold">Stage</th>
                  <th className="pb-3 pr-4 font-semibold">Applied</th>
                  <th className="pb-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {applicationsQuery.data.map((application) => (
                  <tr key={application.id} className="table-row border-b border-[hsl(var(--border)_/_0.76)] last:border-b-0">
                    <td className="py-4 pr-4">
                      <p className="table-primary font-semibold">{application.candidate_name}</p>
                      <p className="table-secondary mt-1 text-xs">{application.candidate_email}</p>
                    </td>
                    <td className="table-secondary py-4 pr-4">{application.job_posting_title}</td>
                    <td className="py-4 pr-4">
                      <StatusBadge tone={getStageTone(application.stage)}>{application.stage}</StatusBadge>
                    </td>
                    <td className="table-secondary py-4 pr-4">{formatDateTime(application.applied_at)}</td>
                    <td className="py-4">
                      <div className="flex flex-col items-end gap-2 md:flex-row md:justify-end">
                        <Link to={`/org/recruitment/candidates/${application.candidate}`} className="btn-secondary">
                          Open candidate
                        </Link>
                        <select
                          aria-label={`Move ${application.candidate_name} to stage`}
                          className="field-input min-w-40"
                          value={draftStages[application.id] ?? application.stage}
                          onChange={(event) => setDraftStages((current) => ({ ...current, [application.id]: event.target.value }))}
                        >
                          {STAGES.map((stage) => (
                            <option key={stage} value={stage}>{startCase(stage)}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="btn-primary"
                          disabled={stageMutation.isPending}
                          onClick={() =>
                            void stageMutation.mutateAsync({
                              applicationId: application.id,
                              stage: draftStages[application.id] ?? application.stage,
                            })
                          }
                        >
                          Update stage
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  )
}
