import { useEffect } from 'react'

const POPUP_SELECTOR = [
  '.cds-regimen-catalog-details',
  '.cds-regimen-row-tooltip',
  '.cds-regimen-component',
  '.cds-regimen-option-title',
].join(', ')

export function useRegimenPopupDismissal(open: boolean, onDismiss: () => void): void {
  useEffect(() => {
    if (!open) return
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target
      if (!(target instanceof Element) || target.closest(POPUP_SELECTOR)) return
      onDismiss()
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [onDismiss, open])
}
