import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Check, LaptopMinimal, MoonStar, SunMedium } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/hooks/useTheme'
import type { ThemePreference } from '@/context/theme-context'

const themeIcons = {
  system: LaptopMinimal,
  light: SunMedium,
  dark: MoonStar,
}

const themeLabels: Record<ThemePreference, string> = {
  system: 'System',
  light: 'Light',
  dark: 'Dark',
}

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme()
  const CurrentIcon = themeIcons[theme]

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button type="button" className="theme-toggle-button" aria-label="Toggle color theme">
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={theme}
              initial={{ opacity: 0, scale: 0.72, rotate: -16 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              exit={{ opacity: 0, scale: 0.72, rotate: 16 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="flex items-center justify-center"
            >
              <CurrentIcon className="h-4 w-4" />
            </motion.span>
          </AnimatePresence>
          <span className="hidden sm:block">{themeLabels[theme]}</span>
          <span className="sr-only">Current theme {themeLabels[resolvedTheme]}</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          sideOffset={10}
          align="end"
          className="theme-menu-content"
        >
          {(['system', 'light', 'dark'] as ThemePreference[]).map((option) => {
            const Icon = themeIcons[option]
            const active = option === theme
            return (
              <DropdownMenu.Item
                key={option}
                onSelect={() => setTheme(option)}
                className={cn('theme-menu-item', active && 'theme-menu-item-active')}
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  {themeLabels[option]}
                </span>
                {active ? <Check className="h-4 w-4" /> : null}
              </DropdownMenu.Item>
            )
          })}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
