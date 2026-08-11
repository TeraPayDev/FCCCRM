import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  api,
  dataPlatformApi,
  type CurrentUser,
  type Dataset,
  type DatasetField,
  type DatasetSource,
  type DatasetVersion,
  type ValidationRun,
} from "../api/client";
import { loadTokens } from "../auth/session";
import { PageHeader, StatusBadge } from "../components/Page";
import "./datasets.css";

export function DatasetDetailPage() {
  const { datasetId = "" } = useParams();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [sources, setSources] = useState<DatasetSource[]>([]);
  const [fields, setFields] = useState<DatasetField[]>([]);
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [validations, setValidations] = useState<Record<string, ValidationRun[]>>({});
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [fieldType, setFieldType] = useState("string");
  const [sourceName, setSourceName] = useState("");
  const [updateMethod, setUpdateMethod] = useState("manual CSV upload");
  const [secretRef, setSecretRef] = useState("");

  async function reload() {
    const tokens = loadTokens();
    if (!tokens) return navigate("/login");
    const [detail, sourceData, fieldData, versionData] = await Promise.all([
      dataPlatformApi.dataset(tokens.access_token, datasetId),
      dataPlatformApi.sources(tokens.access_token, datasetId),
      dataPlatformApi.fields(tokens.access_token, datasetId),
      dataPlatformApi.versions(tokens.access_token, datasetId),
    ]);
    setDataset(detail);
    setSources(sourceData);
    setFields(fieldData);
    setVersions(versionData);
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
        const [detail, sourceData, fieldData, versionData, currentUser] = await Promise.all([
          dataPlatformApi.dataset(accessToken, datasetId),
          dataPlatformApi.sources(accessToken, datasetId),
          dataPlatformApi.fields(accessToken, datasetId),
          dataPlatformApi.versions(accessToken, datasetId),
          api.me(accessToken),
        ]);
        if (!cancelled) {
          setDataset(detail);
          setSources(sourceData);
          setFields(fieldData);
          setVersions(versionData);
          setMe(currentUser);
        }
      } catch (error) {
        if (!cancelled)
          setMessage(error instanceof Error ? error.message : "Unable to load dataset.");
      }
    }
    void loadInitial();
    return () => {
      cancelled = true;
    };
  }, [datasetId, navigate]);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const tokens = loadTokens();
    if (!tokens || !file) return;
    try {
      await dataPlatformApi.uploadCsv(tokens.access_token, datasetId, file, sources[0]?.id);
      setFile(null);
      setMessage("CSV uploaded and version created.");
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
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
        "Dataset source stored. Only a secret reference is retained; credentials are not stored here.",
      );
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to add dataset source.");
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
      setMessage("Field definition stored.");
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to add field.");
    }
  }

  async function validate(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    const run = await dataPlatformApi.validateVersion(tokens.access_token, versionId);
    setValidations((current) => ({ ...current, [versionId]: [run] }));
    setMessage(
      `Validation ${run.status}: ${run.error_count} errors, ${run.warning_count} warnings.`,
    );
    await reload();
  }

  async function showValidations(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    const runs = await dataPlatformApi.validations(tokens.access_token, versionId);
    setValidations((current) => ({ ...current, [versionId]: runs }));
  }

  async function submit(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      await dataPlatformApi.submitVersion(tokens.access_token, versionId);
      setMessage("Submitted for approval.");
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Submission failed.");
    }
  }

  async function publish(versionId: string) {
    const tokens = loadTokens();
    if (!tokens) return;
    try {
      await dataPlatformApi.publish(tokens.access_token, versionId);
      setMessage("Version published.");
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Publication failed.");
    }
  }

  if (!dataset)
    return (
      <main className="datasets-page">
        <section className="datasets-card">
          <p>{message || "Loading dataset…"}</p>
        </section>
      </main>
    );

  const canManage = me?.permissions.includes("datasets.manage") ?? false;
  const canUpload = me?.permissions.includes("datasets.upload") ?? false;
  const canValidate = me?.permissions.includes("datasets.validate") ?? false;
  const canApprove = me?.permissions.includes("datasets.approve") ?? false;
  const canPublish = me?.permissions.includes("datasets.publish") ?? false;

  const latestVersion = versions[0];
  const lifecycle = [
    "DRAFT",
    "UPLOADED",
    "VALIDATING",
    "VALIDATED",
    "PENDING_APPROVAL",
    "APPROVED",
    "PUBLISHED",
  ];
  const currentIndex = latestVersion ? lifecycle.indexOf(latestVersion.status) : -1;

  return (
    <main className="datasets-page">
      <PageHeader
        eyebrow={`Dataset · ${dataset.code}`}
        title={dataset.name}
        description={
          dataset.description ??
          "Versioned institutional dataset with governed source, validation and publication history."
        }
        actions={
          <Link className="button" to="/datasets">
            ← Catalogue
          </Link>
        }
      />
      {message && <p className="datasets-message">{message}</p>}

      <section className="datasets-card lifecycle-card">
        <div className="card-header">
          <div>
            <h2>Governance lifecycle</h2>
            <p className="card-subtitle">Current progress for the latest dataset version.</p>
          </div>
          {latestVersion ? (
            <StatusBadge value={latestVersion.status} />
          ) : (
            <StatusBadge value="Draft" />
          )}
        </div>
        <div className="lifecycle-track">
          {lifecycle.map((step, index) => (
            <div className={`lifecycle-step${index <= currentIndex ? " complete" : ""}`} key={step}>
              <span>{index + 1}</span>
              <small>{step.replaceAll("_", " ")}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="datasets-grid">
        <article className="datasets-card">
          <div className="card-header">
            <div>
              <h2>Dataset metadata</h2>
              <p className="card-subtitle">Catalogue identity and institutional ownership.</p>
            </div>
            <StatusBadge value={dataset.status} />
          </div>
          <dl>
            <dt>Owner organisation</dt>
            <dd>{dataset.owner_organisation_id}</dd>
            <dt>Sensitivity</dt>
            <dd>{dataset.sensitivity}</dd>
            <dt>Expected format</dt>
            <dd>{dataset.expected_format}</dd>
            <dt>Update frequency</dt>
            <dd>{dataset.update_frequency ?? "Not specified"}</dd>
            <dt>Category</dt>
            <dd>{dataset.category ?? "Not specified"}</dd>
          </dl>
        </article>

        <article className="datasets-card">
          <div className="card-header">
            <div>
              <h2>Sources</h2>
              <p className="card-subtitle">
                Origin and update method. Credentials are never stored here.
              </p>
            </div>
          </div>
          {sources.length ? (
            <div className="source-list">
              {sources.map((source) => (
                <div className="source-item" key={source.id}>
                  <strong>{source.name}</strong>
                  <span>
                    {source.source_type} · {source.update_method ?? "Update method not specified"}
                  </span>
                  {source.connection_secret_ref && <code>{source.connection_secret_ref}</code>}
                </div>
              ))}
            </div>
          ) : (
            <p className="card-subtitle">No source configured yet.</p>
          )}
          {canManage && (
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
                Secret reference
                <input
                  value={secretRef}
                  onChange={(event) => setSecretRef(event.target.value)}
                  placeholder="secret://provider/connection"
                />
              </label>
              <button type="submit">Add source</button>
            </form>
          )}
        </article>
      </section>

      <section className="datasets-card">
        <div className="card-header">
          <div>
            <h2>Schema and validation fields</h2>
            <p className="card-subtitle">
              Reusable field metadata drives validation without hard-coding climate assumptions.
            </p>
          </div>
          <span className="status-badge">{fields.length} fields</span>
        </div>
        {canManage && (
          <form className="dataset-form" onSubmit={(event) => void addField(event)}>
            <label>
              Field name
              <input
                required
                value={fieldName}
                onChange={(event) => setFieldName(event.target.value)}
              />
            </label>
            <label>
              Data type
              <select value={fieldType} onChange={(event) => setFieldType(event.target.value)}>
                <option>string</option>
                <option>number</option>
                <option>integer</option>
                <option>datetime</option>
              </select>
            </label>
            <button type="submit">Add required field</button>
          </form>
        )}
        {fields.length ? (
          <div className="field-grid">
            {fields.map((field) => (
              <div className="field-pill" key={field.id}>
                <strong>{field.name}</strong>
                <span>
                  {field.data_type} · {field.is_required ? "required" : "optional"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="card-subtitle">No field definitions stored yet.</p>
        )}
      </section>

      {canUpload && (
        <section className="datasets-card upload-card">
          <div>
            <h2>Upload CSV source file</h2>
            <p className="card-subtitle">
              The original file is preserved unchanged. CRAM records checksum, size, uploader and
              timestamp.
            </p>
          </div>
          <form className="upload-form" onSubmit={(event) => void upload(event)}>
            <label className="file-drop">
              Choose CSV
              <input
                type="file"
                accept=".csv,text/csv"
                required
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <span>{file ? file.name : "Select a UTF-8 CSV file"}</span>
            </label>
            <button className="button-primary" type="submit" disabled={!file}>
              Upload & create version
            </button>
          </form>
        </section>
      )}

      <section className="datasets-card">
        <div className="card-header">
          <div>
            <h2>Version history</h2>
            <p className="card-subtitle">
              Every accepted upload remains independently traceable through validation and
              publishing.
            </p>
          </div>
          <span className="status-badge">{versions.length} versions</span>
        </div>
        <div className="dataset-versions">
          {versions.map((version) => (
            <article key={version.id} className="dataset-version">
              <header>
                <div>
                  <strong>Version {version.version_number}</strong>
                  <span className="version-date">
                    {new Date(version.created_at).toLocaleString()}
                  </span>
                </div>
                <StatusBadge value={version.status} />
              </header>
              <p>
                Rows: {version.row_count ?? "—"} · SHA-256:{" "}
                {version.checksum_sha256?.slice(0, 16) ?? "—"}…
              </p>
              <div className="dataset-actions">
                {canValidate && (
                  <button type="button" onClick={() => void validate(version.id)}>
                    Run validation
                  </button>
                )}
                <button type="button" onClick={() => void showValidations(version.id)}>
                  Validation results
                </button>
                {version.status === "VALIDATED" && canManage && (
                  <button
                    className="button-primary"
                    type="button"
                    onClick={() => void submit(version.id)}
                  >
                    Submit for approval
                  </button>
                )}
                {version.status === "APPROVED" && canPublish && (
                  <button
                    className="button-primary"
                    type="button"
                    onClick={() => void publish(version.id)}
                  >
                    Publish version
                  </button>
                )}
                {version.status === "PENDING_APPROVAL" && canApprove && (
                  <Link className="button" to="/approvals">
                    Review in approval queue
                  </Link>
                )}
              </div>
              {validations[version.id]?.map((run) => (
                <div key={run.id} className="validation-result">
                  <strong>{run.status}</strong> · {run.error_count} errors · {run.warning_count}{" "}
                  warnings
                  {run.errors.map((issue) => (
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
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
