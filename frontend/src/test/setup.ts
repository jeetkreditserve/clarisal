import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import React from 'react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
})

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (!('ResizeObserver' in window)) {
  Object.defineProperty(window, 'ResizeObserver', {
    writable: true,
    value: ResizeObserverMock,
  })
}

vi.mock('motion/react', () => {
  const MotionDiv = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(function MotionDiv(props, ref) {
    const { animate: _animate, initial: _initial, transition: _transition, whileHover: _whileHover, ...rest } = props as Record<string, unknown>
    return React.createElement('div', { ...rest, ref }, props.children)
  })

  return {
    motion: new Proxy(
      {},
      {
        get: () => MotionDiv,
      },
    ),
  }
})
