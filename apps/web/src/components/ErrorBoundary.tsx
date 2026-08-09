import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("CRAM frontend error boundary", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main>
          <h1>CRAM Platform</h1>
          <h2>Application error</h2>
          <p>The application could not render this page. Please refresh and try again.</p>
        </main>
      );
    }

    return this.props.children;
  }
}
