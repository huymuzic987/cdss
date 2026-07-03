import type { TreeGraphGlobalNode } from '../api/types'

interface GlobalConfigPanelProps {
  globalNodes: TreeGraphGlobalNode[]
}

export function GlobalConfigPanel({ globalNodes }: GlobalConfigPanelProps) {
  if (globalNodes.length === 0) return null

  return (
    <div className="panel">
      <div className="detail-field-label">Global config</div>
      {globalNodes.map((node) => (
        <div key={node.node_key} className="detail-field">
          <div className="detail-text">{node.text_en}</div>
          {node.global_config && (
            <pre className="detail-json">{JSON.stringify(node.global_config, null, 2)}</pre>
          )}
        </div>
      ))}
    </div>
  )
}
