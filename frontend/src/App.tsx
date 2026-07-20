import { useEffect, useRef, useState } from 'react'
import { TreeCanvas } from './canvas/TreeCanvas'
import { useSidebarResize } from './hooks/useSidebarResize'
import { useTraversal } from './hooks/useTraversal'
import { useTreeGraphs } from './hooks/useTreeGraphs'
import { GlobalConfigPanel } from './panels/GlobalConfigPanel'
import { Legend } from './panels/Legend'
import { MockPatientSidebar } from './panels/MockPatientSidebar'
import { NodeDetailPanel } from './panels/NodeDetailPanel'
import { TraversalResultModal } from './panels/TraversalResultModal'
import './App.css'

type Theme = 'dark' | 'light'

function App() {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('cdss-theme')
    return saved === 'light' ? 'light' : 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('cdss-theme', theme)
  }, [theme])

  const [showSettings, setShowSettings] = useState(false)
  const settingsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!showSettings) return
    const handleClickOutside = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false)
      }
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowSettings(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [showSettings])

  const {
    trees,
    activeTreeKey,
    setActiveTreeKey,
    focusNodeKey,
    selectedNode,
    setSelectedNode,
    error,
    activeGraph,
    ensureGraph,
    handleSelectTab,
    handleJumpToLink,
    setError,
    setFocusNodeKey,
  } = useTreeGraphs()

  const {
    traversalState,
    highlightedNodeKeys,
    activeNodeKey,
    activeTraversalTreeKey,
    modalResult,
    modalPartial,
    showModal,
    setShowModal,
    handleStartTraversal,
    handleStartManualTraversal,
    handleManualStep,
    manualMode,
    manualStepInfo,
    handleReset,
  } = useTraversal({ ensureGraph, setActiveTreeKey, setFocusNodeKey, setError })

  const { width: rightSidebarWidth, isResizing, handleMouseDown } = useSidebarResize()

  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)

  const tabsScrollRef = useRef<HTMLDivElement>(null)
  const [canScrollTabsLeft, setCanScrollTabsLeft] = useState(false)
  const [canScrollTabsRight, setCanScrollTabsRight] = useState(false)

  const updateTabsScrollState = () => {
    const el = tabsScrollRef.current
    if (!el) return
    setCanScrollTabsLeft(el.scrollLeft > 2)
    setCanScrollTabsRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 2)
  }

  useEffect(() => {
    updateTabsScrollState()
    const el = tabsScrollRef.current
    if (!el) return
    const observer = new ResizeObserver(updateTabsScrollState)
    observer.observe(el)
    return () => observer.disconnect()
  }, [trees])

  const scrollTabs = (direction: -1 | 1) => {
    tabsScrollRef.current?.scrollBy({ left: direction * 180, behavior: 'smooth' })
  }

  const handleTabsWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const el = tabsScrollRef.current
    if (!el) return
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      el.scrollLeft += e.deltaY
    }
  }

  // Only pass highlight props when the active tab matches the traversal tree
  const isTraversalTab = activeTreeKey === activeTraversalTreeKey
  const visibleHighlights =
    activeTreeKey && highlightedNodeKeys[activeTreeKey]
      ? highlightedNodeKeys[activeTreeKey]
      : new Set<string>()
  const visibleActiveNode =
    isTraversalTab && traversalState !== 'idle' ? activeNodeKey : null

  return (
    <div className="app">
      {/* ---- Top bar ---- */}
      <div className="top-bar">
        <div className="top-bar-brand">
          <span className="top-bar-title">Hypertension CDSS</span>
          <span className="top-bar-subtitle">Clinical Decision Support</span>
        </div>
        <div className="top-bar-actions" ref={settingsRef}>
          <button
            type="button"
            className={`settings-btn${showSettings ? ' active' : ''}`}
            onClick={() => setShowSettings((v) => !v)}
            title="Settings"
            aria-label="Settings"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>

          {showSettings && (
            <div className="settings-popover" role="dialog" aria-label="Settings">
              <div className="settings-section-label">Appearance</div>
              <div className="settings-theme-group">
                <button
                  type="button"
                  className={`settings-theme-btn${theme === 'light' ? ' active' : ''}`}
                  onClick={() => setTheme('light')}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="4"/>
                    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
                  </svg>
                  Light
                </button>
                <button
                  type="button"
                  className={`settings-theme-btn${theme === 'dark' ? ' active' : ''}`}
                  onClick={() => setTheme('dark')}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                  </svg>
                  Dark
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ---- Tree tabs ---- */}
      <div className="top-tabs-wrap">
        {canScrollTabsLeft && (
          <button
            type="button"
            className="tab-scroll-btn tab-scroll-left"
            onClick={() => scrollTabs(-1)}
            aria-label="Scroll tabs left"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
        )}
        <div
          className="top-tabs-bar"
          ref={tabsScrollRef}
          onScroll={updateTabsScrollState}
          onWheel={handleTabsWheel}
        >
          {trees.map((tree) => (
            <button
              key={tree.tree_key}
              type="button"
              className={`top-tab${activeTreeKey === tree.tree_key ? ' active' : ''}`}
              onClick={() => handleSelectTab(tree.tree_key)}
              title={tree.name_en}
            >
              {tree.name_en}
            </button>
          ))}
        </div>
        {canScrollTabsRight && (
          <button
            type="button"
            className="tab-scroll-btn tab-scroll-right"
            onClick={() => scrollTabs(1)}
            aria-label="Scroll tabs right"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="app-body">
        {/* ---- LEFT: Patient Simulator ---- */}
        <div className="left-panel" style={{ width: leftCollapsed ? 0 : 280 }}>
          <MockPatientSidebar
            isRunning={traversalState === 'running'}
            canReset={traversalState !== 'idle'}
            onStart={(treeKey, input) => {
              void handleStartTraversal(treeKey, input)
            }}
            onManualStart={(treeKey, input) => {
              void handleStartManualTraversal(treeKey, input)
            }}
            onReset={handleReset}
          />
        </div>

        {/* ---- LEFT COLLAPSE TOGGLE ---- */}
        <button
          type="button"
          className="panel-toggle-btn"
          onClick={() => setLeftCollapsed((v) => !v)}
          title={leftCollapsed ? 'Expand left panel' : 'Collapse left panel'}
          aria-label={leftCollapsed ? 'Expand left panel' : 'Collapse left panel'}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {leftCollapsed
              ? <path d="M4 2l4 4-4 4"/>
              : <path d="M8 2L4 6l4 4"/>
            }
          </svg>
        </button>

        {/* ---- CENTER: Canvas ---- */}
        <div className="canvas-area" style={{ pointerEvents: isResizing ? 'none' : 'auto' }}>
          {activeGraph ? (
            <TreeCanvas
              key={activeGraph.tree.tree_key}
              graph={activeGraph}
              theme={theme}
              focusNodeKey={focusNodeKey}
              onSelectNode={setSelectedNode}
              highlightedNodeKeys={visibleHighlights}
              activeNodeKey={visibleActiveNode}
              manualMode={manualMode}
              manualStepInfo={manualStepInfo}
              onCanvasClick={handleManualStep}
            />
          ) : (
            <div className="panel-empty loading">Loading tree…</div>
          )}
        </div>

        {/* ---- RESIZER ---- */}
        {!rightCollapsed && (
          <div
            className={`sidebar-resizer ${isResizing ? 'resizing' : ''}`}
            onMouseDown={handleMouseDown}
          />
        )}

        {/* ---- RIGHT COLLAPSE TOGGLE ---- */}
        <button
          type="button"
          className="panel-toggle-btn"
          onClick={() => setRightCollapsed((v) => !v)}
          title={rightCollapsed ? 'Expand right panel' : 'Collapse right panel'}
          aria-label={rightCollapsed ? 'Expand right panel' : 'Collapse right panel'}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {rightCollapsed
              ? <path d="M8 2L4 6l4 4"/>
              : <path d="M4 2l4 4-4 4"/>
            }
          </svg>
        </button>

        {/* ---- RIGHT: Side panels ---- */}
        <div
          className="side-panels"
          style={rightCollapsed
            ? { width: 0, padding: 0, overflow: 'hidden', minWidth: 0 }
            : { width: rightSidebarWidth }
          }
        >
          <Legend theme={theme} />
          <NodeDetailPanel
            node={selectedNode}
            references={activeGraph?.references ?? []}
            onJumpToLink={(targetTreeKey, targetNodeKey) => {
              void handleJumpToLink(targetTreeKey, targetNodeKey)
            }}
            theme={theme}
          />
          <GlobalConfigPanel globalNodes={activeGraph?.global_nodes ?? []} />
        </div>
      </div>

      {/* ---- Result modal ---- */}
      {showModal && (
        <TraversalResultModal
          result={modalResult}
          partial={modalPartial}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}

export default App
