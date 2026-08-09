import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export function SystemStatusPage() {
  const health = useQuery({
    queryKey: ["system", "health"],
    queryFn: api.health,
    retry: 1,
  });

  const apiStatus = health.isPending
    ? "Checking..."
    : health.isError
      ? "Unavailable"
      : `${health.data.status} (${health.data.version})`;

  return (
    <main>
      <h1>CRAM Platform</h1>
      <p>Climate Risk Analytics Management Platform</p>
      <hr />
      <h2>Development Environment</h2>
      <p><strong>Frontend:</strong> Running</p>
      <p><strong>API:</strong> {apiStatus}</p>
      <p><Link to="/about">About this skeleton</Link></p>
    </main>
  );
}
