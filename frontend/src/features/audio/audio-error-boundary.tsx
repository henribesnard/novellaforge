'use client'

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class AudioErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[AudioPlayer] Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-sm text-red-700">
              Une erreur est survenue avec le lecteur audio.
            </p>
            <button
              className="mt-2 text-xs text-red-600 underline"
              onClick={() => this.setState({ hasError: false })}
              type="button"
            >
              Reessayer
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
