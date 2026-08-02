import { useCallback, useEffect, useRef, useState } from 'react'

type MobileDrawer = 'patient' | 'details' | null
type OpenMobileDrawer = Exclude<MobileDrawer, null>

const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

export function useMobileDrawer(isMobile: boolean) {
  const [mobileDrawer, setMobileDrawer] = useState<MobileDrawer>(null)
  const leftPanelRef = useRef<HTMLDivElement>(null)
  const rightPanelRef = useRef<HTMLDivElement>(null)
  const leftToggleRef = useRef<HTMLButtonElement>(null)
  const rightToggleRef = useRef<HTMLButtonElement>(null)
  const focusReturnDrawerRef = useRef<OpenMobileDrawer | null>(null)

  useEffect(() => {
    if (!isMobile) {
      focusReturnDrawerRef.current = null
      setMobileDrawer(null)
    }
  }, [isMobile])

  const closeMobileDrawer = useCallback((drawer: OpenMobileDrawer) => {
    focusReturnDrawerRef.current = drawer
    setMobileDrawer(null)
  }, [])

  const toggleMobileDrawer = useCallback((drawer: OpenMobileDrawer) => {
    setMobileDrawer((current) => {
      if (current === drawer) {
        focusReturnDrawerRef.current = drawer
        return null
      }

      return drawer
    })
  }, [])

  useEffect(() => {
    if (!isMobile) {
      return
    }

    if (mobileDrawer === null) {
      const returnDrawer = focusReturnDrawerRef.current

      if (returnDrawer === 'patient') {
        leftToggleRef.current?.focus()
      } else if (returnDrawer === 'details') {
        rightToggleRef.current?.focus()
      }

      focusReturnDrawerRef.current = null
      return
    }

    const activePanel = mobileDrawer === 'patient' ? leftPanelRef.current : rightPanelRef.current
    activePanel?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)?.focus()
  }, [isMobile, mobileDrawer])

  useEffect(() => {
    if (!isMobile || mobileDrawer === null) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') {
        return
      }

      event.preventDefault()
      closeMobileDrawer(mobileDrawer)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closeMobileDrawer, isMobile, mobileDrawer])

  return {
    mobileDrawer,
    leftPanelRef,
    rightPanelRef,
    leftToggleRef,
    rightToggleRef,
    closeMobileDrawer,
    toggleMobileDrawer,
    patientDrawerExpanded: isMobile ? mobileDrawer === 'patient' : undefined,
    detailsDrawerExpanded: isMobile ? mobileDrawer === 'details' : undefined,
    patientDrawerHidden: isMobile && mobileDrawer !== 'patient',
    detailsDrawerHidden: isMobile && mobileDrawer !== 'details',
  }
}
