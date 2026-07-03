import { useCallback, useEffect, useState } from 'react'
import { fetchTreeGraph, fetchTrees } from './api/client'
import type { TreeGraphNode, TreeGraphResponse, TreeSummary } from './api/types'
import { TreeCanvas } from './canvas/TreeCanvas'
import { GlobalConfigPanel } from './panels/GlobalConfigPanel'
import { Legend } from './panels/Legend'
import { NodeDetailPanel } from './panels/NodeDetailPanel'
import './App.css'

function App() {
  const [trees, setTrees] = useState<TreeSummary[]>([])
  const [activeTreeKey, setActiveTreeKey] = useState<string | null>(null)
  const [graphCache, setGraphCache] = useState<Record<string, TreeGraphResponse>>({})
  const [focusNodeKey, setFocusNodeKey] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<TreeGraphNode | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTrees()
      .then((summaries) => {
        setTrees(summaries)
        setActiveTreeKey(summaries[0]?.tree_key ?? null)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  useEffect(() => {
    if (!activeTreeKey || graphCache[activeTreeKey]) return
    fetchTreeGraph(activeTreeKey)
      .then((graph) => setGraphCache((prev) => ({ ...prev, [activeTreeKey]: graph })))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [activeTreeKey, graphCache])

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

  const activeGraph = activeTreeKey ? graphCache[activeTreeKey] : undefined

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
        <div className="canvas-area">
          {activeGraph ? (
            <TreeCanvas
              key={activeGraph.tree.tree_key}
              graph={activeGraph}
              focusNodeKey={focusNodeKey}
              onSelectNode={setSelectedNode}
            />
          ) : (
            <div className="panel-empty loading">Loading tree...</div>
          )}
        </div>

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
    </div>
  )
}

export default App
