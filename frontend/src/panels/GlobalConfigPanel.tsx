import type { TreeGraphGlobalNode } from '../api/types'
import { CopyButton } from './CopyButton'

interface GlobalConfigPanelProps {
  globalNodes: TreeGraphGlobalNode[]
}

export function GlobalConfigPanel({ globalNodes }: GlobalConfigPanelProps) {
  if (globalNodes.length === 0) return null

  return (
    <div className="panel">
      <div className="detail-field-label" style={{ marginBottom: '8px' }}>Global config</div>
      {globalNodes.map((node) => {
        const configStr = node.global_config ? JSON.stringify(node.global_config, null, 2) : ''
        const copyText = `${node.text_en}${configStr ? '\n' + configStr : ''}`
        return (
          <div key={node.node_key} className="detail-field" style={{ borderBottom: '1px solid var(--border-soft)', paddingBottom: '8px', marginBottom: '8px' }}>
            <div className="detail-field-header">
              <span className="detail-key">{node.node_key}</span>
              <CopyButton text={copyText} />
            </div>
            <div className="detail-text" style={{ marginTop: '4px' }}>{node.text_en}</div>
            {node.global_config && (
              <pre className="detail-json" style={{ marginTop: '6px' }}>{configStr}</pre>
            )}
          </div>
        )
      })}
    </div>
  )
}

