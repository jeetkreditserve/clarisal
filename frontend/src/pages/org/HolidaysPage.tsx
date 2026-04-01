import { useState } from 'react'
import { MinusCircle, PlusCircle } from 'lucide-react'
import { toast } from 'sonner'

import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateHolidayCalendar, useHolidayCalendars, useLocations, usePublishHolidayCalendar } from '@/hooks/useOrgAdmin'
import { createDefaultHolidayCalendarForm, HOLIDAY_CLASSIFICATION_OPTIONS, HOLIDAY_SESSION_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { startCase } from '@/lib/format'

export function HolidaysPage() {
  const { data, isLoading } = useHolidayCalendars()
  const { data: locations } = useLocations()
  const createMutation = useCreateHolidayCalendar()
  const publishMutation = usePublishHolidayCalendar()
  const [form, setForm] = useState(createDefaultHolidayCalendarForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const locationOptions =
    locations?.filter((location) => location.is_active).map((location) => ({
      value: location.id,
      label: location.name,
    })) ?? []
  const holidayClassificationOptions = HOLIDAY_CLASSIFICATION_OPTIONS.map((classification) => ({
    value: classification,
    label: startCase(classification),
  }))
  const holidaySessionOptions = HOLIDAY_SESSION_OPTIONS.map((session) => ({
    value: session,
    label: startCase(session),
  }))

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      await createMutation.mutateAsync(form)
      toast.success('Holiday calendar created.')
      setForm(createDefaultHolidayCalendarForm())
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to create holiday calendar.'))
      }
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Holidays" title="Holiday calendars" description="Define and publish annual holiday calendars, then assign them to office locations." />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Create holiday calendar" description="Holiday calendars are date-based and managed year by year, while leave cycles remain separately configurable.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div>
              <input className="field-input" placeholder="Calendar name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required />
              <FieldErrorText message={fieldErrors.name} />
            </div>
            <div>
              <input className="field-input" type="number" value={form.year} onChange={(event) => setForm((current) => ({ ...current, year: Number(event.target.value) }))} required />
              <FieldErrorText message={fieldErrors.year} />
            </div>
            <div>
              <textarea className="field-textarea" placeholder="Description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
              <FieldErrorText message={fieldErrors.description} />
            </div>
            <AppCheckbox
              id="holiday-default"
              checked={form.is_default}
              onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))}
              label="Default calendar for this year"
            />
            <div className="grid gap-2">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Assigned office locations</p>
              {locationOptions.map((location) => (
                <AppCheckbox
                  key={location.value}
                  id={`holiday-location-${location.value}`}
                  checked={form.location_ids.includes(location.value)}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      location_ids: checked
                        ? [...current.location_ids, location.value]
                        : current.location_ids.filter((id) => id !== location.value),
                    }))
                  }
                  label={location.label}
                />
              ))}
            </div>
            {form.holidays.map((holiday, index) => (
              <div key={index} className="surface-muted grid gap-3 rounded-[22px] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Holiday entry {index + 1}</p>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 text-sm font-medium text-[hsl(var(--danger))] disabled:opacity-40"
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        holidays: current.holidays.filter((_, itemIndex) => itemIndex !== index),
                      }))
                    }
                    disabled={form.holidays.length === 1}
                  >
                    <MinusCircle className="h-4 w-4" />
                    Remove row
                  </button>
                </div>
                <div>
                  <input className="field-input" placeholder="Holiday name" value={holiday.name} onChange={(event) => setForm((current) => ({ ...current, holidays: current.holidays.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item) }))} required />
                </div>
                <div>
                  <AppDatePicker
                    value={holiday.holiday_date}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        holidays: current.holidays.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, holiday_date: value } : item,
                        ),
                      }))
                    }
                    placeholder="Select holiday date"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <AppSelect
                    value={holiday.classification}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        holidays: current.holidays.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, classification: value } : item,
                        ),
                      }))
                    }
                    options={holidayClassificationOptions}
                  />
                  <AppSelect
                    value={holiday.session}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        holidays: current.holidays.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, session: value } : item,
                        ),
                      }))
                    }
                    options={holidaySessionOptions}
                  />
                </div>
              </div>
            ))}
            <button type="button" className="btn-secondary" onClick={() => setForm((current) => ({ ...current, holidays: [...current.holidays, { name: '', holiday_date: '', classification: 'PUBLIC', session: 'FULL_DAY', description: '' }] }))}>
              <PlusCircle className="h-4 w-4" />
              Add holiday
            </button>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              Save holiday calendar
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Published and draft calendars" description="Use separate calendars when different office locations observe different holiday schedules.">
          <div className="space-y-4">
            {data?.map((calendar) => (
              <div key={calendar.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{calendar.name}</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">{calendar.year} • {calendar.holidays.length} holidays</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge tone={calendar.status === 'PUBLISHED' ? 'success' : 'warning'}>{calendar.status}</StatusBadge>
                    {calendar.status !== 'PUBLISHED' ? (
                      <button className="btn-secondary" onClick={() => void publishMutation.mutateAsync(calendar.id)}>
                        Publish
                      </button>
                    ) : null}
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {calendar.holidays.map((holiday) => (
                    <StatusBadge key={holiday.id} tone={holiday.classification === 'PUBLIC' ? 'success' : holiday.classification === 'RESTRICTED' ? 'warning' : 'info'}>
                      {holiday.name}
                    </StatusBadge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
