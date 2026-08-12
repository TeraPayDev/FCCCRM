import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ApiError,
  api,
  dataPlatformApi,
  type Dataset,
  type DatasetField,
  type DatasetSource,
  type DatasetVersion,
  type Organisation,
  type ValidationRun,
} from "../api/client";
import { loadTokens } from "../auth/session";
import { previewCsv, type CsvDataType, type CsvPreview } from "../utils/csvPreview";
import "./datasets.css";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function schemaCompatible(configured: string, detected: CsvDataType): boolean {
  const normalized = configured.toLowerCase();
  if (normalized === detected) return true;
  if (["number", "float", "decimal"].includes(normalized) && detected === "integer") return true;
  return normalized === "string";
}

export function DatasetDetailPage() {
  const { datasetId = "" } = useParams();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [sources, setSources] = useState<DatasetSource[]>([]);
  const [fields, setFields] = useState<DatasetField[]>([]);
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [validations, setValidations] = useState<Record<string, ValidationRun[]>>({});
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [busy, setBusy] = useState(false);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [message, setMessage] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [fieldType, setFieldType] = useState("string");
  const [sourceName, setSourceName] = useState("");
  const [updateMethod, setUpdateMethod] = useState("manual CSV upload");
  const [secretRef, setSecretRef] = useState("");

  const ownerName = useMemo(
    () =>
      organisations.find((organisation) => organisation.id === dataset?.owner_organisation_id)
        ?.name ?? "Institutional owner",
    [dataset?.owner_organisation_id, organisations],
  );

  function handleError(error: unknown, fallback: string) {
    if (error instanceof ApiError && error.status === 401) {
      setMessage("Your session expired. Please sign in again.");
      navigate("/login");
      return;
    }
    setMessage(error instanceof Error ? error.message : fallback);
  }

  async function reload() {
    const tokens = loadTokens();
    if (!tokens) {
      navigate("/login");
      return;
    }
    try {
      const [detail, sourceData, fieldData, versionData, organisationData] = await Promise.all([
        dataPlatformApi.dataset(tokens.access_token, datasetId),
        dataPlatformApi.sources(tokens.access_token, datasetId),
        dataPlatformApi.fields(tokens.access_token, datasetId),
        dataPlatformApi.versions(tokens.access_token, datasetId),
        api.organisations(tokens.access_token),
      ]);
      setDataset(detail);
      setSources(sourceData);
      setFields(fieldData);
      setVersions(versionData);
      setOrganisations(organisationData);
    } catch (error) {
      handleError(error, "Unable to load dataset.");
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);

    return () => window.clearTimeout(timer);
    // reload is intentionally scoped to the active dataset.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  async function selectFile(selected: File | null) {
    setFile(selected);
    setPreview(null);
    setPreviewError("");
    setMessage("");
    if (!selected) return;

    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setPreviewError("Choose a CSV file.");
      return;
    }

    try {
      const text = await selected.text();
      setPreview(previewCsv(text));
    } catch (error) {
      setPreviewError(error instanceof Error ? error.message : "Unable to inspect the CSV.");
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const tokens = loadTokens();
    if (!tokens || !file || !preview) return;

    setBusy(true);
    setMessage("");
    try {
      await dataPlatformApi.uploadCsv(tokens.access_token, datasetId, file, sources[0]?.id);
      setMessage(
        `Upload complete. CRAM created a governed dataset version with ${preview.rowCount.toLocaleString()} rows and ${preview.fields.length} detected fields.`,
      );
      setFile(null);
      setPreview(null);
      setPreviewError("");
      setFileInputKey((current) => current + 1);
      await reload();
    } catch (error) {
      handleError(error, "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function addSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const tokens = loadTokens();
    if (!tokens || !dataset) return;
    try {
      await dataPlatformApi.createSource(tokens.access_token, datasetId, {
        provider_organisation_id: dataset.owner_organisation_id,
        name: sourceName.trim(),
        source_type: "FILE",
        source_reference: "catalogue-managed source",
        connection_secret_ref: secretRef.trim() || undefined,
        update_method: updateMethod.trim(),
      });
      setSourceName("");
      setSecretRef("");
      setMessage(
        "Dataset source added. Credentials remain outside CRAM; only references are stored.",
      );
      await reload();
    } catch (error) {
      handleError(error, "Unable to add dataset source.");
    }
  }

  async function addField(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      await dataPlatformApi.createField(tokens.access_token, datasetId, {
        name: fieldName.trim(),
        data_type: fieldType,
        ordinal: fields.length,
        is_required: true,
        validation_rules: {},
      });
      setFieldName("");
      setMessage("Manual schema field added.");
      await reload();
    } catch (error) {
      handleError(error, "Unable to add field.");
    }
  }

  async function validate(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      const run = await dataPlatformApi.validateVersion(tokens.access_token, versionId);
      setValidations((current) => ({ ...current, [versionId]: [run] }));
      setMessage(
        run.status === "PASSED"
          ? `Validation passed for ${run.total_rows.toLocaleString()} rows.`
          : `Validation ${run.status}: ${run.error_count} errors, ${run.warning_count} warnings.`,
      );
      await reload();
    } catch (error) {
      handleError(error, "Validation failed.");
    }
  }

  async function showValidations(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      const runs = await dataPlatformApi.validations(tokens.access_token, versionId);
      setValidations((current) => ({ ...current, [versionId]: runs }));
    } catch (error) {
      handleError(error, "Unable to load validation results.");
    }
  }

  async function submit(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      await dataPlatformApi.submitVersion(tokens.access_token, versionId);
      setMessage("Dataset version submitted for institutional approval.");
      await reload();
    } catch (error) {
      handleError(error, "Submission failed.");
    }
  }

  async function publish(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      await dataPlatformApi.publish(tokens.access_token, versionId);
      setMessage("Approved dataset version published.");
      await reload();
    } catch (error) {
      handleError(error, "Publication failed.");
    }
  }

  if (!dataset) {
    return (
      <main className="datasets-page">
        <div className="datasets-loading">{message || "Loading dataset…"}</div>
      </main>
    );
  }

  return (
    <main className="datasets-page dataset-detail-page">
      <header className="datasets-header dataset-detail-header">
        <div>
          <p className="dataset-eyebrow">Institutional dataset</p>
          <h1>{dataset.name}</h1>
          <div className="dataset-title-meta">
            <span>{dataset.code}</span>
            <span className={`dataset-status status-${dataset.status.toLowerCase()}`}>
              {dataset.status}
            </span>
            <span>{dataset.sensitivity}</span>
          </div>
        </div>
        <Link className="dataset-back-link" to="/datasets">
          ← Data Catalogue
        </Link>
      </header>

      {message && <div className="datasets-message">{message}</div>}

      <section className="ingestion-progress" aria-label="Dataset governance workflow">
        <div className="progress-step complete">
          <span>1</span>
          <div>
            <strong>Register</strong>
            <small>Dataset & source</small>
          </div>
        </div>
        <div className={`progress-step ${versions.length ? "complete" : "active"}`}>
          <span>2</span>
          <div>
            <strong>Upload</strong>
            <small>Inspect & version CSV</small>
          </div>
        </div>
        <div
          className={`progress-step ${versions.some((v) => ["VALIDATED", "PENDING_APPROVAL", "APPROVED", "PUBLISHED"].includes(v.status)) ? "complete" : versions.length ? "active" : ""}`}
        >
          <span>3</span>
          <div>
            <strong>Validate</strong>
            <small>Quality checks</small>
          </div>
        </div>
        <div
          className={`progress-step ${versions.some((v) => ["PENDING_APPROVAL", "APPROVED", "PUBLISHED"].includes(v.status)) ? "active" : ""}`}
        >
          <span>4</span>
          <div>
            <strong>Approve & publish</strong>
            <small>Governed release</small>
          </div>
        </div>
      </section>

      <section className="datasets-grid dataset-summary-grid">
        <article className="datasets-card dataset-summary-card">
          <div className="card-heading-row">
            <div>
              <p className="dataset-eyebrow">Dataset profile</p>
              <h2>Metadata</h2>
            </div>
          </div>
          <dl className="dataset-metadata-list">
            <dt>Institutional owner</dt>
            <dd>{ownerName}</dd>
            <dt>Category</dt>
            <dd>{dataset.category ?? "Not specified"}</dd>
            <dt>Expected format</dt>
            <dd>{dataset.expected_format}</dd>
            <dt>Update frequency</dt>
            <dd>{dataset.update_frequency ?? "Not specified"}</dd>
          </dl>
        </article>

        <article className="datasets-card dataset-summary-card">
          <div className="card-heading-row">
            <div>
              <p className="dataset-eyebrow">Provenance</p>
              <h2>Data source</h2>
            </div>
            <span className="dataset-count-badge">{sources.length}</span>
          </div>
          {sources.length ? (
            <div className="source-list">
              {sources.map((source) => (
                <div className="source-item" key={source.id}>
                  <strong>{source.name}</strong>
                  <span>
                    {source.source_type} · {source.update_method ?? "Update method not specified"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="dataset-muted">No source configured yet.</p>
          )}
          <details className="dataset-advanced-panel">
            <summary>{sources.length ? "Add another source" : "Configure source"}</summary>
            <form className="dataset-form source-form" onSubmit={(event) => void addSource(event)}>
              <label>
                Source name
                <input
                  required
                  value={sourceName}
                  onChange={(event) => setSourceName(event.target.value)}
                />
              </label>
              <label>
                Update method
                <input
                  value={updateMethod}
                  onChange={(event) => setUpdateMethod(event.target.value)}
                />
              </label>
              <label>
                Secret reference <span className="optional-label">optional</span>
                <input
                  value={secretRef}
                  onChange={(event) => setSecretRef(event.target.value)}
                  placeholder="secret://provider/connection"
                />
              </label>
              <button type="submit">Add source</button>
            </form>
          </details>
        </article>
      </section>

      <section className="datasets-card ingestion-card">
        <div className="ingestion-card-header">
          <div>
            <p className="dataset-eyebrow">Step 2 · Ingestion</p>
            <h2>Upload and inspect CSV</h2>
            <p>
              Select a CSV and CRAM will detect its columns and data types before creating a
              version.
            </p>
          </div>
          <span className="schema-mode-badge">Automatic schema detection</span>
        </div>

        <form onSubmit={(event) => void upload(event)}>
          <label className={`csv-dropzone ${file ? "has-file" : ""}`}>
            <input
              key={fileInputKey}
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => void selectFile(event.target.files?.[0] ?? null)}
            />
            <span className="csv-upload-icon">CSV</span>
            <strong>{file ? file.name : "Choose a CSV file"}</strong>
            <small>
              {file
                ? `${formatBytes(file.size)} · ready for review`
                : "CSV up to 10 MiB · UTF-8 recommended"}
            </small>
          </label>

          {previewError && <p className="validation-error preview-error">{previewError}</p>}

          {preview && (
            <div className="csv-preview-panel">
              <div className="csv-preview-summary">
                <div>
                  <span>Rows detected</span>
                  <strong>{preview.rowCount.toLocaleString()}</strong>
                </div>
                <div>
                  <span>Columns detected</span>
                  <strong>{preview.fields.length}</strong>
                </div>
                <div>
                  <span>Registered schema</span>
                  <strong>{fields.length || "New"}</strong>
                </div>
              </div>

              <div className="schema-review-heading">
                <div>
                  <h3>Detected schema</h3>
                  <p>Review what CRAM found before the file is committed.</p>
                </div>
                <span>
                  {fields.length
                    ? "Compared with registered schema"
                    : "Will become the initial schema"}
                </span>
              </div>
              <div className="schema-table-wrap">
                <table className="schema-review-table">
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Detected type</th>
                      <th>Requirement</th>
                      <th>Schema status</th>
                      <th>Sample</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.fields.map((detected) => {
                      const configured = fields.find((field) => field.name === detected.name);
                      const compatible = configured
                        ? schemaCompatible(configured.data_type, detected.data_type)
                        : true;
                      return (
                        <tr key={detected.name}>
                          <td>
                            <strong>{detected.name}</strong>
                          </td>
                          <td>
                            <span className="type-pill">{detected.data_type}</span>
                          </td>
                          <td>{detected.is_required ? "Required" : "May contain blanks"}</td>
                          <td>
                            {configured ? (
                              <span
                                className={`schema-status ${compatible ? "matched" : "conflict"}`}
                              >
                                {compatible ? "Matched" : `Conflict: ${configured.data_type}`}
                              </span>
                            ) : (
                              <span className="schema-status new">New field</span>
                            )}
                          </td>
                          <td className="sample-values">
                            {detected.sample_values.join(" · ") || "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {preview.sampleRows.length > 0 && (
                <details className="sample-preview">
                  <summary>Preview sample rows</summary>
                  <div className="schema-table-wrap">
                    <table>
                      <thead>
                        <tr>
                          {preview.fields.map((field) => (
                            <th key={field.name}>{field.name}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {preview.sampleRows.map((row, index) => (
                          <tr key={index}>
                            {preview.fields.map((field) => (
                              <td key={field.name}>{row[field.name] || "—"}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}

              <div className="upload-review-actions">
                <p>
                  <strong>Nothing is published by uploading.</strong> CRAM creates a version that
                  must still pass validation and approval.
                </p>
                <button
                  className="primary-upload-button"
                  type="submit"
                  disabled={
                    busy ||
                    preview.fields.some((detected) => {
                      const configured = fields.find((field) => field.name === detected.name);
                      return configured
                        ? !schemaCompatible(configured.data_type, detected.data_type)
                        : false;
                    })
                  }
                >
                  {busy ? "Uploading…" : "Upload & create version"}
                </button>
              </div>
            </div>
          )}
        </form>

        <details className="dataset-advanced-panel schema-advanced">
          <summary>Advanced schema settings</summary>
          <p className="dataset-muted">
            Automatic detection is recommended. Add a field manually only when institutional
            governance requires a predefined schema.
          </p>
          <form className="dataset-form" onSubmit={(event) => void addField(event)}>
            <label>
              Field
              <input
                required
                value={fieldName}
                onChange={(event) => setFieldName(event.target.value)}
              />
            </label>
            <label>
              Type
              <select value={fieldType} onChange={(event) => setFieldType(event.target.value)}>
                <option>string</option>
                <option>number</option>
                <option>integer</option>
                <option>datetime</option>
              </select>
            </label>
            <button type="submit">Add required field</button>
          </form>
          {fields.length > 0 && (
            <div className="registered-schema-list">
              {fields.map((field) => (
                <span key={field.id}>
                  {field.name} <small>{field.data_type}</small>
                </span>
              ))}
            </div>
          )}
        </details>
      </section>

      <section className="datasets-card version-history-card">
        <div className="ingestion-card-header">
          <div>
            <p className="dataset-eyebrow">Governance lifecycle</p>
            <h2>Version history</h2>
            <p>Validate every uploaded version before submitting it for institutional approval.</p>
          </div>
          <span className="dataset-count-badge">{versions.length}</span>
        </div>
        {versions.length === 0 ? (
          <div className="empty-version-state">
            <strong>No versions yet</strong>
            <span>Select a CSV above to create the first governed version.</span>
          </div>
        ) : (
          <div className="dataset-versions">
            {versions.map((version) => (
              <article key={version.id} className="dataset-version">
                <header>
                  <div>
                    <strong>Version {version.version_number}</strong>
                    <span>Created {new Date(version.created_at).toLocaleString()}</span>
                  </div>
                  <span className={`dataset-status status-${version.status.toLowerCase()}`}>
                    {version.status.replaceAll("_", " ")}
                  </span>
                </header>
                <div className="version-facts">
                  <span>
                    <strong>{version.row_count?.toLocaleString() ?? "—"}</strong> rows
                  </span>
                  <span>
                    <strong>{version.checksum_sha256?.slice(0, 12) ?? "—"}</strong> checksum
                  </span>
                </div>
                <div className="dataset-actions">
                  {["UPLOADED", "VALIDATION_FAILED", "VALIDATED"].includes(version.status) && (
                    <button
                      type="button"
                      className="primary-action"
                      onClick={() => void validate(version.id)}
                    >
                      {version.status === "VALIDATED" ? "Run validation again" : "Validate data"}
                    </button>
                  )}
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={() => void showValidations(version.id)}
                  >
                    Validation results
                  </button>
                  {version.status === "VALIDATED" && (
                    <button
                      type="button"
                      className="primary-action"
                      onClick={() => void submit(version.id)}
                    >
                      Submit for approval
                    </button>
                  )}
                  {version.status === "APPROVED" && (
                    <button
                      type="button"
                      className="primary-action"
                      onClick={() => void publish(version.id)}
                    >
                      Publish version
                    </button>
                  )}
                </div>
                {validations[version.id]?.map((run) => (
                  <div
                    key={run.id}
                    className={`validation-result validation-${run.status.toLowerCase()}`}
                  >
                    <div className="validation-summary">
                      <strong>{run.status}</strong>
                      <span>{run.total_rows.toLocaleString()} rows checked</span>
                      <span>{run.error_count} errors</span>
                      <span>{run.warning_count} warnings</span>
                    </div>
                    {run.errors.slice(0, 12).map((issue) => (
                      <p
                        key={issue.id}
                        className={
                          issue.severity === "ERROR" ? "validation-error" : "validation-warning"
                        }
                      >
                        {issue.severity} · row {issue.row_number ?? "—"} ·{" "}
                        {issue.field_name ?? "record"}: {issue.message}
                      </p>
                    ))}
                    {run.errors.length > 12 && (
                      <p className="dataset-muted">Showing the first 12 validation findings.</p>
                    )}
                  </div>
                ))}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
