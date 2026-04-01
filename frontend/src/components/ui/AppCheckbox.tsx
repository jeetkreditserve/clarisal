import * as Checkbox from '@radix-ui/react-checkbox'
import { Check } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface AppCheckboxProps {
  id?: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  label?: ReactNode
  description?: ReactNode
  disabled?: boolean
  className?: string
}

export function AppCheckbox({
  id,
  checked,
  onCheckedChange,
  label,
  description,
  disabled,
  className,
}: AppCheckboxProps) {
  const checkbox = (
    <Checkbox.Root
      id={id}
      checked={checked}
      disabled={disabled}
      onCheckedChange={(nextChecked: boolean | 'indeterminate') => onCheckedChange(nextChecked === true)}
      className={cn(
        'flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-[hsl(var(--border-strong))] bg-[hsl(var(--surface))] text-[hsl(var(--brand-foreground))] shadow-[var(--shadow-soft)] transition focus:outline-none focus:ring-4 focus:ring-[hsl(var(--ring)/0.16)] data-[state=checked]:border-[hsl(var(--brand))] data-[state=checked]:bg-[hsl(var(--brand))] disabled:cursor-not-allowed disabled:opacity-60',
        className,
      )}
    >
      <Checkbox.Indicator>
        <Check className="h-3.5 w-3.5" />
      </Checkbox.Indicator>
    </Checkbox.Root>
  )

  if (!label && !description) {
    return checkbox
  }

  return (
    <label
      htmlFor={id}
      className={cn(
        'flex items-start gap-3 rounded-[1rem] border border-[hsl(var(--border)/0.7)] bg-[hsl(var(--surface)/0.85)] px-3 py-3 text-sm text-[hsl(var(--foreground))]',
        disabled && 'cursor-not-allowed opacity-60',
      )}
    >
      {checkbox}
      <span className="min-w-0 flex-1">
        {label ? <span className="block font-medium text-[hsl(var(--foreground-strong))]">{label}</span> : null}
        {description ? <span className="mt-1 block text-xs leading-5 text-[hsl(var(--muted-foreground))]">{description}</span> : null}
      </span>
    </label>
  )
}
