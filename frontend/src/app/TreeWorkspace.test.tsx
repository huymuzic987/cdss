// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { type ComponentProps } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TreeWorkspace } from './TreeWorkspace'

vi.mock('../panels/MockPatientSidebar', () => ({
  MockPatientSidebar: () => (
    <div>
      <button type="button">Patient action</button>
    </div>
  ),
}))

vi.mock('../panels/Legend', () => ({
  Legend: () => <div>Legend</div>,
}))

vi.mock('../panels/NodeDetailPanel', () => ({
  NodeDetailPanel: () => (
    <div>
      <button type="button">Details action</button>
    </div>
  ),
}))

vi.mock('../panels/GlobalConfigPanel', () => ({
  GlobalConfigPanel: () => <div>Global config</div>,
}))

vi.mock('../canvas/TreeCanvas', () => ({
  TreeCanvas: () => <div>Tree canvas</div>,
}))

function installMatchMedia(initialMatches: boolean) {
  let matches = initialMatches
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
    setMatches(nextMatches: boolean) {
      matches = nextMatches
      for (const listener of listeners) {
        listener({ matches: nextMatches } as MediaQueryListEvent)
      }
    },
  }
}

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

let matchMediaController: ReturnType<typeof installMatchMedia>

beforeEach(() => {
  matchMediaController = installMatchMedia(true)
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

  it('keeps inactive mobile drawers hidden and moves focus into the opened drawer', async () => {
    const user = userEvent.setup()

    render(<TreeWorkspace {...mobileProps} />)

    const patientPanel = document.querySelector('.left-panel')
    const detailsPanel = document.querySelector('.side-panels')

    expect(patientPanel).toHaveAttribute('aria-hidden', 'true')
    expect(patientPanel).toHaveAttribute('inert')
    expect(detailsPanel).toHaveAttribute('aria-hidden', 'true')
    expect(detailsPanel).toHaveAttribute('inert')

    await user.click(screen.getByRole('button', { name: 'Show patient panel' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Patient action' })).toHaveFocus()
    })
    expect(patientPanel).not.toHaveAttribute('aria-hidden')
    expect(patientPanel).not.toHaveAttribute('inert')
    expect(detailsPanel).toHaveAttribute('aria-hidden', 'true')
    expect(detailsPanel).toHaveAttribute('inert')
  })

  it('keeps only one mobile drawer open at a time', async () => {
    const user = userEvent.setup()

    render(<TreeWorkspace {...mobileProps} />)

    await user.click(screen.getByRole('button', { name: 'Show patient panel' }))
    await user.click(screen.getByRole('button', { name: 'Show details panel' }))

    expect(screen.getByRole('button', { name: 'Show patient panel' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: 'Hide details panel' })).toHaveAttribute('aria-expanded', 'true')
  })

  it('returns focus to the drawer toggle when the backdrop closes it', async () => {
    const user = userEvent.setup()

    render(<TreeWorkspace {...mobileProps} />)

    await user.click(screen.getByRole('button', { name: 'Show patient panel' }))
    await user.click(screen.getByRole('button', { name: 'Close open panel' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Show patient panel' })).toHaveFocus()
    })
    expect(screen.getByRole('button', { name: 'Show patient panel' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('returns focus to the details toggle when Escape closes the drawer', async () => {
    const user = userEvent.setup()

    render(<TreeWorkspace {...mobileProps} />)

    await user.click(screen.getByRole('button', { name: 'Show details panel' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Details action' })).toHaveFocus()
    })

    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Show details panel' })).toHaveFocus()
    })
    expect(screen.getByRole('button', { name: 'Show details panel' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('leaves desktop panels accessible when the mobile layout is inactive', () => {
    matchMediaController.setMatches(false)

    render(<TreeWorkspace {...mobileProps} />)

    expect(document.querySelector('.left-panel')).not.toHaveAttribute('aria-hidden')
    expect(document.querySelector('.left-panel')).not.toHaveAttribute('inert')
    expect(document.querySelector('.side-panels')).not.toHaveAttribute('aria-hidden')
    expect(document.querySelector('.side-panels')).not.toHaveAttribute('inert')
  })
})
