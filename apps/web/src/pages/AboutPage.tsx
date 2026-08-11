import { Link } from "react-router-dom";

export function AboutPage() {
  return (
    <main>
      <h1>CRAM Platform</h1>
      <h2>Project Skeleton</h2>
      <p>This temporary page verifies that application routing is operational.</p>
      <p>
        <Link to="/">Return to system status</Link>
      </p>
    </main>
  );
}
