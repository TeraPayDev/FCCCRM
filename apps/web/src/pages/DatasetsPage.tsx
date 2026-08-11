import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, dataPlatformApi, type Dataset, type Organisation } from "../api/client";
import { loadTokens } from "../auth/session";
import "./datasets.css";

export function DatasetsPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [query, setQuery] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("");
  const [category, setCategory] = useState("");
  const [frequency, setFrequency] = useState("");
  const [message, setMessage] = useState("");

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
        const [page, orgs] = await Promise.all([
          dataPlatformApi.datasets(accessToken),
          api.organisations(accessToken),
        ]);
        if (!cancelled) {
          setDatasets(page.items);
          setOrganisations(orgs);
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
      setMessage("Dataset registered.");
      await reload("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to register dataset.");
    }
  }

  return (
    <main className="datasets-page">
      <header className="datasets-header">
        <div>
          <h1>CRAM Data Catalogue</h1>
          <p>Institutional datasets, sources, versions and governance metadata.</p>
        </div>
        <nav>
          <Link to="/profile">Profile</Link>
          <Link to="/approvals">Approval queue</Link>
        </nav>
      </header>
      <section className="datasets-card">
        <form
          className="datasets-search"
          onSubmit={(event) => {
            event.preventDefault();
            void reload();
          }}
        >
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search code or name"
          />
          <button type="submit">Search</button>
        </form>
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Dataset</th>
              <th>Owner</th>
              <th>Status</th>
              <th>Format</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((dataset) => (
              <tr key={dataset.id}>
                <td>{dataset.code}</td>
                <td>
                  <Link to={`/datasets/${dataset.id}`}>{dataset.name}</Link>
                </td>
                <td>
                  {organisations.find((item) => item.id === dataset.owner_organisation_id)?.name ??
                    dataset.owner_organisation_id}
                </td>
                <td>{dataset.status}</td>
                <td>{dataset.expected_format}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="datasets-card">
        <h2>Register dataset</h2>
        <form className="dataset-form" onSubmit={(event) => void create(event)}>
          <label>
            Code
            <input required value={code} onChange={(event) => setCode(event.target.value)} />
          </label>
          <label>
            Name
            <input required value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Owner
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
            <input value={category} onChange={(event) => setCategory(event.target.value)} />
          </label>
          <label>
            Update frequency
            <input value={frequency} onChange={(event) => setFrequency(event.target.value)} />
          </label>
          <button type="submit">Register</button>
        </form>
        {message && <p>{message}</p>}
      </section>
    </main>
  );
}
