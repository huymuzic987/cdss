import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import type { JsonObject, TreeGraphNode, TreeGraphResponse } from '../api/types'
import type { Theme } from './useTheme'
import { ErrorBoundary } from './ErrorBoundary'
import { GlobalConfigPanel } from '../panels/GlobalConfigPanel'
import { Legend } from '../panels/Legend'
import { MockPatientSidebar } from '../panels/MockPatientSidebar'
import { NodeDetailPanel } from '../panels/NodeDetailPanel'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { useMobileDrawer } from '../hooks/useMobileDrawer'

const TreeCanvas = lazy(() => import('../canvas/TreeCanvas').then(({ TreeCanvas: canvas }) => ({ default: canvas })))
const MOBILE_LAYOUT_QUERY = '(max-width: 780px)'
const LEFT_SIDEBAR_WIDTH = 320

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
  const isMobile = useMediaQuery(MOBILE_LAYOUT_QUERY)
  const mobileDrawerControls = useMobileDrawer(isMobile)
  const {
    mobileDrawer,
    leftPanelRef,
    rightPanelRef,
    leftToggleRef,
    rightToggleRef,
    closeMobileDrawer,
    toggleMobileDrawer,
    patientDrawerHidden,
    detailsDrawerHidden,
  } = mobileDrawerControls
  const patientDrawerExpanded = isMobile ? mobileDrawer === 'patient' : !leftCollapsed
  const detailsDrawerExpanded = isMobile ? mobileDrawer === 'details' : !rightCollapsed

  return (
    <main className="app-body">
      <div
        ref={leftPanelRef}
        className={`left-panel ${isMobile && mobileDrawer === 'patient' ? 'mobile-drawer-open' : ''}`}
        style={{ width: leftCollapsed ? 0 : LEFT_SIDEBAR_WIDTH }}
        aria-hidden={patientDrawerHidden ? true : undefined}
        inert={patientDrawerHidden ? true : undefined}
      >
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
        ref={leftToggleRef}
        type="button"
        className="panel-toggle-btn panel-toggle-left"
        style={{ left: leftCollapsed ? 14 : LEFT_SIDEBAR_WIDTH }}
        onClick={() => {
          if (isMobile) {
            toggleMobileDrawer('patient')
            return
          }

          setLeftCollapsed((value) => !value)
        }}
        title={patientDrawerExpanded ? 'Hide patient panel' : 'Show patient panel'}
        aria-label={patientDrawerExpanded ? 'Hide patient panel' : 'Show patient panel'}
        aria-expanded={patientDrawerExpanded}
      >
        {patientDrawerExpanded ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
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
      {!isMobile && !rightCollapsed && (
        <div className={`sidebar-resizer ${props.isResizing ? 'resizing' : ''}`} onMouseDown={props.onResizeStart} />
      )}
      <button
        ref={rightToggleRef}
        type="button"
        className="panel-toggle-btn panel-toggle-right"
        style={{ right: rightCollapsed ? 14 : props.sidebarWidth }}
        onClick={() => {
          if (isMobile) {
            toggleMobileDrawer('details')
            return
          }

          setRightCollapsed((value) => !value)
        }}
        title={detailsDrawerExpanded ? 'Hide details panel' : 'Show details panel'}
        aria-label={detailsDrawerExpanded ? 'Hide details panel' : 'Show details panel'}
        aria-expanded={detailsDrawerExpanded}
      >
        {detailsDrawerExpanded ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
      </button>
      {isMobile && mobileDrawer !== null && (
        <button
          type="button"
          className="mobile-drawer-backdrop"
          aria-label="Close open panel"
          onClick={() => closeMobileDrawer(mobileDrawer)}
        />
      )}
      <div
        ref={rightPanelRef}
        className={`side-panels ${isMobile && mobileDrawer === 'details' ? 'mobile-drawer-open' : ''}`}
        style={rightCollapsed
          ? { width: 0, padding: 0, overflow: 'hidden', minWidth: 0 }
          : { width: props.sidebarWidth }}
        aria-hidden={detailsDrawerHidden ? true : undefined}
        inert={detailsDrawerHidden ? true : undefined}
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
