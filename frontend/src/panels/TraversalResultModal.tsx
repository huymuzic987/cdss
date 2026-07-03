import type { ApiErrorResponse, EvaluationResponse, TraversalTraceEntry } from '../api/types'

interface TraversalResultModalProps {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  onClose: () => void
}

function ConditionRow({ entry }: { entry: TraversalTraceEntry }) {
  const passed = entry.condition_result === true
  const failed = entry.condition_result === false
  return (
    <div className="modal-condition-row">
      <span
        className={`modal-condition-badge ${passed ? 'passed' : failed ? 'failed' : 'neutral'}`}
      >
        {passed ? '✓' : failed ? '✗' : '→'}
      </span>
      <div className="modal-condition-info">
        <div className="modal-condition-node">
          <span className="modal-node-tree">{entry.tree_key.split('-').map(w => w[0]).join('').toUpperCase()}</span>
          {' · '}
          <span className="modal-node-key">
            {entry.event === 'candidate_evaluated' && entry.candidate_node_key
              ? entry.candidate_node_key
              : entry.node_key}
          </span>
        </div>
        {entry.condition_definition && (
          <div className="modal-condition-def">
            {summariseCondition(entry.condition_definition)}
          </div>
        )}
      </div>
    </div>
  )
}

// Build a short human-readable label for a condition
function summariseCondition(def: Record<string, unknown>): string {
  if ('all' in def) return `ALL (${(def.all as unknown[]).length} checks)`
  if ('any' in def) return `ANY (${(def.any as unknown[]).length} checks)`
  if ('not' in def) return `NOT (…)`
  if ('op' in def) {
    const path = String(def.path ?? def.left ?? '?').replace(/^input\./, '')
    const op = String(def.op)
    if (op === 'exists') return `${path} exists`
    const right =
      'value_from_path' in def
        ? `← ${String(def.value_from_path).replace(/^context\./, 'ctx.')}`
        : JSON.stringify(def.value)
    return `${path} ${op} ${right}`
  }
  return JSON.stringify(def).slice(0, 60)
}

export function TraversalResultModal({ result, partial, onClose }: TraversalResultModalProps) {
  if (!result && !partial) return null

  const log = result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []
  const actions = result?.actions ?? partial?.partial_run_state?.actions ?? []
  const context = result?.context ?? partial?.partial_run_state?.context ?? {}
  const isSuccess = !!result

  const conditionEntries = log.filter(
    (e) => e.event === 'candidate_evaluated' && e.condition_result !== null,
  )
  const enteredNodes = log.filter((e) => e.event === 'node_entered')

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className={`modal-header ${isSuccess ? 'success' : 'partial'}`}>
          <div className="modal-header-icon">{isSuccess ? '✅' : '⚠️'}</div>
          <div>
            <div className="modal-header-title">
              {isSuccess ? 'Traversal Complete' : 'Partial Traversal – Unresolved Link'}
            </div>
            {!isSuccess && partial && (
              <div className="modal-header-sub">{partial.message}</div>
            )}
            {!isSuccess && partial?.details?.link_target_tree_key && (
              <div className="modal-header-sub">
                Link target not found:{' '}
                <code>{String(partial.details.link_target_tree_key)}</code>
              </div>
            )}
          </div>
          <button type="button" className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {/* Stats row */}
          <div className="modal-stats">
            <div className="modal-stat">
              <div className="modal-stat-value">{enteredNodes.length}</div>
              <div className="modal-stat-label">Nodes Entered</div>
            </div>
            <div className="modal-stat">
              <div className="modal-stat-value">{conditionEntries.length}</div>
              <div className="modal-stat-label">Conditions Checked</div>
            </div>
            <div className="modal-stat">
              <div className="modal-stat-value">{conditionEntries.filter(e => e.condition_result).length}</div>
              <div className="modal-stat-label">Passed</div>
            </div>
            <div className="modal-stat">
              <div className="modal-stat-value">{actions.length}</div>
              <div className="modal-stat-label">Actions</div>
            </div>
          </div>

          {/* Actions */}
          {actions.length > 0 && (
            <section className="modal-section">
              <div className="modal-section-title">📋 Clinical Recommendations</div>
              {actions.map((action, i) => (
                <div key={i} className="modal-action-card">
                  <div className="modal-action-header">
                    <span className="modal-action-type">{String(action.payload.action_type ?? 'ACTION')}</span>
                    <span className="modal-action-node">{action.node_key}</span>
                  </div>
                  <div className="modal-action-text-vi">{action.text_vi}</div>
                  <div className="modal-action-text-en">{action.text_en}</div>
                  {action.payload && Object.keys(action.payload).length > 0 && (
                    <details className="modal-action-payload">
                      <summary>Payload</summary>
                      <pre>{JSON.stringify(action.payload, null, 2)}</pre>
                    </details>
                  )}
                </div>
              ))}
            </section>
          )}

          {/* Context output */}
          {Object.keys(context).length > 0 && (
            <section className="modal-section">
              <div className="modal-section-title">🧠 Derived Context</div>
              <pre className="modal-json">{JSON.stringify(context, null, 2)}</pre>
            </section>
          )}

          {/* Condition checks */}
          {conditionEntries.length > 0 && (
            <section className="modal-section">
              <div className="modal-section-title">🔍 Condition Checks</div>
              <div className="modal-conditions">
                {conditionEntries.map((entry, i) => (
                  <ConditionRow key={i} entry={entry} />
                ))}
              </div>
            </section>
          )}

          {/* Traversal path */}
          <section className="modal-section">
            <div className="modal-section-title">🗺️ Path Taken ({enteredNodes.length} steps)</div>
            <div className="modal-path">
              {enteredNodes.map((entry, i) => (
                <div key={i} className="modal-path-step">
                  <span className="modal-path-num">{i + 1}</span>
                  <span className="modal-path-tree">{entry.tree_key.split('-').slice(0, 2).join('-')}</span>
                  <span className="modal-path-node">{entry.node_key}</span>
                  <span className={`modal-path-type modal-path-type-${entry.node_type.toLowerCase()}`}>
                    {entry.node_type}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="modal-footer">
          <button type="button" className="modal-footer-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
