import { useCallback, useEffect, useRef, useState } from 'react'
import { evaluateTree, fetchTreeGraph, fetchTrees } from './api/client'
import type {
  ApiErrorResponse,
  EvaluationResponse,
  JsonObject,
  TraversalTraceEntry,
  TreeGraphNode,
  TreeGraphResponse,
  TreeSummary,
} from './api/types'
import { TreeCanvas } from './canvas/TreeCanvas'
import { GlobalConfigPanel } from './panels/GlobalConfigPanel'
import { Legend } from './panels/Legend'
import { MockPatientSidebar } from './panels/MockPatientSidebar'
import { NodeDetailPanel } from './panels/NodeDetailPanel'
import { TraversalResultModal } from './panels/TraversalResultModal'
import './App.css'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TraversalState = 'idle' | 'running' | 'done'

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

function App() {
  // ---- Tree data ----
  const [trees, setTrees] = useState<TreeSummary[]>([])
  const [activeTreeKey, setActiveTreeKey] = useState<string | null>(null)
  const [graphCache, setGraphCache] = useState<Record<string, TreeGraphResponse>>({})
  const [focusNodeKey, setFocusNodeKey] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<TreeGraphNode | null>(null)
  const [error, setError] = useState<string | null>(null)

  // ---- Traversal simulation ----
  const [traversalState, setTraversalState] = useState<TraversalState>('idle')
  const [highlightedNodeKeys, setHighlightedNodeKeys] = useState<Record<string, ReadonlySet<string>>>({})
  const [activeNodeKey, setActiveNodeKey] = useState<string | null>(null)
  const [activeTraversalTreeKey, setActiveTraversalTreeKey] = useState<string | null>(null)

  // ---- Result modal ----
  const [modalResult, setModalResult] = useState<EvaluationResponse | null>(null)
  const [modalPartial, setModalPartial] = useState<ApiErrorResponse | null>(null)
  const [showModal, setShowModal] = useState(false)

  // Ref to abort in-flight animation
  const cancelRef = useRef(false)

  // ---- Sidebar resizing ----
  const [rightSidebarWidth, setRightSidebarWidth] = useState(320)
  const [isResizing, setIsResizing] = useState(false)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX
      // Constrain sidebar width between 240px and 600px
      if (newWidth >= 240 && newWidth <= 600) {
        setRightSidebarWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  // ---- Initial load ----
  useEffect(() => {
    const TRAVERSAL_ORDER = [
      'hypertension-diagnosis',
      'risk-classification',
      'treatment-threshold-and-bp-target',
      'essential-treatment-strategy',
      'optimal-treatment-strategy',
    ]

    fetchTrees()
      .then((summaries) => {
        const ordered = [...summaries].sort((a, b) => {
          const idxA = TRAVERSAL_ORDER.indexOf(a.tree_key)
          const idxB = TRAVERSAL_ORDER.indexOf(b.tree_key)
          const valA = idxA === -1 ? 999 : idxA
          const valB = idxB === -1 ? 999 : idxB
          return valA - valB
        })
        setTrees(ordered)
        setActiveTreeKey(ordered[0]?.tree_key ?? null)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  // ---- Lazy-load graph when switching tabs ----
  useEffect(() => {
    if (!activeTreeKey || graphCache[activeTreeKey]) return
    fetchTreeGraph(activeTreeKey)
      .then((graph) => setGraphCache((prev) => ({ ...prev, [activeTreeKey]: graph })))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [activeTreeKey, graphCache])

  // ---- Jump-to-link (from node detail panel) ----
  const handleJumpToLink = useCallback(
    async (targetTreeKey: string, targetNodeKey: string | null) => {
      let targetGraph = graphCache[targetTreeKey]
      if (!targetGraph) {
        try {
          targetGraph = await fetchTreeGraph(targetTreeKey)
          setGraphCache((prev) => ({ ...prev, [targetTreeKey]: targetGraph }))
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err))
          return
        }
      }
      setActiveTreeKey(targetTreeKey)
      setFocusNodeKey(targetNodeKey ?? targetGraph.start_node_key)
    },
    [graphCache],
  )

  const handleSelectTab = (treeKey: string) => {
    setActiveTreeKey(treeKey)
    setFocusNodeKey(null)
    setSelectedNode(null)
  }

  // ---- Ensure a tree graph is loaded (used during simulation) ----
  const ensureGraph = useCallback(
    async (treeKey: string): Promise<TreeGraphResponse | null> => {
      if (graphCache[treeKey]) return graphCache[treeKey]
      try {
        const graph = await fetchTreeGraph(treeKey)
        setGraphCache((prev) => ({ ...prev, [treeKey]: graph }))
        return graph
      } catch {
        return null
      }
    },
    [graphCache],
  )

  // ---- SIMULATION ENGINE ----
  const handleStartTraversal = useCallback(
    async (startTreeKey: string, input: JsonObject): Promise<void> => {
      cancelRef.current = false
      setTraversalState('running')
      setHighlightedNodeKeys({})
      setActiveNodeKey(null)
      setActiveTraversalTreeKey(startTreeKey)
      setError(null)
      setShowModal(false)

      // Ensure starting graph is loaded & switch to its tab
      await ensureGraph(startTreeKey)
      if (cancelRef.current) return
      setActiveTreeKey(startTreeKey)

      // Call /evaluate
      const { result, partial, error: evalError } = await evaluateTree({ start_tree_key: startTreeKey, input })

      if (cancelRef.current) return

      if (evalError) {
        setError(evalError.message)
        setTraversalState('idle')
        return
      }

      const traceLog: TraversalTraceEntry[] =
        result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []

      // Preload all graphs in the path
      const uniqueTreeKeys = Array.from(new Set(traceLog.map((entry) => entry.tree_key)))
      await Promise.all(uniqueTreeKeys.map((key) => ensureGraph(key)))

      if (cancelRef.current) return

      // Group all entered nodes by tree key
      const enteredByTree: Record<string, Set<string>> = {}
      for (const entry of traceLog) {
        if (entry.event === 'node_entered') {
          if (!enteredByTree[entry.tree_key]) {
            enteredByTree[entry.tree_key] = new Set()
          }
          enteredByTree[entry.tree_key].add(entry.node_key)
        }
      }

      // Update the full highlighted set for all trees
      const newHighlights: Record<string, ReadonlySet<string>> = {}
      for (const [treeKey, nodeSet] of Object.entries(enteredByTree)) {
        newHighlights[treeKey] = nodeSet
      }
      setHighlightedNodeKeys(newHighlights)

      // Find the last entered node
      const lastEntry = [...traceLog].reverse().find((e) => e.event === 'node_entered')
      if (lastEntry) {
        setActiveTraversalTreeKey(lastEntry.tree_key)
        setActiveTreeKey(lastEntry.tree_key)
        setActiveNodeKey(lastEntry.node_key)
        setFocusNodeKey(lastEntry.node_key)
      } else {
        setActiveNodeKey(null)
      }

      setTraversalState('done')

      // Show result modal
      setModalResult(result)
      setModalPartial(partial)
      setShowModal(true)
    },
    [ensureGraph],
  )

  const handleReset = () => {
    cancelRef.current = true
    setTraversalState('idle')
    setHighlightedNodeKeys({})
    setActiveNodeKey(null)
    setActiveTraversalTreeKey(null)
    setShowModal(false)
    setFocusNodeKey(null)
  }

  // ---- Derived ----
  const activeGraph = activeTreeKey ? graphCache[activeTreeKey] : undefined

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
