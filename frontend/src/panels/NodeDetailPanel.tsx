import type { JsonObject, TreeGraphNode, TreeGraphSourceReference } from '../api/types'
import { NODE_TYPE_COLORS } from '../canvas/DecisionNodeShapeUtil'
import { CopyButton } from './CopyButton'

interface NodeDetailPanelProps {
  node: TreeGraphNode | null
  references: TreeGraphSourceReference[]
  onJumpToLink: (targetTreeKey: string, targetNodeKey: string | null) => void
}

function JsonBlock({ label, value }: { label: string; value: JsonObject | null }) {
  if (!value) return null
  const jsonStr = JSON.stringify(value, null, 2)
  return (
    <div className="detail-field">
      <div className="detail-field-header">
        <div className="detail-field-label">{label}</div>
        <CopyButton text={jsonStr} />
      </div>
      <pre className="detail-json">{jsonStr}</pre>
    </div>
  )
}

export function NodeDetailPanel({ node, references, onJumpToLink }: NodeDetailPanelProps) {
  if (!node) {
    return (
      <div className="panel">
        <p className="panel-empty">Select a node to see its details.</p>
      </div>
    )
  }

  const nodeReferences = references.filter((reference) => reference.node_key === node.node_key)
  const colors = NODE_TYPE_COLORS[node.node_type]
  const upperSectionText = `Key: ${node.node_key}\nEnglish: ${node.text_en}\nVietnamese: ${node.text_vi}`


  return (
    <div className="panel">
      <div className="detail-header">
        <span className="detail-badge" style={{ background: colors.background, color: colors.border }}>
          {node.node_type}
        </span>
        <span className="detail-key">{node.node_key}</span>
        <CopyButton text={upperSectionText} />
      </div>

      <div className="detail-field">
        <div className="detail-field-label">English</div>
        <div className="detail-text">{node.text_en}</div>
      </div>
      <div className="detail-field">
        <div className="detail-field-label">Vietnamese</div>
        <div className="detail-text">{node.text_vi}</div>
      </div>

      <JsonBlock label="Condition" value={node.condition_definition} />
      <JsonBlock label="Context patch" value={node.context_patch} />
      <JsonBlock label="Action payload" value={node.action_payload} />

      {node.node_type === 'LINK' && node.link_target_tree_key && (
        <div className="detail-field">
          <div className="detail-field-header">
            <div className="detail-field-label">Link target</div>
            <CopyButton
              text={`${node.link_target_tree_key}${
                node.link_target_node_key ? ` / ${node.link_target_node_key}` : ' / (start)'
              }`}
            />
          </div>
          <div className="detail-text">
            {node.link_target_tree_key}
            {node.link_target_node_key ? ` / ${node.link_target_node_key}` : ' / (start)'}
          </div>
          <button
            type="button"
            className="jump-button"
            onClick={() => onJumpToLink(node.link_target_tree_key!, node.link_target_node_key)}
          >
            Go to linked tree
          </button>
        </div>
      )}

      {nodeReferences.length > 0 && (
        <div className="detail-field">
          <div className="detail-field-header">
            <div className="detail-field-label">Source references</div>
            <CopyButton
              text={nodeReferences
                .map((ref) => `${ref.source_title}${ref.locator ? ` (${ref.locator})` : ''}`)
                .join('\n')}
            />
          </div>
          <ul className="reference-list">
            {nodeReferences.map((reference) => (
              <li key={`${reference.node_key}-${reference.reference_order}`}>
                <div>{reference.source_title}</div>
                {reference.locator && <div className="reference-locator">{reference.locator}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

