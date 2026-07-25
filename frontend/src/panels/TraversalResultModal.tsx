import type { ApiErrorResponse, EvaluationResponse, JsonObject, TraversalTraceEntry } from '../api/types'

interface TraversalResultModalProps {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  onClose: () => void
}

interface Medicine {
  drug_id: string
  name: string
  subgroup: string
  route: string
  dose_low: string
  dose_usual: string
  dose_max: string
  source: string
  link: string | null
  available: boolean
}

interface MedicineOption {
  classes: string[]
  medicines: Record<string, Medicine[]>
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function parseMedicine(value: unknown): Medicine | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null
  const m = value as JsonObject
  return {
    drug_id: asString(m.drug_id),
    name: asString(m.name),
    subgroup: asString(m.subgroup),
    route: asString(m.route),
    dose_low: asString(m.dose_low),
    dose_usual: asString(m.dose_usual),
    dose_max: asString(m.dose_max),
    source: asString(m.source),
    link: typeof m.link === 'string' ? m.link : null,
    available: m.available !== false,
  }
}

// Reads payload.medicines, the flat single-drug list the backend attaches to
// END nodes that name one specific drug (e.g. aspirin prophylaxis).
function getMedicines(payload: JsonObject): Medicine[] | null {
  const medicines = payload.medicines
  if (!Array.isArray(medicines)) return null
  return medicines.map(parseMedicine).filter((m): m is Medicine => m !== null)
}

// Reads payload.medicine_options, the class-letter -> medicine expansion the
// backend attaches to "start/escalate drug combination" END nodes only.
function getMedicineOptions(payload: JsonObject): MedicineOption[] | null {
  const medicineOptions = payload.medicine_options
  if (!Array.isArray(medicineOptions)) return null

  const options: MedicineOption[] = []
  for (const option of medicineOptions) {
    if (typeof option !== 'object' || option === null || Array.isArray(option)) return null
    const classes = (option as JsonObject).classes
    const medicines = (option as JsonObject).medicines
    if (!Array.isArray(classes) || typeof medicines !== 'object' || medicines === null) return null

    const medicinesByClass: Record<string, Medicine[]> = {}
    for (const [classLetter, entries] of Object.entries(medicines as JsonObject)) {
      if (!Array.isArray(entries)) continue
      medicinesByClass[classLetter] = entries
        .map(parseMedicine)
        .filter((m): m is Medicine => m !== null)
    }
    options.push({
      classes: classes.filter((c): c is string => typeof c === 'string'),
      medicines: medicinesByClass,
    })
  }
  return options
}

// No backend to record acknowledgements yet — these are inert placeholders.
const ACKNOWLEDGE_REASONS = [
  'Will repeat BP',
  'Will order different dose',
  'Will discuss with pt',
  'Remind me next visit',
]

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
          {/* Actions */}
          {actions.map((action, i) => {
            const medicineOptions = getMedicineOptions(action.payload)
            const medicines = getMedicines(action.payload)
            return (
              <div key={i} className="modal-action-card">
                <div className="modal-action-header">
                  <span className="modal-action-type">{String(action.payload.action_type ?? 'ACTION')}</span>
                  <span className="modal-action-node">{action.node_key}</span>
                </div>
                <div className="modal-alert-reason">{action.text_vi}</div>
                {action.text_en && <div className="modal-alert-detail">{action.text_en}</div>}

                {medicineOptions && medicineOptions.length > 0 && (
                  <div className="modal-medicine-options">
                    {medicineOptions.map((option, optionIndex) => (
                      <div key={optionIndex} className="modal-medicine-option">
                        <div className="modal-medicine-option-classes">
                          {option.classes.join(' + ')}
                        </div>
                        <div className="modal-drugclass-row">
                          {option.classes.map((classLetter) => (
                            <div key={classLetter} className="modal-drugclass-chip" tabIndex={0}>
                              <span>Nhóm {classLetter}</span>
                              <div className="modal-drugclass-popover">
                                {(option.medicines[classLetter] ?? []).map((medicine) => (
                                  <div key={medicine.drug_id} className="modal-medicine-row">
                                    <span className="modal-medicine-name">{medicine.name}</span>
                                    <span className="modal-medicine-dose">
                                      {medicine.dose_low} · {medicine.dose_usual} · {medicine.dose_max}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {medicines && medicines.length > 0 && (
                  <div className="modal-medicine-list">
                    {medicines.map((medicine) => (
                      <div
                        key={medicine.drug_id}
                        className={`modal-medicine-row${medicine.available ? '' : ' unavailable'}`}
                      >
                        <span className="modal-medicine-name">{medicine.name}</span>
                        <span className="modal-medicine-dose">
                          {medicine.dose_low} · {medicine.dose_usual} · {medicine.dose_max}
                        </span>
                        {!medicine.available && (
                          <span className="modal-medicine-unavailable-badge">Unavailable</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div className="modal-ack-row">
                  {ACKNOWLEDGE_REASONS.map((reason) => (
                    <button key={reason} type="button" className="modal-ack-btn">{reason}</button>
                  ))}
                </div>
              </div>
            )
          })}

          {/* Everything below is collapsed by default — debug / audit detail, not part of the alert itself */}
          <details className="modal-debug">
            <summary>Traversal details</summary>
            <div className="modal-debug-body">
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

              {Object.keys(context).length > 0 && (
                <section className="modal-section">
                  <div className="modal-section-title">🧠 Derived Context</div>
                  <pre className="modal-json">{JSON.stringify(context, null, 2)}</pre>
                </section>
              )}

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
          </details>
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
