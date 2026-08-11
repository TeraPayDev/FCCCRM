import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api, type Organisation, type OrganisationUser } from "../api/client";
import { clearTokens, loadTokens } from "../auth/session";
import { PageHeader, StatusBadge } from "../components/Page";
import "./organisations.css";

export function OrganisationsPage() {
  const navigate = useNavigate();

  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [users, setUsers] = useState<OrganisationUser[]>([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const tokens = loadTokens();

    if (!tokens) {
      navigate("/login");
      return;
    }

    const accessToken = tokens.access_token;

    try {
      const me = await api.me(accessToken);

      if (!me.permissions.includes("users.manage")) {
        setMessage("Your account does not have organisation-management permission.");
        return;
      }

      const [organisationData, userData] = await Promise.all([
        api.organisations(accessToken),
        api.organisationUsers(accessToken),
      ]);

      setOrganisations(organisationData);
      setUsers(userData);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearTokens();
        navigate("/login");
        return;
      }

      setMessage(error instanceof ApiError ? error.message : "Unable to load organisations.");
    }
  }

  useEffect(() => {
    const storedTokens = loadTokens();

    if (!storedTokens) {
      navigate("/login");
      return;
    }

    const accessToken = storedTokens.access_token;
    let cancelled = false;

    async function loadInitialData() {
      try {
        const me = await api.me(accessToken);

        if (cancelled) {
          return;
        }

        if (!me.permissions.includes("users.manage")) {
          setMessage("Your account does not have organisation-management permission.");
          return;
        }

        const [organisationData, userData] = await Promise.all([
          api.organisations(accessToken),
          api.organisationUsers(accessToken),
        ]);

        if (cancelled) {
          return;
        }

        setOrganisations(organisationData);
        setUsers(userData);
      } catch (error) {
        if (cancelled) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          clearTokens();
          navigate("/login");
          return;
        }

        setMessage(error instanceof ApiError ? error.message : "Unable to load organisations.");
      }
    }

    void loadInitialData();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  async function createOrganisation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const tokens = loadTokens();

    if (!tokens) {
      navigate("/login");
      return;
    }

    const accessToken = tokens.access_token;

    setBusy(true);
    setMessage("");

    try {
      await api.createOrganisation(accessToken, code.trim(), name.trim());

      setCode("");
      setName("");

      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Unable to create organisation.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleOrganisation(organisation: Organisation) {
    const tokens = loadTokens();

    if (!tokens) {
      navigate("/login");
      return;
    }

    const accessToken = tokens.access_token;

    setBusy(true);
    setMessage("");

    try {
      await api.updateOrganisation(accessToken, organisation.id, {
        is_active: !organisation.is_active,
      });

      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Unable to update organisation.");
    } finally {
      setBusy(false);
    }
  }

  async function renameOrganisation(organisation: Organisation) {
    const nextName = window.prompt("Organisation name", organisation.name)?.trim();

    if (!nextName || nextName === organisation.name) {
      return;
    }

    const tokens = loadTokens();

    if (!tokens) {
      navigate("/login");
      return;
    }

    const accessToken = tokens.access_token;

    setBusy(true);
    setMessage("");

    try {
      await api.updateOrganisation(accessToken, organisation.id, {
        name: nextName,
      });

      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Unable to rename organisation.");
    } finally {
      setBusy(false);
    }
  }

  async function removeOrganisation(organisation: Organisation) {
    const confirmed = window.confirm(
      `Delete ${organisation.code}? Deactivate referenced organisations instead.`,
    );

    if (!confirmed) {
      return;
    }

    const tokens = loadTokens();

    if (!tokens) {
      navigate("/login");
      return;
    }

    const accessToken = tokens.access_token;

    setBusy(true);
    setMessage("");

    try {
      await api.deleteOrganisation(accessToken, organisation.id);

      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Unable to delete organisation.");
    } finally {
      setBusy(false);
    }
  }

  async function assignUser(user: OrganisationUser, organisationId: string) {
    const tokens = loadTokens();

    if (!tokens) {
      navigate("/login");
      return;
    }

    const accessToken = tokens.access_token;

    setBusy(true);
    setMessage("");

    try {
      await api.assignUserOrganisation(accessToken, user.id, organisationId || null);

      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Unable to assign organisation.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="organisation-page">
      <PageHeader
        eyebrow="Governance"
        title="Organisations"
        description="Manage FCC and partner institutions and link users to their institutional owner."
      />

      {message && <p className="organisation-message">{message}</p>}

      <section className="organisation-panel">
        <h2>Register organisation</h2>

        <form className="organisation-form" onSubmit={createOrganisation}>
          <label>
            Code
            <input value={code} onChange={(event) => setCode(event.target.value)} required />
          </label>

          <label>
            Name
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>

          <button type="submit" disabled={busy}>
            Add organisation
          </button>
        </form>
      </section>

      <section className="organisation-panel">
        <h2>Institution register</h2>

        <div className="organisation-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {organisations.map((organisation) => (
                <tr key={organisation.id}>
                  <td>{organisation.code}</td>

                  <td>{organisation.name}</td>

                  <td>
                    <StatusBadge value={organisation.is_active ? "Active" : "Inactive"} />
                  </td>

                  <td className="organisation-actions">
                    <button
                      type="button"
                      onClick={() => renameOrganisation(organisation)}
                      disabled={busy}
                    >
                      Rename
                    </button>

                    <button
                      type="button"
                      onClick={() => toggleOrganisation(organisation)}
                      disabled={busy}
                    >
                      {organisation.is_active ? "Deactivate" : "Activate"}
                    </button>

                    <button
                      type="button"
                      onClick={() => removeOrganisation(organisation)}
                      disabled={busy}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}

              {organisations.length === 0 && (
                <tr>
                  <td colSpan={4}>No organisations are currently registered.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="organisation-panel">
        <h2>User institutional ownership</h2>

        <div className="organisation-table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Organisation</th>
              </tr>
            </thead>

            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.username}</td>

                  <td>{user.email}</td>

                  <td>
                    <select
                      value={user.organisation_id ?? ""}
                      onChange={(event) => assignUser(user, event.target.value)}
                      disabled={busy}
                    >
                      <option value="">Unassigned</option>

                      {organisations
                        .filter((organisation) => organisation.is_active)
                        .map((organisation) => (
                          <option key={organisation.id} value={organisation.id}>
                            {organisation.code} — {organisation.name}
                          </option>
                        ))}
                    </select>
                  </td>
                </tr>
              ))}

              {users.length === 0 && (
                <tr>
                  <td colSpan={3}>No users are currently available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
