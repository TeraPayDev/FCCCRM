import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main>
      <h1>404</h1>
      <p>The requested CRAM page does not exist.</p>
      <p><Link to="/">Return home</Link></p>
    </main>
  );
}
