import type { ReactNode } from "react";
import "./module-shell.css";

export function ModuleShell(props: {
  title: string;
  subtitle: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="module-shell">
      <header className="module-header">
        <div>
          <p className="eyebrow">{props.eyebrow ?? "CRAM operational workspace"}</p>
          <h1>{props.title}</h1>
          <p>{props.subtitle}</p>
        </div>
        {props.actions && <div className="module-header-actions">{props.actions}</div>}
      </header>
      {props.children}
    </main>
  );
}
