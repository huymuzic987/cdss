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

function App() {
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
    handleReset,
  } = useTraversal({ ensureGraph, setActiveTreeKey, setFocusNodeKey, setError })

  const { width: rightSidebarWidth, isResizing, handleMouseDown } = useSidebarResize()

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
      <div className="tab-bar">
        {trees.map((tree) => (
          <button
            key={tree.tree_key}
            type="button"
            className={tree.tree_key === activeTreeKey ? 'tab active' : 'tab'}
            onClick={() => handleSelectTab(tree.tree_key)}
          >
            {tree.name_en}
          </button>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="app-body">
        {/* ---- LEFT: Mock Patient Sidebar ---- */}
        <MockPatientSidebar
          isRunning={traversalState === 'running'}
          canReset={traversalState !== 'idle'}
          onStart={(treeKey, input) => {
            void handleStartTraversal(treeKey, input)
          }}
          onReset={handleReset}
        />

        {/* ---- CENTER: Canvas ---- */}
        <div className="canvas-area" style={{ pointerEvents: isResizing ? 'none' : 'auto' }}>
          {activeGraph ? (
            <TreeCanvas
              key={activeGraph.tree.tree_key}
              graph={activeGraph}
              focusNodeKey={focusNodeKey}
              onSelectNode={setSelectedNode}
              highlightedNodeKeys={visibleHighlights}
              activeNodeKey={visibleActiveNode}
            />
          ) : (
            <div className="panel-empty loading">Loading tree…</div>
          )}
        </div>

        {/* ---- RESIZER ---- */}
        <div
          className={`sidebar-resizer ${isResizing ? 'resizing' : ''}`}
          onMouseDown={handleMouseDown}
        />

        {/* ---- RIGHT: Side panels ---- */}
        <div className="side-panels" style={{ width: rightSidebarWidth }}>
          <Legend />
          <NodeDetailPanel
            node={selectedNode}
            references={activeGraph?.references ?? []}
            onJumpToLink={(targetTreeKey, targetNodeKey) => {
              void handleJumpToLink(targetTreeKey, targetNodeKey)
            }}
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
