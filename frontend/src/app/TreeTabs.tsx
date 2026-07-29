import { useEffect, useRef, useState } from 'react'
import type { TreeSummary } from '../api/types'

interface TreeTabsProps {
  trees: TreeSummary[]
  activeTreeKey: string | null
  showDashboard: boolean
  onShowDashboard: () => void
  onSelectTree: (treeKey: string) => void
}

function ScrollArrow({ direction, onClick }: { direction: -1 | 1; onClick: () => void }) {
  const label = direction < 0 ? 'Scroll tabs left' : 'Scroll tabs right'
  return (
    <button
      type="button"
      className={`tab-scroll-btn tab-scroll-${direction < 0 ? 'left' : 'right'}`}
      onClick={onClick}
      aria-label={label}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d={direction < 0 ? 'M15 18l-6-6 6-6' : 'M9 18l6-6-6-6'} />
      </svg>
    </button>
  )
}

export function TreeTabs({ trees, activeTreeKey, showDashboard, onShowDashboard, onSelectTree }: TreeTabsProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const updateScrollState = () => {
    const element = scrollRef.current
    if (!element) return
    setCanScrollLeft(element.scrollLeft > 2)
    setCanScrollRight(element.scrollLeft + element.clientWidth < element.scrollWidth - 2)
  }

  useEffect(() => {
    updateScrollState()
    const element = scrollRef.current
    if (!element) return
    const observer = new ResizeObserver(updateScrollState)
    observer.observe(element)
    return () => observer.disconnect()
  }, [trees])

  const scroll = (direction: -1 | 1) =>
    scrollRef.current?.scrollBy({ left: direction * 180, behavior: 'smooth' })

  return (
    <div className="top-tabs-wrap">
      {canScrollLeft && <ScrollArrow direction={-1} onClick={() => scroll(-1)} />}
      <div
        className="top-tabs-bar"
        ref={scrollRef}
        onScroll={updateScrollState}
        onWheel={(event) => {
          const element = scrollRef.current
          if (element && Math.abs(event.deltaY) > Math.abs(event.deltaX)) element.scrollLeft += event.deltaY
        }}
      >
        <button type="button" className={`top-tab dashboard-tab${showDashboard ? ' active' : ''}`} onClick={onShowDashboard}>
          Dashboard
        </button>
        {trees.map((tree) => (
          <button
            key={tree.tree_key}
            type="button"
            className={`top-tab${!showDashboard && activeTreeKey === tree.tree_key ? ' active' : ''}`}
            onClick={() => onSelectTree(tree.tree_key)}
            title={tree.name_en}
          >
            {tree.name_en}
          </button>
        ))}
      </div>
      {canScrollRight && <ScrollArrow direction={1} onClick={() => scroll(1)} />}
    </div>
  )
}
