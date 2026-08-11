import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { dataPlatformApi, type Approval } from "../api/client";
import { loadTokens } from "../auth/session";
import { EmptyState, PageHeader, StatusBadge } from "../components/Page";
import "./datasets.css";

export function ApprovalQueuePage() {
  const navigate = useNavigate();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
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
    dataPlatformApi
      .approvals(accessToken)
      .then((items) => {
        if (!cancelled) setApprovals(items);
      })
      .catch((error) => {
        if (!cancelled)
          setMessage(error instanceof Error ? error.message : "Unable to load approvals.");
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);
  async function decide(approval: Approval, approve: boolean) {
    const tokens = loadTokens();
    if (!tokens) return;
    const comments = window.prompt(approve ? "Approval comment" : "Rejection reason", "") ?? "";
    setBusyId(approval.id);
    try {
      if (approve) await dataPlatformApi.approve(tokens.access_token, approval.id, comments);
      else await dataPlatformApi.reject(tokens.access_token, approval.id, comments);
      await reload();
      setMessage(approve ? "Dataset version approved." : "Dataset version rejected.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to decide approval.");
    } finally {
      setBusyId(null);
    }
  }
  const pending = approvals.filter((approval) => approval.status === "PENDING");
  return (
    <main className="datasets-page">
      <PageHeader
        eyebrow="Governance"
        title="Dataset approval queue"
        description="Review validated versions before publication. Approval and publication remain permission-separated."
        actions={
          <Link className="button" to="/datasets">
            Back to catalogue
          </Link>
        }
      />
      {message && <p className="notice notice-info">{message}</p>}
      <section className="grid-3 approval-metrics">
        <article className="metric-card">
          <span className="metric-label">Pending review</span>
          <div className="metric-value">{pending.length}</div>
          <span className="metric-detail">Requires reviewer action</span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Approved / closed</span>
          <div className="metric-value">{approvals.length - pending.length}</div>
          <span className="metric-detail">Visible review history</span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Total queue records</span>
          <div className="metric-value">{approvals.length}</div>
          <span className="metric-detail">Current API result</span>
        </article>
      </section>
      <section className="datasets-card">
        {approvals.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Submitted</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Review</th>
                </tr>
              </thead>
              <tbody>
                {approvals.map((approval) => (
                  <tr key={approval.id}>
                    <td>{new Date(approval.submitted_at).toLocaleString()}</td>
                    <td>
                      <code>{approval.dataset_version_id.slice(0, 8)}…</code>
                    </td>
                    <td>
                      <StatusBadge value={approval.status} />
                    </td>
                    <td>
                      {approval.status === "PENDING" ? (
                        <div className="dataset-actions">
                          <button
                            className="button-primary"
                            disabled={busyId === approval.id}
                            type="button"
                            onClick={() => void decide(approval, true)}
                          >
                            Approve
                          </button>
                          <button
                            className="button-danger"
                            disabled={busyId === approval.id}
                            type="button"
                            onClick={() => void decide(approval, false)}
                          >
                            Reject
                          </button>
                        </div>
                      ) : (
                        <span className="review-comment">
                          {approval.comments ?? "No reviewer comment"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Approval queue is clear"
            description="Validated dataset versions submitted for review will appear here."
          />
        )}
      </section>
    </main>
  );
}
