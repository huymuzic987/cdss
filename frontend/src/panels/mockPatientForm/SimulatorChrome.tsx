import { AlertTriangle, FlaskConical, Moon, MousePointer2, Play, Sun, X } from 'lucide-react'

interface SimulatorHeaderProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export function SimulatorHeader({ theme, onToggleTheme }: SimulatorHeaderProps) {
  return (
    <div className="ps-header">
      <div className="ps-header-left">
        <span className="ps-header-icon"><FlaskConical size={16} /></span>
        <div>
          <div className="ps-header-title">Patient Simulator</div>
          <div className="ps-header-sub">Fill in fields to simulate traversal</div>
        </div>
      </div>
      <button
        type="button"
        className="ps-theme-toggle"
        onClick={onToggleTheme}
        title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
      >
        {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
      </button>
    </div>
  )
}

interface SimulatorFooterProps {
  isRunning: boolean
  canReset: boolean
  validationError: string | null
  onStart: () => void
  onManualStart: () => void
  onReset: () => void
}

export function SimulatorFooter(props: SimulatorFooterProps) {
  return (
    <div className="ps-footer">
      {props.validationError && (
        <div className="ps-validation-error">
          <AlertTriangle size={13} style={{ flexShrink: 0 }} /> {props.validationError}
        </div>
      )}
      <button type="button" className="ps-btn-start" onClick={props.onStart} disabled={props.isRunning}>
        {props.isRunning
          ? <><span className="ps-spinner" /> Simulating…</>
          : <><Play size={13} /> Start Traversal</>}
      </button>
      <button type="button" className="ps-btn-manual" onClick={props.onManualStart} disabled={props.isRunning}>
        <MousePointer2 size={13} /> Manual Traverse
      </button>
      <button type="button" className="ps-btn-reset" onClick={props.onReset} disabled={!props.canReset}>
        <X size={13} /> Reset
      </button>
    </div>
  )
}
