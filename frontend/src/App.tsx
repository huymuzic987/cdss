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
    return saved === 'dark' ? 'dark' : 'light'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('cdss-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'))

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

  // While a traversal is running or done, only show tabs for trees touched by
  // the path (plus the tree the traversal is currently/last in). Resetting
  // (traversalState -> 'idle') brings back the full tree list.
  const visibleTrees =
    traversalState === 'idle'
      ? trees
      : trees.filter(
          (tree) => tree.tree_key === activeTraversalTreeKey || highlightedNodeKeys[tree.tree_key],
        )

  useEffect(() => {
    updateTabsScrollState()
    const el = tabsScrollRef.current
    if (!el) return
    const observer = new ResizeObserver(updateTabsScrollState)
    observer.observe(el)
    return () => observer.disconnect()
  }, [visibleTrees])

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
          {visibleTrees.map((tree) => (
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
            theme={theme}
            onToggleTheme={toggleTheme}
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
