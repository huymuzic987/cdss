import { lazy, Suspense, useEffect, useState } from 'react'

import { TreeTabs } from './app/TreeTabs'
import { TreeWorkspace } from './app/TreeWorkspace'
import { useTheme } from './app/useTheme'
import { useSidebarResize } from './hooks/useSidebarResize'
import { useTraversal } from './hooks/useTraversal'
import { useTreeGraphs } from './hooks/useTreeGraphs'
import { DrugToleranceCheckbox } from './panels/DrugToleranceCheckbox'
import { EmergencyScenarioCheckbox } from './panels/EmergencyScenarioCheckbox'
import './App.css'

const DashboardPage = lazy(() => import('./dashboard/DashboardPage').then(({ DashboardPage: page }) => ({ default: page })))
const ShowcasePage = lazy(() => import('./showcase/ShowcasePage').then(({ ShowcasePage: page }) => ({ default: page })))
const TraversalResultModal = lazy(() => import('./panels/TraversalResultModal').then(({ TraversalResultModal: modal }) => ({ default: modal })))
const ContributionPage = lazy(() => import('./contribution/ContributionPage').then(({ ContributionPage: page }) => ({ default: page })))

// Stable identity so an idle render (no highlighted nodes) doesn't hand
// TreeCanvas a brand-new Set every time, which would otherwise re-trigger its
// highlight-sync effect on every unrelated App re-render.
const EMPTY_HIGHLIGHTS: ReadonlySet<string> = new Set()

function getInitialView(): 'tree' | 'dashboard' | 'contribution' {
  const path = window.location.pathname
  const hash = window.location.hash
  if (path === '/contribution' || hash === '#contribution' || hash === '#/contribution') return 'contribution'
  if (path === '/dashboard' || hash === '#dashboard' || hash === '#/dashboard') return 'dashboard'
  return 'tree'
}

function WorkbenchApp() {
  const { theme, toggleTheme } = useTheme()
  const [viewMode, setViewMode] = useState<'tree' | 'dashboard' | 'contribution'>(getInitialView)
  const graphs = useTreeGraphs()
  const traversal = useTraversal({
    ensureGraph: graphs.ensureGraph,
    setActiveTreeKey: graphs.setActiveTreeKey,
    setFocusNodeKey: graphs.setFocusNodeKey,
    setError: graphs.setError,
  })
  const sidebar = useSidebarResize()

  useEffect(() => {
    const handlePopState = () => setViewMode(getInitialView())
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigateTo = (mode: 'tree' | 'dashboard' | 'contribution', treeKey?: string) => {
    setViewMode(mode)
    if (mode === 'contribution') {
      window.history.pushState({}, '', '/contribution')
    } else if (mode === 'dashboard') {
      window.history.pushState({}, '', '/dashboard')
    } else if (treeKey) {
      window.history.pushState({}, '', '/')
      graphs.handleSelectTab(treeKey)
    } else {
      window.history.pushState({}, '', '/')
    }
  }

  const visibleTrees = traversal.traversalState === 'idle'
    ? graphs.trees
    : graphs.trees.filter(
      (tree) => tree.tree_key === traversal.activeTraversalTreeKey
        || traversal.highlightedNodeKeys[tree.tree_key],
    )
  const visibleHighlights = graphs.activeTreeKey
    ? traversal.highlightedNodeKeys[graphs.activeTreeKey] ?? EMPTY_HIGHLIGHTS
    : EMPTY_HIGHLIGHTS
  const visibleActiveNode = graphs.activeTreeKey === traversal.activeTraversalTreeKey
    && traversal.traversalState !== 'idle'
    ? traversal.activeNodeKey
    : null

  return (
    <div className="app">
      {viewMode === 'tree' && (
        <TreeTabs
          trees={visibleTrees}
          activeTreeKey={graphs.activeTreeKey}
          onSelectTree={(treeKey) => navigateTo('tree', treeKey)}
        />
      )}




      {graphs.error && viewMode === 'tree' && <div className="error-banner">{graphs.error}</div>}
      {viewMode === 'contribution' ? (
        <main className="app-body overflow-y-auto">
          <Suspense fallback={<LoadingState label="Loading contributions…" />}>
            <ContributionPage />
          </Suspense>
        </main>
      ) : viewMode === 'dashboard' ? (
        <main className="app-body">
          <Suspense fallback={<LoadingState label="Loading dashboard…" />}>
            <DashboardPage />
          </Suspense>
        </main>
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
        <Suspense fallback={null}>
          <TraversalResultModal
            result={traversal.modalResult}
            partial={traversal.modalPartial}
            graphs={graphs.graphCache}
            onClose={() => traversal.setShowModal(false)}
          />
        </Suspense>
      )}
      {traversal.showDrugTolerancePopup && (
        traversal.checkpointKind === 'emergency'
          ? <EmergencyScenarioCheckbox onConfirm={traversal.handleEmergencyScenarioConfirm} onCancel={traversal.handleDrugToleranceCancel} />
          : <DrugToleranceCheckbox onConfirm={traversal.handleDrugToleranceConfirm} onCancel={traversal.handleDrugToleranceCancel} onChange={traversal.handleDrugToleranceChange} />
      )}
      {traversal.checkpointPending && !traversal.showDrugTolerancePopup && traversal.traversalState === 'running' && (
        <button className="checkpoint-reopen" type="button" onClick={traversal.reopenCheckpoint}>
          Reopen checkpoint
        </button>
      )}
    </div>
  )
}

function LoadingState({ label }: { label: string }) {
  return <div className="app-loading" role="status" aria-live="polite">{label}</div>
}

function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  return path === '/showcase'
    ? <Suspense fallback={<LoadingState label="Loading showcase…" />}><ShowcasePage /></Suspense>
    : <WorkbenchApp />
}

export default App
