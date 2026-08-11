import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  dataPlatformApi,
  type Dataset,
  type DatasetField,
  type DatasetSource,
  type DatasetVersion,
  type ValidationRun,
} from "../api/client";
import { loadTokens } from "../auth/session";
import "./datasets.css";

export function DatasetDetailPage() {
  const { datasetId = "" } = useParams();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<Dataset | null>(null);
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
        const [detail, sourceData, fieldData, versionData] = await Promise.all([
          dataPlatformApi.dataset(accessToken, datasetId),
          dataPlatformApi.sources(accessToken, datasetId),
          dataPlatformApi.fields(accessToken, datasetId),
          dataPlatformApi.versions(accessToken, datasetId),
        ]);
        if (!cancelled) {
          setDataset(detail);
          setSources(sourceData);
          setFields(fieldData);
          setVersions(versionData);
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
        <p>{message || "Loading dataset..."}</p>
      </main>
    );

  return (
    <main className="datasets-page">
      <header className="datasets-header">
        <div>
          <h1>{dataset.name}</h1>
          <p>
            {dataset.code} · {dataset.status} · {dataset.sensitivity}
          </p>
        </div>
        <Link to="/datasets">Catalogue</Link>
      </header>
      {message && <p className="datasets-message">{message}</p>}
      <section className="datasets-grid">
        <article className="datasets-card">
          <h2>Metadata</h2>
          <dl>
            <dt>Owner</dt>
            <dd>{dataset.owner_organisation_id}</dd>
            <dt>Expected format</dt>
            <dd>{dataset.expected_format}</dd>
            <dt>Update frequency</dt>
            <dd>{dataset.update_frequency ?? "Not specified"}</dd>
          </dl>
        </article>
        <article className="datasets-card">
          <h2>Sources</h2>
          {sources.length ? (
            sources.map((source) => (
              <p key={source.id}>
                <strong>{source.name}</strong> · {source.source_type} ·{" "}
                {source.update_method ?? "unspecified update method"}
                {source.connection_secret_ref
                  ? ` · secret ref: ${source.connection_secret_ref}`
                  : ""}
              </p>
            ))
          ) : (
            <p>No source configured yet.</p>
          )}
          <form className="dataset-form" onSubmit={(event) => void addSource(event)}>
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
        </article>
      </section>
      <section className="datasets-card">
        <h2>Schema / validation fields</h2>
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
        <ul>
          {fields.map((field) => (
            <li key={field.id}>
              {field.ordinal}: {field.name} ({field.data_type}){" "}
              {field.is_required ? "required" : "optional"}
            </li>
          ))}
        </ul>
      </section>
      <section className="datasets-card">
        <h2>Upload CSV</h2>
        <form className="dataset-form" onSubmit={(event) => void upload(event)}>
          <input
            type="file"
            accept=".csv,text/csv"
            required
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <button type="submit">Upload original file</button>
        </form>
      </section>
      <section className="datasets-card">
        <h2>Version history</h2>
        <div className="dataset-versions">
          {versions.map((version) => (
            <article key={version.id} className="dataset-version">
              <header>
                <strong>Version {version.version_number}</strong>
                <span>{version.status}</span>
              </header>
              <p>
                Rows: {version.row_count ?? "—"} · SHA-256:{" "}
                {version.checksum_sha256?.slice(0, 16) ?? "—"}…
              </p>
              <div className="dataset-actions">
                <button type="button" onClick={() => void validate(version.id)}>
                  Validate
                </button>
                <button type="button" onClick={() => void showValidations(version.id)}>
                  Results
                </button>
                {version.status === "VALIDATED" && (
                  <button type="button" onClick={() => void submit(version.id)}>
                    Submit
                  </button>
                )}
                {version.status === "APPROVED" && (
                  <button type="button" onClick={() => void publish(version.id)}>
                    Publish
                  </button>
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
                      {issue.severity} row {issue.row_number ?? "—"} {issue.field_name ?? ""}:{" "}
                      {issue.message}
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
