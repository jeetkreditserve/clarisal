import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { adjustOrgCalibrationRating, createOrgCalibrationSession, lockOrgCalibrationSession } from '@/lib/api/performance'
import { getErrorMessage } from '@/lib/errors'

export function CalibrationPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draftRatings, setDraftRatings] = useState<Record<string, string>>({})
  const [draftReasons, setDraftReasons] = useState<Record<string, string>>({})

  const sessionQuery = useQuery({
    queryKey: ['performance', 'org', 'calibration-session', id],
    queryFn: () => createOrgCalibrationSession(id),
    enabled: Boolean(id),
  })

  const adjustMutation = useMutation({
    mutationFn: ({ sessionId, employeeId, rating, reason }: { sessionId: string; employeeId: string; rating: number; reason: string }) =>
      adjustOrgCalibrationRating(sessionId, employeeId, { rating, reason }),
    onSuccess: () => {
      toast.success('Calibration rating updated.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'org', 'calibration-session', id] })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to update the calibration rating.'))
    },
  })

  const lockMutation = useMutation({
    mutationFn: lockOrgCalibrationSession,
    onSuccess: () => {
      toast.success('Calibration session locked.')
      void queryClient.invalidateQueries({ queryKey: ['performance', 'org', 'appraisal-cycles'] })
      navigate('/org/performance/appraisals')
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Unable to lock the calibration session.'))
    },
  })

  if (sessionQuery.isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={5} />
      </div>
    )
  }

  const session = sessionQuery.data
  if (!session) return null

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Performance"
        title="Calibration"
        description="Review current manager ratings, record moderated changes, and lock the session once the final view is agreed."
      />

      <SectionCard title="Calibration entries" description="Each row starts from the submitted manager rating. Adjustments stay editable until the session is locked.">
        <div className="space-y-3">
          {session.entries.map((entry) => (
            <div key={entry.id} className="surface-muted rounded-[22px] px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{entry.employee_name}</p>
                  <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                    Original rating: {entry.original_rating ?? 'Not available'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <input
                    className="field-input w-28"
                    type="number"
                    min="1"
                    max="5"
                    step="0.5"
                    value={draftRatings[entry.employee] ?? String(entry.current_rating ?? '')}
                    onChange={(event) => setDraftRatings((current) => ({ ...current, [entry.employee]: event.target.value }))}
                    aria-label={`Calibration rating for ${entry.employee_name}`}
                    disabled={Boolean(session.locked_at)}
                  />
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() =>
                      void adjustMutation.mutateAsync({
                        sessionId: session.id,
                        employeeId: entry.employee,
                        rating: Number(draftRatings[entry.employee] ?? entry.current_rating ?? 0),
                        reason: draftReasons[entry.employee] ?? entry.reason,
                      })
                    }
                    disabled={adjustMutation.isPending || Boolean(session.locked_at)}
                  >
                    Save rating
                  </button>
                </div>
              </div>
              <textarea
                className="field-textarea mt-4"
                value={draftReasons[entry.employee] ?? entry.reason}
                onChange={(event) => setDraftReasons((current) => ({ ...current, [entry.employee]: event.target.value }))}
                placeholder="Why is this rating changing?"
                disabled={Boolean(session.locked_at)}
              />
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary"
            onClick={() => void lockMutation.mutateAsync(session.id)}
            disabled={lockMutation.isPending || Boolean(session.locked_at)}
          >
            {session.locked_at ? 'Calibration locked' : 'Lock session'}
          </button>
        </div>
      </SectionCard>
    </div>
  )
}
