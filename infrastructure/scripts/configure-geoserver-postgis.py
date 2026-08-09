#!/usr/bin/env python3
"""
CRAM Milestone 2 - Configure and verify GeoServer -> PostGIS connectivity.

Infrastructure-only script:
1. Creates GeoServer workspace "cram" if needed.
2. Creates PostGIS datastore "cram-postgis" if needed.
3. Verifies GeoServer can query the datastore.

No CRAM application/domain tables or GIS layers are created.
"""

from __future__ import annotations

import base64
import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"

WORKSPACE = "cram"
DATASTORE = "cram-postgis"
GEOSERVER_BASE = "http://localhost:8080/geoserver"
REST_BASE = f"{GEOSERVER_BASE}/rest"


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise RuntimeError(f"Environment file not found: {path}")

    values: dict[str, str] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        values[key] = value

    return values


def auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def request(
    method: str,
    url: str,
    username: str,
    password: str,
    body: str | None = None,
    content_type: str = "text/xml",
    accept: str = "application/json",
) -> tuple[int, bytes]:
    data = body.encode("utf-8") if body is not None else None

    headers = {
        "Authorization": auth_header(username, password),
        "Accept": accept,
    }

    if body is not None:
        headers["Content-Type"] = content_type

    req = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def verify_auth(username: str, password: str) -> bool:
    status, _ = request(
        "GET",
        f"{REST_BASE}/workspaces.json",
        username,
        password,
    )
    return status == 200


def resolve_geoserver_credentials(env: dict[str, str]) -> tuple[str, str]:
    username = env.get("GEOSERVER_ADMIN_USER", "admin")
    password = env.get("GEOSERVER_ADMIN_PASSWORD", "")

    if password and verify_auth(username, password):
        return username, password

    if password:
        print(
            "GeoServer credentials in .env did not authenticate. "
            "Enter the credentials that currently work in the GeoServer web interface."
        )
    else:
        print(
            "GeoServer admin password was not found in .env. "
            "Enter the credentials that currently work in the GeoServer web interface."
        )

    username = input(f"GeoServer admin user [{username}]: ").strip() or username
    password = getpass.getpass("GeoServer admin password: ")

    if not verify_auth(username, password):
        raise RuntimeError("GeoServer authentication failed.")

    return username, password


def ensure_workspace(username: str, password: str) -> None:
    workspace_url = f"{REST_BASE}/workspaces/{WORKSPACE}.json"
    status, _ = request("GET", workspace_url, username, password)

    if status == 200:
        print(f"Workspace '{WORKSPACE}' already exists.")
        return

    if status != 404:
        raise RuntimeError(
            f"Could not check workspace '{WORKSPACE}'. HTTP status: {status}"
        )

    body = f"<workspace><name>{escape(WORKSPACE)}</name></workspace>"

    status, response = request(
        "POST",
        f"{REST_BASE}/workspaces",
        username,
        password,
        body=body,
    )

    if status not in {200, 201}:
        raise RuntimeError(
            f"Could not create workspace '{WORKSPACE}'. "
            f"HTTP status: {status}; response: {response.decode(errors='replace')}"
        )

    print(f"Created workspace '{WORKSPACE}'.")


def ensure_datastore(
    username: str,
    password: str,
    env: dict[str, str],
) -> None:
    store_url = (
        f"{REST_BASE}/workspaces/{WORKSPACE}/datastores/{DATASTORE}.json"
    )
    status, _ = request("GET", store_url, username, password)

    if status == 200:
        print(f"Datastore '{DATASTORE}' already exists.")
        return

    if status != 404:
        raise RuntimeError(
            f"Could not check datastore '{DATASTORE}'. HTTP status: {status}"
        )

    db_name = env["POSTGRES_DB"]
    db_user = env["POSTGRES_USER"]
    db_password = env["POSTGRES_PASSWORD"]

    # Keep the datastore XML to the minimal PostGIS parameters documented
    # by GeoServer's REST examples. Avoid optional parameters until the
    # datastore is established successfully.
    body = f"""<dataStore>
  <name>{escape(DATASTORE)}</name>
  <connectionParameters>
    <host>db</host>
    <port>5432</port>
    <database>{escape(db_name)}</database>
    <user>{escape(db_user)}</user>
    <passwd>{escape(db_password)}</passwd>
    <dbtype>postgis</dbtype>
  </connectionParameters>
</dataStore>"""

    status, response = request(
        "POST",
        f"{REST_BASE}/workspaces/{WORKSPACE}/datastores",
        username,
        password,
        body=body,
        content_type="text/xml",
    )

    if status not in {200, 201}:
        raise RuntimeError(
            f"Could not create datastore '{DATASTORE}'. "
            f"HTTP status: {status}; response: {response.decode(errors='replace')}"
        )

    print(f"Created datastore '{DATASTORE}'.")


def verify_datastore_connection(username: str, password: str) -> None:
    url = (
        f"{REST_BASE}/workspaces/{WORKSPACE}/datastores/{DATASTORE}"
        "/featuretypes.json?list=available"
    )

    status, response = request(
        "GET",
        url,
        username,
        password,
        accept="application/json",
    )

    if status != 200:
        raise RuntimeError(
            "GeoServer could not query available feature types from PostGIS. "
            f"HTTP status: {status}; response: {response.decode(errors='replace')}"
        )

    payload = json.loads(response.decode("utf-8") or "{}")
    available = payload.get("featureTypes", {}).get("featureType", [])

    if isinstance(available, dict):
        available = [available]

    names = [
        item.get("name", str(item))
        for item in available
        if isinstance(item, dict)
    ]

    print("GeoServer -> PostGIS connectivity verified.")

    if names:
        print("Available feature types:", ", ".join(names))
    else:
        print(
            "Available feature types: none currently present in the selected "
            "schema (the datastore query succeeded, so connectivity is verified)."
        )


def main() -> int:
    try:
        env = load_env(ENV_FILE)

        required = [
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        ]

        missing = [name for name in required if not env.get(name)]
        if missing:
            raise RuntimeError(
                "Missing required values in .env: " + ", ".join(missing)
            )

        username, password = resolve_geoserver_credentials(env)

        ensure_workspace(username, password)
        ensure_datastore(username, password, env)
        verify_datastore_connection(username, password)

        print()
        print(
            "CRAM GeoServer/PostGIS infrastructure configuration "
            "completed successfully."
        )
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
