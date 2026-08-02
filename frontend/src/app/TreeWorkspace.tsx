import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from 'lucide-react'
import { lazy, Suspense, useEffect, useState } from 'react'
import type { JsonObject, TreeGraphNode, TreeGraphResponse } from '../api/types'
import type { Theme } from './useTheme'
import { ErrorBoundary } from './ErrorBoundary'
import { GlobalConfigPanel } from '../panels/GlobalConfigPanel'
import { Legend } from '../panels/Legend'
import { MockPatientSidebar } from '../panels/MockPatientSidebar'
import { NodeDetailPanel } from '../panels/NodeDetailPanel'
import { useMediaQuery } from '../hooks/useMediaQuery'

const TreeCanvas = lazy(() => import('../canvas/TreeCanvas').then(({ TreeCanvas: canvas }) => ({ default: canvas })))
const MOBILE_LAYOUT_QUERY = '(max-width: 780px)'

type MobileDrawer = 'patient' | 'details' | null

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
  const [mobileDrawer, setMobileDrawer] = useState<MobileDrawer>(null)
  const { graph, theme } = props
  const isMobile = useMediaQuery(MOBILE_LAYOUT_QUERY)

  useEffect(() => {
    if (!isMobile) {
      setMobileDrawer(null)
    }
  }, [isMobile])

  const toggleMobileDrawer = (drawer: Exclude<MobileDrawer, null>) => {
    setMobileDrawer((current) => (current === drawer ? null : drawer))
  }

  const patientDrawerExpanded = isMobile ? mobileDrawer === 'patient' : !leftCollapsed
  const detailsDrawerExpanded = isMobile ? mobileDrawer === 'details' : !rightCollapsed

  return (
    <main className="app-body">
      <div className={`left-panel ${isMobile && mobileDrawer === 'patient' ? 'mobile-drawer-open' : ''}`} style={{ width: leftCollapsed ? 0 : 280 }}>
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
          onClick={() => setMobileDrawer(null)}
        />
      )}
      <div
        className={`side-panels ${isMobile && mobileDrawer === 'details' ? 'mobile-drawer-open' : ''}`}
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
