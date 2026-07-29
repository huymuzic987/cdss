import { useState } from 'react'
import { TreeTabs } from './app/TreeTabs'
import { TreeWorkspace } from './app/TreeWorkspace'
import { useTheme } from './app/useTheme'
import { DashboardPage } from './dashboard/DashboardPage'
import { useSidebarResize } from './hooks/useSidebarResize'
import { useTraversal } from './hooks/useTraversal'
import { useTreeGraphs } from './hooks/useTreeGraphs'
import { DrugToleranceCheckbox } from './panels/DrugToleranceCheckbox'
import { TraversalResultModal } from './panels/TraversalResultModal'
import './App.css'

function App() {
  const { theme, toggleTheme } = useTheme()
  const [showDashboard, setShowDashboard] = useState(false)
  const graphs = useTreeGraphs()
  const traversal = useTraversal({
    ensureGraph: graphs.ensureGraph,
    setActiveTreeKey: graphs.setActiveTreeKey,
    setFocusNodeKey: graphs.setFocusNodeKey,
    setError: graphs.setError,
  })
  const sidebar = useSidebarResize()

  const visibleTrees = traversal.traversalState === 'idle'
    ? graphs.trees
    : graphs.trees.filter(
      (tree) => tree.tree_key === traversal.activeTraversalTreeKey
        || traversal.highlightedNodeKeys[tree.tree_key],
    )
  const visibleHighlights = graphs.activeTreeKey
    ? traversal.highlightedNodeKeys[graphs.activeTreeKey] ?? new Set<string>()
    : new Set<string>()
  const visibleActiveNode = graphs.activeTreeKey === traversal.activeTraversalTreeKey
    && traversal.traversalState !== 'idle'
    ? traversal.activeNodeKey
    : null

  return (
    <div className="app">
      <TreeTabs
        trees={visibleTrees}
        activeTreeKey={graphs.activeTreeKey}
        showDashboard={showDashboard}
        onShowDashboard={() => setShowDashboard(true)}
        onSelectTree={(treeKey) => {
          setShowDashboard(false)
          graphs.handleSelectTab(treeKey)
        }}
      />

      {graphs.error && !showDashboard && <div className="error-banner">{graphs.error}</div>}
      {showDashboard ? (
        <div className="app-body"><DashboardPage /></div>
      ) : (
        <TreeWorkspace
          graph={graphs.activeGraph}
          theme={theme}
          isRunning={traversal.traversalState === 'running'}
          canReset={traversal.traversalState !== 'idle'}
          sidebarWidth={sidebar.width}
          isResizing={sidebar.isResizing}
          onResizeStart={sidebar.handleMouseDown}
          focusNodeKey={graphs.focusNodeKey}
          selectedNode={graphs.selectedNode}
          highlightedNodeKeys={visibleHighlights}
          activeNodeKey={visibleActiveNode}
          manualMode={traversal.manualMode}
          manualStepInfo={traversal.manualStepInfo}
          onSelectNode={graphs.setSelectedNode}
          onJumpToLink={(treeKey, nodeKey) => void graphs.handleJumpToLink(treeKey, nodeKey)}
          onStart={(treeKey, input) => void traversal.handleStartTraversal(treeKey, input)}
          onManualStart={(treeKey, input) => void traversal.handleStartManualTraversal(treeKey, input)}
          onManualStep={traversal.handleManualStep}
          onReset={traversal.handleReset}
          onToggleTheme={toggleTheme}
        />
      )}

      {traversal.showModal && (
        <TraversalResultModal
          result={traversal.modalResult}
          partial={traversal.modalPartial}
          onClose={() => traversal.setShowModal(false)}
        />
      )}
      {traversal.showDrugTolerancePopup && (
        <DrugToleranceCheckbox
          onConfirm={traversal.handleDrugToleranceConfirm}
          onCancel={traversal.handleDrugToleranceCancel}
          onChange={traversal.handleDrugToleranceChange}
        />
      )}
    </div>
  )
}

export default App
