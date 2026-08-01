import { useEffect, useState } from 'react'

export type ShowcaseTheme = 'dark' | 'light'

const STORAGE_KEY = 'cdss-showcase-theme'

export function useShowcaseTheme() {
  const [theme, setTheme] = useState<ShowcaseTheme>(() =>
    localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark',
  )

  useEffect(() => localStorage.setItem(STORAGE_KEY, theme), [theme])

  return {
    theme,
    toggleTheme: () => setTheme((current) => current === 'dark' ? 'light' : 'dark'),
  }
}

