import * as Popover from '@radix-ui/react-popover'
import { Check, ChevronDown, Search } from 'lucide-react'
import { useMemo, useState } from 'react'

import { cn } from '@/lib/utils'

export interface AppSelectOption {
  value: string
  label: string
  hint?: string
  disabled?: boolean
  keywords?: string[]
}

interface AppSelectProps {
  id?: string
  name?: string
  value?: string | null
  onValueChange: (value: string) => void
  options: AppSelectOption[]
  placeholder?: string
  searchPlaceholder?: string
  emptyLabel?: string
  disabled?: boolean
  searchable?: boolean
  triggerClassName?: string
  contentClassName?: string
  side?: 'top' | 'right' | 'bottom' | 'left'
}

export function AppSelect({
  id,
  name,
  value,
  onValueChange,
  options,
  placeholder = 'Select an option',
  searchPlaceholder = 'Search options',
  emptyLabel = 'No options found.',
  disabled,
  searchable,
  triggerClassName,
  contentClassName,
  side = 'bottom',
}: AppSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  const selectedOption = options.find((option) => option.value === value) ?? null
  const enableSearch = searchable ?? options.length >= 8

  const filteredOptions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    if (!normalizedQuery) return options
    return options.filter((option) => {
      const keywords = [option.label, option.hint ?? '', ...(option.keywords ?? [])].join(' ').toLowerCase()
      return keywords.includes(normalizedQuery)
    })
  }, [options, query])

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (!nextOpen) {
      setQuery('')
    }
  }

  return (
    <Popover.Root open={open} onOpenChange={handleOpenChange}>
      {name ? <input type="hidden" name={name} value={value ?? ''} /> : null}
      <Popover.Trigger asChild>
        <button
          id={id}
          type="button"
          disabled={disabled}
          className={cn(
            'field-input flex items-center justify-between gap-3 text-left disabled:cursor-not-allowed disabled:opacity-60',
            !selectedOption && 'text-[hsl(var(--muted-foreground))]',
            triggerClassName,
          )}
          aria-haspopup="listbox"
          aria-expanded={open}
        >
          <span className="min-w-0 flex-1 truncate">{selectedOption?.label ?? placeholder}</span>
          <ChevronDown className="h-4 w-4 shrink-0 text-[hsl(var(--muted-foreground))]" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side={side}
          align="start"
          sideOffset={8}
          className={cn(
            'z-50 w-[var(--radix-popover-trigger-width)] min-w-[16rem] rounded-[1.2rem] border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-2 shadow-[var(--shadow-card)] backdrop-blur-xl',
            contentClassName,
          )}
        >
          {enableSearch ? (
            <div className="relative mb-2">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                className="field-input min-h-[2.75rem] pl-9"
              />
            </div>
          ) : null}
          <div className="max-h-72 overflow-y-auto pr-1">
            {filteredOptions.length === 0 ? (
              <p className="px-3 py-3 text-sm text-[hsl(var(--muted-foreground))]">{emptyLabel}</p>
            ) : (
              <div className="grid gap-1">
                {filteredOptions.map((option) => {
                  const isSelected = option.value === value
                  return (
                    <button
                      key={option.value}
                      type="button"
                      disabled={option.disabled}
                      onClick={() => {
                        onValueChange(option.value)
                        handleOpenChange(false)
                      }}
                      className={cn(
                        'flex w-full items-start justify-between gap-3 rounded-[1rem] px-3 py-2.5 text-left text-sm transition',
                        option.disabled
                          ? 'cursor-not-allowed opacity-50'
                          : 'hover:bg-[hsl(var(--surface-subtle))] focus:bg-[hsl(var(--surface-subtle))] focus:outline-none',
                        isSelected && 'bg-[hsl(var(--brand)/0.12)] text-[hsl(var(--foreground-strong))]',
                      )}
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium text-[hsl(var(--foreground-strong))]">{option.label}</span>
                        {option.hint ? (
                          <span className="mt-0.5 block text-xs text-[hsl(var(--muted-foreground))]">{option.hint}</span>
                        ) : null}
                      </span>
                      <Check
                        className={cn(
                          'mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--brand))] transition-opacity',
                          isSelected ? 'opacity-100' : 'opacity-0',
                        )}
                      />
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
