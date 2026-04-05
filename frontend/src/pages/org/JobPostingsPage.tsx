import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BriefcaseBusiness } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { createRecruitmentJobPosting, fetchRecruitmentJobPostings } from '@/lib/api/recruitment'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'

const emptyForm = {
  title: '',
  description: '',
  requirements: '',
}

function getJobStatusTone(status: string) {
  if (status === 'OPEN') return 'success'
  if (status === 'PAUSED') return 'warning'
  if (status === 'CLOSED' || status === 'FILLED') return 'neutral'
  return 'info'
}

export function JobPostingsPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(emptyForm)

  const jobsQuery = useQuery({
    queryKey: ['recruitment', 'jobs'],
    queryFn: fetchRecruitmentJobPostings,
  })

  const createMutation = useMutation({
    mutationFn: createRecruitmentJobPosting,
    onSuccess: () => {
      toast.success('Job posting created.')
      setForm(emptyForm)
      void queryClient.invalidateQueries({ queryKey: ['recruitment', 'jobs'] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to create the job posting.'))
    },
  })

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void createMutation.mutateAsync(form)
  }

  if (jobsQuery.isLoading) {
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
        eyebrow="Recruitment"
        title="Job postings"
        description="Open roles start here. Draft postings can be refined before you begin moving candidates through the hiring pipeline."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <SectionCard title="New posting" description="Create the role profile first. Candidate movement and offer handoff happen against a specific posting.">
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <div>
              <label className="field-label" htmlFor="job-posting-title">Title</label>
              <input
                id="job-posting-title"
                className="field-input"
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="Senior Backend Engineer"
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="job-posting-description">Description</label>
              <textarea
                id="job-posting-description"
                className="field-input min-h-28"
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Scope, team context, and immediate ownership."
              />
            </div>
            <div>
              <label className="field-label" htmlFor="job-posting-requirements">Requirements</label>
              <textarea
                id="job-posting-requirements"
                className="field-input min-h-24"
                value={form.requirements}
                onChange={(event) => setForm((current) => ({ ...current, requirements: event.target.value }))}
                placeholder="Python, Django, payroll domain familiarity."
              />
            </div>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create posting'}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Open pipeline" description="Each posting tracks how many applications are in motion and whether the role is still actively hiring.">
          {!jobsQuery.data?.length ? (
            <EmptyState
              icon={BriefcaseBusiness}
              title="No job postings yet"
              description="Create the first posting to start collecting and tracking applications."
            />
          ) : (
            <div className="table-shell overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="table-head-row">
                    <th className="pb-3 pr-4 font-semibold">Title</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Applications</th>
                    <th className="pb-3 font-semibold">Created</th>
                  </tr>
                </thead>
                <tbody className="table-body">
                  {jobsQuery.data.map((posting) => (
                    <tr key={posting.id} className="table-row border-b border-[hsl(var(--border)_/_0.76)] last:border-b-0">
                      <td className="py-4 pr-4">
                        <p className="table-primary font-semibold">{posting.title}</p>
                        <p className="table-secondary mt-1 text-xs">{posting.department_name || 'Department not assigned'}</p>
                      </td>
                      <td className="py-4 pr-4">
                        <StatusBadge tone={getJobStatusTone(posting.status)}>{posting.status}</StatusBadge>
                      </td>
                      <td className="table-secondary py-4 pr-4">{posting.application_count}</td>
                      <td className="table-secondary py-4">{formatDateTime(posting.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
