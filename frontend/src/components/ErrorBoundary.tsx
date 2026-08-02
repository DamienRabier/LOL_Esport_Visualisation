import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface State {
  error: Error | null;
}

// Catches render errors in a page so one broken view doesn't blank the whole app.
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Render error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="page">
          <div className="error">
            <strong>Something broke rendering this view.</strong>
            <pre style={{ whiteSpace: "pre-wrap", marginTop: 8, fontSize: 12 }}>
              {this.state.error.message}
              {"\n"}
              {this.state.error.stack?.split("\n").slice(0, 4).join("\n")}
            </pre>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
