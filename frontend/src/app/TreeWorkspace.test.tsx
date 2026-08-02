// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { type ComponentProps } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TreeWorkspace } from './TreeWorkspace'

vi.mock('../panels/MockPatientSidebar', () => ({
  MockPatientSidebar: () => <div>Mock patient sidebar</div>,
}))

vi.mock('../panels/Legend', () => ({
  Legend: () => <div>Legend</div>,
}))

vi.mock('../panels/NodeDetailPanel', () => ({
  NodeDetailPanel: () => <div>Node details</div>,
}))

vi.mock('../panels/GlobalConfigPanel', () => ({
  GlobalConfigPanel: () => <div>Global config</div>,
}))

vi.mock('../canvas/TreeCanvas', () => ({
  TreeCanvas: () => <div>Tree canvas</div>,
}))

function installMatchMedia(matches: boolean) {
  const listeners = new Set<(event: MediaQueryListEvent) => void>()

  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: (_event: 'change', listener: (event: MediaQueryListEvent) => void) => {
        listeners.add(listener)
      },
      removeEventListener: (_event: 'change', listener: (event: MediaQueryListEvent) => void) => {
        listeners.delete(listener)
      },
      addListener: (listener: (event: MediaQueryListEvent) => void) => {
        listeners.add(listener)
      },
      removeListener: (listener: (event: MediaQueryListEvent) => void) => {
        listeners.delete(listener)
      },
      dispatchEvent: vi.fn(),
    })),
  })

  return {
    emit(nextMatches: boolean) {
      for (const listener of listeners) {
        listener({ matches: nextMatches } as MediaQueryListEvent)
      }
    },
  }
}

const mobileMedia = installMatchMedia(true)

const mobileProps: ComponentProps<typeof TreeWorkspace> = {
  graph: undefined,
  theme: 'light',
  isRunning: false,
  canReset: false,
  sidebarWidth: 320,
  isResizing: false,
  onResizeStart: vi.fn(),
  focusNodeKey: null,
  selectedNode: null,
  highlightedNodeKeys: new Set(),
  activeNodeKey: null,
  manualMode: false,
  manualStepInfo: null,
  onSelectNode: vi.fn(),
  onJumpToLink: vi.fn(),
  onStart: vi.fn(),
  onManualStart: vi.fn(),
  onManualStep: vi.fn(),
  onReset: vi.fn(),
  onToggleTheme: vi.fn(),
}

beforeEach(() => {
  mobileMedia.emit(true)
})

afterEach(cleanup)

describe('TreeWorkspace mobile drawers', () => {
  it('opens the patient drawer and exposes its expanded state on mobile', async () => {
    const user = userEvent.setup()

    render(<TreeWorkspace {...mobileProps} />)

    await user.click(screen.getByRole('button', { name: 'Show patient panel' }))

    expect(screen.getByRole('button', { name: 'Hide patient panel' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Close open panel' })).toBeInTheDocument()
  })

  it('keeps only one mobile drawer open at a time', async () => {
    const user = userEvent.setup()

    render(<TreeWorkspace {...mobileProps} />)

    await user.click(screen.getByRole('button', { name: 'Show patient panel' }))
    await user.click(screen.getByRole('button', { name: 'Show details panel' }))

    expect(screen.getByRole('button', { name: 'Show patient panel' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: 'Hide details panel' })).toHaveAttribute('aria-expanded', 'true')
  })

  it('closes the active mobile drawer from the backdrop', async () => {
    const user = userEvent.setup()

    render(<TreeWorkspace {...mobileProps} />)

    await user.click(screen.getByRole('button', { name: 'Show patient panel' }))
    await user.click(screen.getByRole('button', { name: 'Close open panel' }))

    expect(screen.getByRole('button', { name: 'Show patient panel' })).toHaveAttribute('aria-expanded', 'false')
  })
})
