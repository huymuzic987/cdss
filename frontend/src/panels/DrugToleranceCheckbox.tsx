import { useState } from 'react'

/**
 * DrugToleranceCheckbox
 *
 * A modal popup that appears when the traversal reaches the "MRA tolerance"
 * check node (T13_A_CHECK_MRA). It presents two yes/no radio rows:
 *
 *   1. MRA tolerance         — Yes / No
 *   2. Spironolactone tolerance — Yes / No  (only enabled when MRA = No)
 *
 * Logic:
 *   • MRA Yes   → tolerates_mra = true  (spironolactone row is irrelevant)
 *   • MRA No  + Spironolactone Yes → tolerates_mra = false, tolerates_spironolactone = true
 *   • MRA No  + Spironolactone No  → both = false
 */

export interface DrugToleranceResult {
  tolerates_mra: boolean
  tolerates_spironolactone: boolean
}

interface DrugToleranceCheckboxProps {
  onConfirm: (result: DrugToleranceResult) => void
  onCancel: () => void
}

export function DrugToleranceCheckbox({ onConfirm, onCancel }: DrugToleranceCheckboxProps) {
  // null = not yet answered
  const [mraTolerance, setMraTolerance] = useState<boolean | null>(null)
  const [spiroTolerance, setSpiroTolerance] = useState<boolean | null>(null)

  const spiroEnabled = mraTolerance === false
  const canConfirm =
    mraTolerance === true || (mraTolerance === false && spiroTolerance !== null)

  const handleConfirm = () => {
    if (!canConfirm) return
    if (mraTolerance === true) {
      onConfirm({ tolerates_mra: true, tolerates_spironolactone: false })
    } else {
      onConfirm({
        tolerates_mra: false,
        tolerates_spironolactone: spiroTolerance === true,
      })
    }
  }

  // When MRA changes to Yes, reset spiro since it's no longer relevant
  const handleMraChange = (value: boolean) => {
    setMraTolerance(value)
    if (value === true) {
      setSpiroTolerance(null)
    }
  }

  return (
    <div className="dtc-overlay" onClick={onCancel}>
      <div className="dtc-box" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="dtc-header">
          <div className="dtc-header-icon">💊</div>
          <div>
            <div className="dtc-header-title">Drug Tolerance Check</div>
            <div className="dtc-header-sub">
              Kiểm tra khả năng dung nạp MRA — Resistant Hypertension pathway
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="dtc-body">
          {/* Row 1: MRA tolerance */}
          <div className="dtc-row">
            <div className="dtc-row-label">
              <span className="dtc-drug-name">MRA tolerance</span>
              <span className="dtc-drug-note">Mineralocorticoid Receptor Antagonist</span>
            </div>
            <div className="dtc-choices">
              <button
                type="button"
                className={`dtc-choice-btn dtc-yes${mraTolerance === true ? ' active' : ''}`}
                onClick={() => handleMraChange(true)}
              >
                Yes
              </button>
              <button
                type="button"
                className={`dtc-choice-btn dtc-no${mraTolerance === false ? ' active' : ''}`}
                onClick={() => handleMraChange(false)}
              >
                No
              </button>
            </div>
          </div>

          {/* Row 2: Spironolactone tolerance */}
          <div className={`dtc-row${!spiroEnabled ? ' dtc-row-disabled' : ''}`}>
            <div className="dtc-row-label">
              <span className="dtc-drug-name">Spironolactone tolerance</span>
              <span className="dtc-drug-note">
                {spiroEnabled
                  ? 'Select tolerance for Spironolactone specifically'
                  : 'Only applicable when MRA is not tolerated'}
              </span>
            </div>
            <div className="dtc-choices">
              <button
                type="button"
                className={`dtc-choice-btn dtc-yes${spiroTolerance === true ? ' active' : ''}${!spiroEnabled ? ' disabled' : ''}`}
                onClick={() => spiroEnabled && setSpiroTolerance(true)}
                disabled={!spiroEnabled}
              >
                Yes
              </button>
              <button
                type="button"
                className={`dtc-choice-btn dtc-no${spiroTolerance === false ? ' active' : ''}${!spiroEnabled ? ' disabled' : ''}`}
                onClick={() => spiroEnabled && setSpiroTolerance(false)}
                disabled={!spiroEnabled}
              >
                No
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="dtc-footer">
          <div className="dtc-summary">
            {mraTolerance === null && (
              <span className="dtc-summary-pending">Select MRA tolerance to continue</span>
            )}
            {mraTolerance === true && (
              <span className="dtc-summary-value">
                tolerates_mra = <strong>true</strong>
              </span>
            )}
            {mraTolerance === false && spiroTolerance === null && (
              <span className="dtc-summary-pending">
                Now select Spironolactone tolerance
              </span>
            )}
            {mraTolerance === false && spiroTolerance === true && (
              <span className="dtc-summary-value">
                tolerates_mra = <strong>false</strong> · tolerates_spironolactone = <strong>true</strong>
              </span>
            )}
            {mraTolerance === false && spiroTolerance === false && (
              <span className="dtc-summary-value">
                tolerates_mra = <strong>false</strong> · tolerates_spironolactone = <strong>false</strong>
              </span>
            )}
          </div>
          <div className="dtc-footer-actions">
            <button type="button" className="dtc-btn-cancel" onClick={onCancel}>
              Cancel
            </button>
            <button
              type="button"
              className={`dtc-btn-confirm${canConfirm ? '' : ' disabled'}`}
              disabled={!canConfirm}
              onClick={handleConfirm}
            >
              Confirm & Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
