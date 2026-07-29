import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  /** Shown in the fallback message, e.g. "tree canvas". Defaults to a generic phrase. */
  label?: string
}

interface ErrorBoundaryState {
  error: Error | null
}

/** Catches render-time errors in its subtree and shows a fallback instead of
 * leaving the user with a blank page. */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error', error, info)
  }

  handleRetry = () => {
    this.setState({ error: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary-fallback">
          <div className="error-boundary-card">
            <h2>Something went wrong</h2>
            <p>
              {this.props.label
                ? `The ${this.props.label} ran into a problem and could not continue.`
                : 'This page ran into a problem and could not continue.'}
            </p>
            <div className="error-boundary-actions">
              <button type="button" className="error-boundary-btn" onClick={this.handleRetry}>
                Try again
              </button>
              <button type="button" className="error-boundary-btn error-boundary-btn-primary" onClick={this.handleReload}>
                Reload page
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
