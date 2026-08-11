from __future__ import annotations

from datetime import UTC, datetime

MOCK_DATA: dict[str, list[dict[str, object]]] = {
    "SLMET": [
        {
            "station_code": "SLMET-DEMO-01",
            "observed_at": "2026-08-11T12:00:00Z",
            "temperature_c": 31.2,
            "humidity_pct": 78.0,
        }
    ],
    "NDMA": [{"incident_ref": "NDMA-DEMO-001", "hazard": "FLOOD", "severity": "MODERATE"}],
    "NACSA": [{"area_code": "NACSA-DEMO", "vulnerability_index": 0.54}],
    "STATSSL": [{"area_code": "STATSSL-DEMO", "population": 12500, "period": "2026"}],
}


def sandbox_pull(
    institution: str, configuration: dict[str, object] | None = None
) -> dict[str, object]:
    key = institution.upper().replace("-", "").replace(" ", "")
    aliases = {"STATISTICSSIERRALEONE": "STATSSL", "STATISTICSSL": "STATSSL", "SLMET": "SLMET"}
    key = aliases.get(key, key)
    records = MOCK_DATA.get(key, [])
    return {
        "institution": institution,
        "mode": "sandbox",
        "received_at": datetime.now(UTC).isoformat(),
        "records": records,
        "record_count": len(records),
        "configuration_echo": configuration or {},
    }
