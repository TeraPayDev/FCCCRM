import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "../components/Icon";
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
        <Link to="/datasets" className="button secondary-button icon-button">
          <Icon name="data" /> Data Catalogue
        </Link>
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
                <td>
                  <span className={`approval-status ${approval.status.toLowerCase()}`}>
                    {approval.status}
                  </span>
                </td>
                <td>
                  {approval.status === "PENDING" ? (
                    <>
                      <span className="approval-actions">
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => void decide(approval, true)}
                        >
                          <Icon name="check" /> Approve
                        </button>
                        <button
                          className="secondary-action"
                          type="button"
                          onClick={() => void decide(approval, false)}
                        >
                          Reject
                        </button>
                      </span>
                    </>
                  ) : (
                    (approval.comments ?? "—")
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!approvals.length && (
          <div className="empty-inline">No dataset versions are waiting for review.</div>
        )}
      </section>
    </main>
  );
}
