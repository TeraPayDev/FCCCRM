import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  api,
  dataPlatformApi,
  type CurrentUser,
  type Dataset,
  type Organisation,
} from "../api/client";
import { loadTokens } from "../auth/session";
import { EmptyState, PageHeader, StatusBadge } from "../components/Page";
import "./datasets.css";

export function DatasetsPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [query, setQuery] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("");
  const [category, setCategory] = useState("");
  const [frequency, setFrequency] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

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
        const [page, orgs, currentUser] = await Promise.all([
          dataPlatformApi.datasets(accessToken),
          api.organisations(accessToken),
          api.me(accessToken),
        ]);
        if (!cancelled) {
          setDatasets(page.items);
          setOrganisations(orgs);
          setMe(currentUser);
          setOwner(orgs[0]?.id ?? "");
        }
      } catch (error) {
        if (!cancelled)
          setMessage(error instanceof Error ? error.message : "Unable to load datasets.");
      }
    }
    void loadInitial();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  async function reload(search = query) {
    const tokens = loadTokens();
    if (!tokens) return navigate("/login");
    const params = new URLSearchParams();
    if (search.trim()) params.set("q", search.trim());
    const page = await dataPlatformApi.datasets(tokens.access_token, params.toString());
    setDatasets(page.items);
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const tokens = loadTokens();
    if (!tokens || !owner) return;
    setBusy(true);
    setMessage("");
    try {
      await dataPlatformApi.createDataset(tokens.access_token, {
        code: code.trim(),
        name: name.trim(),
        owner_organisation_id: owner,
        category: category.trim() || undefined,
        sensitivity: "INTERNAL",
        expected_format: "CSV",
        update_frequency: frequency.trim() || undefined,
      });
      setCode("");
      setName("");
      setCategory("");
      setFrequency("");
      setMessage("Dataset registered successfully.");
      await reload("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to register dataset.");
    } finally {
      setBusy(false);
    }
  }

  const canManage = me?.permissions.includes("datasets.manage") ?? false;

  return (
    <main className="datasets-page">
      <PageHeader
        eyebrow="Data management"
        title="Data catalogue"
        description="Institutional datasets, sources, versions and governance metadata in one searchable catalogue."
        actions={
          me?.permissions.includes("datasets.approve") ? (
            <Link className="button" to="/approvals">
              Open approval queue
            </Link>
          ) : undefined
        }
      />
      {message && (
        <p
          className={`notice ${message.toLowerCase().includes("unable") || message.toLowerCase().includes("failed") ? "notice-error" : "notice-success"}`}
        >
          {message}
        </p>
      )}

      <section className="datasets-card catalogue-panel">
        <div className="catalogue-toolbar">
          <form
            className="datasets-search"
            onSubmit={(event) => {
              event.preventDefault();
              void reload();
            }}
          >
            <input
              aria-label="Search datasets"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by dataset code or name…"
            />
            <button type="submit">Search</button>
            {query && (
              <button
                className="text-button"
                type="button"
                onClick={() => {
                  setQuery("");
                  void reload("");
                }}
              >
                Clear
              </button>
            )}
          </form>
          <span className="catalogue-count">{datasets.length} shown</span>
        </div>
        {datasets.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dataset</th>
                  <th>Owner</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Format</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((dataset) => (
                  <tr key={dataset.id}>
                    <td>
                      <Link className="dataset-name-link" to={`/datasets/${dataset.id}`}>
                        <strong>{dataset.name}</strong>
                        <span>{dataset.code}</span>
                      </Link>
                    </td>
                    <td>
                      {organisations.find((item) => item.id === dataset.owner_organisation_id)
                        ?.name ?? "Institutional owner"}
                    </td>
                    <td>{dataset.category ?? "—"}</td>
                    <td>
                      <StatusBadge value={dataset.status} />
                    </td>
                    <td>{dataset.expected_format}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No datasets found"
            description="Adjust the search or register the first institutional dataset if you have catalogue-management permission."
          />
        )}
      </section>

      {canManage && (
        <section className="datasets-card">
          <div className="card-header">
            <div>
              <h2>Register a dataset</h2>
              <p className="card-subtitle">
                Create the logical data product before sources, fields and uploaded versions are
                added.
              </p>
            </div>
          </div>
          <form
            className="dataset-form dataset-register-grid"
            onSubmit={(event) => void create(event)}
          >
            <label>
              Dataset code
              <input
                required
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="e.g. SL-MET-WEATHER"
              />
            </label>
            <label>
              Dataset name
              <input required value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label>
              Institutional owner
              <select required value={owner} onChange={(event) => setOwner(event.target.value)}>
                {organisations.map((organisation) => (
                  <option key={organisation.id} value={organisation.id}>
                    {organisation.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Category
              <input
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                placeholder="Weather, GIS, socioeconomic…"
              />
            </label>
            <label>
              Update frequency
              <input
                value={frequency}
                onChange={(event) => setFrequency(event.target.value)}
                placeholder="Daily, monthly, ad hoc…"
              />
            </label>
            <button className="button-primary" type="submit" disabled={busy}>
              {busy ? "Registering…" : "Register dataset"}
            </button>
          </form>
        </section>
      )}
    </main>
  );
}
