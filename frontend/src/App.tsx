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
  const STEP_MS = 500 // fixed step speed
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

      if (evalError) {
        setError(evalError.message)
        setTraversalState('idle')
        return
      }

      const traceLog: TraversalTraceEntry[] =
        result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []

      // Step through the trace entries
      const enteredByTree: Record<string, Set<string>> = {}
      let currentTreeKey = startTreeKey

      const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms))

      for (const entry of traceLog) {
        if (cancelRef.current) break

        // If tree switches, switch the tab first
        if (entry.tree_key !== currentTreeKey) {
          currentTreeKey = entry.tree_key
          setActiveTraversalTreeKey(currentTreeKey)

          // Ensure new tree's graph is loaded
          await ensureGraph(currentTreeKey)
          if (cancelRef.current) break

          setActiveTreeKey(currentTreeKey)
          // Wait a tick for the canvas to mount
          await sleep(220)
          if (cancelRef.current) break
        }

        if (entry.event === 'node_entered') {
          // Light up this node as active
          setActiveNodeKey(entry.node_key)
          setFocusNodeKey(entry.node_key)

          // Track it as entered for the current tree
          if (!enteredByTree[currentTreeKey]) {
            enteredByTree[currentTreeKey] = new Set()
          }
          enteredByTree[currentTreeKey].add(entry.node_key)

          // Update the full highlighted set for this tree
          setHighlightedNodeKeys((prev) => ({
            ...prev,
            [currentTreeKey]: new Set(enteredByTree[currentTreeKey]),
          }))

          await sleep(STEP_MS)
        } else {
          // candidate_evaluated: brief flash for the candidate
          if (entry.candidate_node_key) {
            setActiveNodeKey(entry.candidate_node_key)
            await sleep(Math.min(STEP_MS * 0.4, 250))
            if (cancelRef.current) break
            setActiveNodeKey(null)
            await sleep(60)
          }
        }
      }

      if (cancelRef.current) return

      setActiveNodeKey(null)
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
    isTraversalTab && traversalState === 'running' ? activeNodeKey : null

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
          onStart={(treeKey, input) => {
            void handleStartTraversal(treeKey, input)
          }}
          onReset={handleReset}
        />

        {/* ---- CENTER: Canvas ---- */}
        <div className="canvas-area">
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

        {/* ---- RIGHT: Side panels ---- */}
        <div className="side-panels">
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
