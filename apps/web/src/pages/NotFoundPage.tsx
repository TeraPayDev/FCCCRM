import { Link } from "react-router-dom";
export function NotFoundPage() {
  return (
    <main className="about-page">
      <section className="card empty-state">
        <div className="empty-state-mark">404</div>
        <strong>Page not found</strong>
        <p>The requested CRAM workspace does not exist or has moved.</p>
        <Link className="button button-primary" to="/">
          Return to overview
        </Link>
      </section>
    </main>
  );
}
