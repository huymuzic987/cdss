import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import type { JsonObject, TreeGraphNode, TreeGraphResponse } from '../api/types'
import type { Theme } from './useTheme'
import { ErrorBoundary } from './ErrorBoundary'
import { GlobalConfigPanel } from '../panels/GlobalConfigPanel'
import { Legend } from '../panels/Legend'
import { MockPatientSidebar } from '../panels/MockPatientSidebar'
import { NodeDetailPanel } from '../panels/NodeDetailPanel'

const TreeCanvas = lazy(() => import('../canvas/TreeCanvas').then(({ TreeCanvas: canvas }) => ({ default: canvas })))

interface TreeWorkspaceProps {
  graph?: TreeGraphResponse
  theme: Theme
  isRunning: boolean
  canReset: boolean
  sidebarWidth: number
  isResizing: boolean
  onResizeStart: (event: React.MouseEvent) => void
  focusNodeKey: string | null
  selectedNode: TreeGraphNode | null
  highlightedNodeKeys: ReadonlySet<string>
  activeNodeKey: string | null
  manualMode: boolean
  manualStepInfo: { current: number; total: number } | null
  onSelectNode: (node: TreeGraphNode | null) => void
  onJumpToLink: (treeKey: string, nodeKey: string | null) => void
  onStart: (treeKey: string, input: JsonObject) => void
  onManualStart: (treeKey: string, input: JsonObject) => void
  onManualStep: () => void
  onReset: () => void
  onToggleTheme: () => void
}

export function TreeWorkspace(props: TreeWorkspaceProps) {
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const { graph, theme } = props

  return (
    <main className="app-body">
      <div className="left-panel" style={{ width: leftCollapsed ? 0 : 280 }}>
        <MockPatientSidebar
          isRunning={props.isRunning}
          canReset={props.canReset}
          onStart={props.onStart}
          onManualStart={props.onManualStart}
          onReset={props.onReset}
          theme={theme}
          onToggleTheme={props.onToggleTheme}
        />
      </div>
      <button
        type="button"
        className="panel-toggle-btn panel-toggle-left"
        style={{ left: leftCollapsed ? 14 : 280 }}
        onClick={() => setLeftCollapsed((value) => !value)}
        title={leftCollapsed ? 'Show patient panel' : 'Hide patient panel'}
        aria-label={leftCollapsed ? 'Show patient panel' : 'Hide patient panel'}
        aria-expanded={!leftCollapsed}
      >
        {leftCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
      </button>
      <div className="canvas-area" style={{ pointerEvents: props.isResizing ? 'none' : 'auto' }}>
        {graph ? (
          <ErrorBoundary key={graph.tree.tree_key} label="tree canvas">
            <Suspense fallback={<div className="panel-empty loading app-loading" role="status">Loading canvas…</div>}>
              <TreeCanvas
                graph={graph}
                theme={theme}
                focusNodeKey={props.focusNodeKey}
                onSelectNode={props.onSelectNode}
                highlightedNodeKeys={props.highlightedNodeKeys}
                activeNodeKey={props.activeNodeKey}
                manualMode={props.manualMode}
                manualStepInfo={props.manualStepInfo}
                onCanvasClick={props.onManualStep}
              />
            </Suspense>
          </ErrorBoundary>
        ) : <div className="panel-empty loading">Loading tree…</div>}
      </div>
      {!rightCollapsed && (
        <div className={`sidebar-resizer ${props.isResizing ? 'resizing' : ''}`} onMouseDown={props.onResizeStart} />
      )}
      <button
        type="button"
        className="panel-toggle-btn panel-toggle-right"
        style={{ right: rightCollapsed ? 14 : props.sidebarWidth }}
        onClick={() => setRightCollapsed((value) => !value)}
        title={rightCollapsed ? 'Show details panel' : 'Hide details panel'}
        aria-label={rightCollapsed ? 'Show details panel' : 'Hide details panel'}
        aria-expanded={!rightCollapsed}
      >
        {rightCollapsed ? <PanelRightOpen size={16} /> : <PanelRightClose size={16} />}
      </button>
      <div
        className="side-panels"
        style={rightCollapsed
          ? { width: 0, padding: 0, overflow: 'hidden', minWidth: 0 }
          : { width: props.sidebarWidth }}
      >
        <Legend theme={theme} />
        <NodeDetailPanel
          node={props.selectedNode}
          references={graph?.references ?? []}
          onJumpToLink={props.onJumpToLink}
          theme={theme}
        />
        <GlobalConfigPanel globalNodes={graph?.global_nodes ?? []} />
      </div>
    </main>
  )
}
