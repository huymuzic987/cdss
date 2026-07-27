import { Tldraw } from 'tldraw'
import 'tldraw/tldraw.css'
import type { TreeGraphNode, TreeGraphResponse } from '../api/types'
import { DecisionNodeShapeUtil } from './DecisionNodeShapeUtil'
import { useManualModeClicks } from './useManualModeClicks'
import { useTreeCanvasControls } from './useTreeCanvasControls'
import { useTreeCanvasScene } from './useTreeCanvasScene'
import { useTreeCanvasSync } from './useTreeCanvasSync'

const SHAPE_UTILS = [DecisionNodeShapeUtil]
const HIDDEN_COMPONENTS = {
  Toolbar: null,
  StylePanel: null,
  ActionsMenu: null,
  MainMenu: null,
  PageMenu: null,
  KeyboardShortcutsDialog: null,
  DebugPanel: null,
  DebugMenu: null,
  MenuPanel: null,
  SharePanel: null,
  PeopleMenu: null,
  HelperButtons: null,
  ContextMenu: null,
  QuickActions: null,
  SelectionBackground: null,
}

interface TreeCanvasProps {
  graph: TreeGraphResponse
  theme: 'dark' | 'light'
  focusNodeKey: string | null
  onSelectNode: (node: TreeGraphNode | null) => void
  /** Node keys that were traversed (entered) */
  highlightedNodeKeys?: ReadonlySet<string>
  /** The currently active node being stepped through */
  activeNodeKey?: string | null
  /** When true, an overlay awaits a click to reveal the next manual-traversal step */
  manualMode?: boolean
  manualStepInfo?: { current: number; total: number } | null
  onCanvasClick?: () => void
}

export function TreeCanvas({
  graph,
  theme,
  focusNodeKey,
  onSelectNode,
  highlightedNodeKeys,
  activeNodeKey,
  manualMode,
  manualStepInfo,
  onCanvasClick,
}: TreeCanvasProps) {
  const {
    editorRef,
    shapeIdsRef,
    lastSavedPositionsRef,
    lastSavedArrowKindRef,
    lastSavedEdgeLayoutsRef,
    isSceneLoaded,
    arrowKind,
    setArrowKind,
    handleMount,
  } = useTreeCanvasScene({ graph, theme, focusNodeKey, onSelectNode })

  useTreeCanvasSync({ editorRef, shapeIdsRef, isSceneLoaded, theme, focusNodeKey, highlightedNodeKeys, activeNodeKey })

  const { searchQuery, handleSearch, handleChangeArrowKind, handleResetLayout } = useTreeCanvasControls({
    editorRef,
    shapeIdsRef,
    lastSavedPositionsRef,
    lastSavedArrowKindRef,
    lastSavedEdgeLayoutsRef,
    graph,
    setArrowKind,
  })


  const { handlePointerDownCapture, handlePointerUpCapture, handleClickCapture } = useManualModeClicks(manualMode, onCanvasClick)

  return (
    <div
      className="tree-canvas"
      onPointerDownCapture={handlePointerDownCapture}
      onPointerUpCapture={handlePointerUpCapture}
      onClickCapture={handleClickCapture}
    >
      <div className="canvas-toolbar">
        <div className="canvas-toolbar-search">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(event) => handleSearch(event.target.value)}
          />
        </div>

        <div className="canvas-toolbar-divider" />

        <button type="button" title="Fit to screen" onClick={() => editorRef.current?.zoomToFit({ animation: { duration: 200 } })}>
          Fit
        </button>

        <div className="canvas-toolbar-divider" />

        <div className="canvas-toolbar-group">
          <button
            type="button"
            className={arrowKind === 'straight' ? 'active' : ''}
            title="Straight connectors"
            onClick={() => handleChangeArrowKind('straight')}
          >
            Straight
          </button>
          <button
            type="button"
            className={arrowKind === 'elbow' ? 'active' : ''}
            title="Elbow connectors"
            onClick={() => handleChangeArrowKind('elbow')}
          >
            Elbow
          </button>
        </div>

        <div className="canvas-toolbar-divider" />

        <button type="button" title="Reset layout to default" onClick={handleResetLayout}>
          Reset
        </button>
      </div>
      <Tldraw
        shapeUtils={SHAPE_UTILS}
        components={HIDDEN_COMPONENTS}
        onMount={handleMount}
        licenseKey={import.meta.env.VITE_TLDRAW_LICENSE_KEY}
      />
      {manualMode && (
        <div className="manual-overlay">
          {manualStepInfo && (
            <div className="manual-banner">
              <span className="manual-pulse-dot" />
              <span>
                Manual Traverse: Click canvas to advance (Step{' '}
                <strong>{manualStepInfo.current}</strong> of{' '}
                <strong>{manualStepInfo.total}</strong>)
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
