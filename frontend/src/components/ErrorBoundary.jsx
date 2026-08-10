import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, info) { console.error('ErrorBoundary:', error, info); }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) this.props.onReset();
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-black px-4">
          <div className="max-w-md w-full card p-8 text-center space-y-4">
            <AlertTriangle className="w-14 h-14 text-red-400 mx-auto" />
            <h2 className="text-xl font-bold text-white">Something went wrong</h2>
            <p className="text-sm text-white/50">An unexpected error occurred. This may be a temporary issue.</p>
            {this.state.error && (
              <details className="text-left">
                <summary className="text-xs text-red-400 cursor-pointer font-medium">Error Details</summary>
                <pre className="mt-2 text-xs text-red-300 bg-red-500/10 p-3 rounded-lg overflow-auto max-h-32">{this.state.error.message}</pre>
              </details>
            )}
            <button onClick={this.handleReload} className="btn-accent inline-flex items-center gap-2"><RefreshCw className="w-4 h-4" />Reload Page</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
