import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { dataPlatformApi, type Approval } from "../api/client";
import { loadTokens } from "../auth/session";
import "./datasets.css";

export function ApprovalQueuePage() {
  const navigate = useNavigate();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [message, setMessage] = useState("");

  async function reload() {
    const tokens = loadTokens();
    if (!tokens) return navigate("/login");
    setApprovals(await dataPlatformApi.approvals(tokens.access_token));
  }

  useEffect(() => {
    const tokens = loadTokens();
    if (!tokens) {
      navigate("/login");
      return;
    }
    const accessToken = tokens.access_token;
    let cancelled = false;
    async function loadInitial() {
      try {
        const items = await dataPlatformApi.approvals(accessToken);
        if (!cancelled) setApprovals(items);
      } catch (error) {
        if (!cancelled)
          setMessage(error instanceof Error ? error.message : "Unable to load approvals.");
      }
    }
    void loadInitial();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  async function decide(approval: Approval, approve: boolean) {
    const tokens = loadTokens();
    if (!tokens) return;
    const comments = window.prompt(approve ? "Approval comment" : "Rejection reason", "") ?? "";
    try {
      if (approve) await dataPlatformApi.approve(tokens.access_token, approval.id, comments);
      else await dataPlatformApi.reject(tokens.access_token, approval.id, comments);
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to decide approval.");
    }
  }

  return (
    <main className="datasets-page">
      <header className="datasets-header">
        <div>
          <h1>Dataset Approval Queue</h1>
          <p>Permission-separated review of validated dataset versions.</p>
        </div>
        <Link to="/datasets">Catalogue</Link>
      </header>
      {message && <p>{message}</p>}
      <section className="datasets-card">
        <table>
          <thead>
            <tr>
              <th>Submitted</th>
              <th>Version</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {approvals.map((approval) => (
              <tr key={approval.id}>
                <td>{new Date(approval.submitted_at).toLocaleString()}</td>
                <td>{approval.dataset_version_id}</td>
                <td>{approval.status}</td>
                <td>
                  {approval.status === "PENDING" ? (
                    <>
                      <button type="button" onClick={() => void decide(approval, true)}>
                        Approve
                      </button>{" "}
                      <button type="button" onClick={() => void decide(approval, false)}>
                        Reject
                      </button>
                    </>
                  ) : (
                    (approval.comments ?? "—")
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
