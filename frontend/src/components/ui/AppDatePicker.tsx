import * as Popover from '@radix-ui/react-popover'
import { format, parseISO } from 'date-fns'
import { Calendar as CalendarIcon } from 'lucide-react'
import { useMemo, useState } from 'react'
import { DayPicker } from 'react-day-picker'

import { cn } from '@/lib/utils'

interface AppDatePickerProps {
  id?: string
  value?: string | null
  onValueChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
}

export function AppDatePicker({
  id,
  value,
  onValueChange,
  placeholder = 'Select date',
  disabled,
}: AppDatePickerProps) {
  const [open, setOpen] = useState(false)
  const selectedDate = useMemo(() => {
    if (!value) return undefined
    try {
      return parseISO(value)
    } catch {
      return undefined
    }
  }, [value])

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          id={id}
          type="button"
          disabled={disabled}
          className={cn(
            'field-input flex items-center justify-between gap-3 text-left disabled:cursor-not-allowed disabled:opacity-60',
            !selectedDate && 'text-[hsl(var(--muted-foreground))]',
          )}
        >
          <span>{selectedDate ? format(selectedDate, 'dd MMM yyyy') : placeholder}</span>
          <CalendarIcon className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={8}
          align="start"
          className="z-50 rounded-[1.4rem] border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-3 shadow-[var(--shadow-card)] backdrop-blur-xl"
        >
          <DayPicker
            mode="single"
            selected={selectedDate}
            onSelect={(nextDate: Date | undefined) => {
              if (!nextDate) return
              onValueChange(format(nextDate, 'yyyy-MM-dd'))
              setOpen(false)
            }}
            showOutsideDays
            classNames={{
              months: 'flex flex-col',
              month: 'space-y-3',
              caption: 'flex items-center justify-between px-1 pt-1',
              caption_label: 'text-sm font-semibold text-[hsl(var(--foreground-strong))]',
              nav: 'flex items-center gap-1',
              button_previous:
                'inline-flex h-8 w-8 items-center justify-center rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface))] text-[hsl(var(--foreground))] transition hover:bg-[hsl(var(--surface-subtle))]',
              button_next:
                'inline-flex h-8 w-8 items-center justify-center rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface))] text-[hsl(var(--foreground))] transition hover:bg-[hsl(var(--surface-subtle))]',
              weekdays: 'grid grid-cols-7 gap-1',
              weekday:
                'h-8 w-10 text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]',
              week: 'grid grid-cols-7 gap-1',
              day: 'inline-flex h-10 w-10 items-center justify-center rounded-[0.95rem] text-sm font-medium text-[hsl(var(--foreground))] transition hover:bg-[hsl(var(--surface-subtle))]',
              selected: 'bg-[hsl(var(--brand))] text-[hsl(var(--brand-foreground))] hover:bg-[hsl(var(--brand))]',
              today: 'border border-[hsl(var(--ring)/0.35)]',
              outside: 'text-[hsl(var(--muted-foreground))] opacity-45',
            }}
          />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
