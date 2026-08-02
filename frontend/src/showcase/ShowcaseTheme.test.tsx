// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { ShowcasePage } from './ShowcasePage'

beforeEach(() => localStorage.clear())
afterEach(cleanup)

describe('showcase theme', () => {
  it('uses dark mode by default', () => {
    const { container } = render(<ShowcasePage />)
    expect(container.firstElementChild).toHaveAttribute('data-showcase-theme', 'dark')
    expect(screen.getByRole('button', { name: 'Switch to light theme' })).toBeTruthy()
  })

  it('toggles to light mode and persists the choice', async () => {
    const user = userEvent.setup()
    const { container } = render(<ShowcasePage />)
    await user.click(screen.getByRole('button', { name: 'Switch to light theme' }))

    expect(container.firstElementChild).toHaveAttribute('data-showcase-theme', 'light')
    expect(screen.getByRole('button', { name: 'Switch to dark theme' })).toBeTruthy()
    expect(localStorage.getItem('cdss-showcase-theme')).toBe('light')
  })
})

