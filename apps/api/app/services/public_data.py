from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings

FREETOWN_LAT = 8.4657
FREETOWN_LON = -13.2317
FREETOWN_BBOX = [-13.35, 8.35, -13.10, 8.55]
USER_AGENT = "CRAM/0.1 public-data-connector (+Freetown City Council)"


class PublicDataError(RuntimeError):
    pass


_CACHE: dict[str, tuple[float, object]] = {}


def _as_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return list(value)


def _clean_number(value: object) -> object:
    if isinstance(value, (int, float)) and float(value) <= -900:
        return None
    return value


def _cached(key: str, ttl_seconds: int, loader: Callable[[], object]) -> object:
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < ttl_seconds:
        return cached[1]
    value = loader()
    _CACHE[key] = (now, value)
    return value


def _request_json(
    url: str,
    *,
    query: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
    timeout: float = 20,
) -> object:
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = None
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data else "GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload: object = json.load(response)
            return payload
    except Exception as exc:  # pragma: no cover - network/environment specific
        raise PublicDataError(f"Public data request failed for {url}: {exc}") from exc


def open_meteo_freetown() -> dict[str, object]:
    def load() -> dict[str, object]:
        payload = _request_json(
            "https://api.open-meteo.com/v1/forecast",
            query={
                "latitude": str(FREETOWN_LAT),
                "longitude": str(FREETOWN_LON),
                "current": ",".join(
                    [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "precipitation",
                        "rain",
                        "surface_pressure",
                        "cloud_cover",
                        "wind_speed_10m",
                    ]
                ),
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,rain",
                "forecast_days": "2",
                "timezone": "UTC",
            },
        )
        if not isinstance(payload, dict):
            raise PublicDataError("Open-Meteo returned an unexpected response.")
        current = _as_dict(payload.get("current"))
        hourly = _as_dict(payload.get("hourly"))
        times = _as_list(hourly.get("time"))
        temperatures = _as_list(hourly.get("temperature_2m"))
        humidity = _as_list(hourly.get("relative_humidity_2m"))
        precipitation = _as_list(hourly.get("precipitation"))
        rain = _as_list(hourly.get("rain"))
        forecast = []
        for index, observed_at in enumerate(times[:48]):
            forecast.append(
                {
                    "observed_at": observed_at,
                    "temperature_c": temperatures[index] if index < len(temperatures) else None,
                    "humidity_pct": humidity[index] if index < len(humidity) else None,
                    "precipitation_mm": precipitation[index]
                    if index < len(precipitation)
                    else None,
                    "rain_mm": rain[index] if index < len(rain) else None,
                }
            )
        return {
            "source": "Open-Meteo",
            "location": "Freetown, Sierra Leone",
            "latitude": FREETOWN_LAT,
            "longitude": FREETOWN_LON,
            "current": current,
            "hourly": forecast,
            "record_count": len(forecast),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": "Live public reference data; not authoritative until ingested and approved in CRAM.",
        }

    return _cached("open-meteo-freetown", 300, load)  # type: ignore[return-value]


def open_meteo_historical_freetown(years: int = 5) -> dict[str, object]:
    years = max(1, min(years, 20))

    def load() -> dict[str, object]:
        end = datetime.now(UTC).date() - timedelta(days=6)
        start = end - timedelta(days=365 * years)
        payload = _request_json(
            "https://archive-api.open-meteo.com/v1/archive",
            query={
                "latitude": str(FREETOWN_LAT),
                "longitude": str(FREETOWN_LON),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum",
                "timezone": "UTC",
            },
            timeout=30,
        )
        if not isinstance(payload, dict):
            raise PublicDataError("Open-Meteo historical API returned an unexpected response.")
        daily = _as_dict(payload.get("daily"))
        times = _as_list(daily.get("time"))
        max_t = _as_list(daily.get("temperature_2m_max"))
        min_t = _as_list(daily.get("temperature_2m_min"))
        precipitation = _as_list(daily.get("precipitation_sum"))
        rain = _as_list(daily.get("rain_sum"))
        records = [
            {
                "date": day,
                "temperature_max_c": max_t[index] if index < len(max_t) else None,
                "temperature_min_c": min_t[index] if index < len(min_t) else None,
                "precipitation_mm": precipitation[index] if index < len(precipitation) else None,
                "rain_mm": rain[index] if index < len(rain) else None,
            }
            for index, day in enumerate(times)
        ]
        return {
            "source": "Open-Meteo Historical Weather API",
            "scope": f"Freetown daily historical reference, approximately {years} years",
            "records": records,
            "record_count": len(records),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": "Reanalysis/historical reference data; operational indicators still require governed CRAM datasets and approved methodologies.",
        }

    return _cached(f"open-meteo-history-{years}", 21600, load)  # type: ignore[return-value]


def open_meteo_freetown_grid() -> dict[str, object]:
    """Return a real public-reference weather surface across greater Freetown.

    Values come directly from Open-Meteo grid cells. They are contextual observations,
    not an FCC-approved heat or flood risk index.
    """

    points = [
        ("Central Freetown", 8.4840, -13.2340),
        ("Aberdeen", 8.4932, -13.2892),
        ("Lumley", 8.4565, -13.2800),
        ("Congo Cross", 8.4742, -13.2560),
        ("Brookfields", 8.4650, -13.2450),
        ("Kissy", 8.4710, -13.1960),
        ("Wellington", 8.4370, -13.1700),
        ("Calaba Town", 8.4045, -13.1680),
        ("Regent", 8.3945, -13.2230),
        ("Goderich", 8.4250, -13.2860),
        ("Juba", 8.4440, -13.2730),
        ("Hastings", 8.3915, -13.1430),
    ]

    def load() -> dict[str, object]:
        features: list[dict[str, object]] = []
        errors: list[str] = []
        for name, latitude, longitude in points:
            try:
                payload = _request_json(
                    "https://api.open-meteo.com/v1/forecast",
                    query={
                        "latitude": str(latitude),
                        "longitude": str(longitude),
                        "current": "temperature_2m,relative_humidity_2m,precipitation,rain",
                        "timezone": "UTC",
                    },
                    timeout=12,
                )
                current = _as_dict(_as_dict(payload).get("current"))
                features.append(
                    _feature(
                        "Point",
                        [longitude, latitude],
                        {
                            "kind": "weather-grid",
                            "name": name,
                            "source": "Open-Meteo",
                            "temperature_c": _clean_number(current.get("temperature_2m")),
                            "humidity_pct": _clean_number(current.get("relative_humidity_2m")),
                            "precipitation_mm": _clean_number(current.get("precipitation")),
                            "rain_mm": _clean_number(current.get("rain")),
                            "observed_at": current.get("time"),
                        },
                    )
                )
            except PublicDataError as exc:
                errors.append(f"{name}: {exc}")
        if not features:
            raise PublicDataError("Open-Meteo grid could not retrieve any Freetown cells.")
        return {
            "type": "FeatureCollection",
            "features": features,
            "record_count": len(features),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "errors": errors,
            "governance": "Public-reference weather surface only; not an approved FCC heat or flood risk index.",
        }

    return _cached("open-meteo-freetown-grid", 600, load)  # type: ignore[return-value]


def world_bank_climate_resources(limit: int = 12) -> dict[str, object]:
    """Return recent World Bank climate/disaster-risk knowledge resources.

    The Documents & Reports API is a public World Bank disclosure/search API.
    Results remain external references until a CRAM user explicitly saves one
    into the governed Knowledge Hub.
    """

    def load() -> dict[str, object]:
        payload = _request_json(
            "https://search.worldbank.org/api/v2/wds",
            query={
                "format": "json",
                "qterm": "climate risk resilience urban flood heat Sierra Leone",
                "rows": str(max(1, min(limit, 25))),
                "os": "0",
            },
            timeout=25,
        )
        root = _as_dict(payload)
        documents = root.get("documents")
        candidates: list[dict[str, object]] = []
        if isinstance(documents, dict):
            candidates = [_as_dict(value) for value in documents.values()]
        elif isinstance(documents, list):
            candidates = [_as_dict(value) for value in documents]

        records: list[dict[str, object]] = []
        for item in candidates:
            title = item.get("display_title") or item.get("title") or item.get("docna")
            if not title:
                continue
            url = item.get("url") or item.get("pdfurl") or item.get("txturl")
            records.append(
                {
                    "external_id": item.get("id") or item.get("docid"),
                    "title": str(title),
                    "organisation": "World Bank",
                    "resource_type": item.get("docty") or item.get("majdocty") or "Publication",
                    "publication_date": item.get("docdt") or item.get("disclosure_date"),
                    "authors": item.get("authr"),
                    "url": url,
                    "source": "World Bank Documents & Reports API",
                    "tags": ["climate risk", "resilience", "public reference"],
                }
            )
        return {
            "source": "World Bank Documents & Reports API",
            "records": records[:limit],
            "record_count": len(records[:limit]),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": "External public knowledge references; save to CRAM to create a governed repository record.",
        }

    return _cached(f"world-bank-climate-resources-{limit}", 21600, load)  # type: ignore[return-value]


def copernicus_cds_readiness() -> dict[str, object]:
    settings = get_settings()
    configured = settings.copernicus_cds_key is not None and bool(
        settings.copernicus_cds_key.get_secret_value().strip()
    )
    return {
        "source": "Copernicus Climate Data Store",
        "api_url": settings.copernicus_cds_url,
        "configured": configured,
        "status": "READY" if configured else "CREDENTIALS_REQUIRED",
        "records": [
            {
                "capability": "CDS programmatic retrieval",
                "status": "Ready for configured personal access token"
                if configured
                else "Add COPERNICUS_CDS_KEY to the server environment",
            },
            {
                "capability": "Dataset terms",
                "status": "Terms must be accepted on each CDS dataset before first download",
            },
        ],
        "record_count": 2,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "governance": "Credentials are server-side only; CRAM never exposes the personal access token to the browser.",
    }


def nasa_power_freetown(days: int = 45) -> dict[str, object]:
    days = max(7, min(days, 366))

    def load() -> dict[str, object]:
        end = datetime.now(UTC).date()
        start = end - timedelta(days=days - 1)
        payload = _request_json(
            "https://power.larc.nasa.gov/api/temporal/daily/point",
            query={
                "parameters": "T2M,RH2M,PRECTOTCORR,PS,WS10M",
                "community": "AG",
                "longitude": str(FREETOWN_LON),
                "latitude": str(FREETOWN_LAT),
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "format": "JSON",
            },
        )
        if not isinstance(payload, dict):
            raise PublicDataError("NASA POWER returned an unexpected response.")
        properties = payload.get("properties")
        parameters = properties.get("parameter") if isinstance(properties, dict) else None
        if not isinstance(parameters, dict):
            parameters = {}
        dates: set[str] = set()
        for series in parameters.values():
            if isinstance(series, dict):
                dates.update(str(key) for key in series)
        records = []
        for day in sorted(dates):
            records.append(
                {
                    "date": day,
                    "temperature_c": _series_value(parameters, "T2M", day),
                    "humidity_pct": _series_value(parameters, "RH2M", day),
                    "precipitation_mm": _series_value(parameters, "PRECTOTCORR", day),
                    "surface_pressure_kpa": _series_value(parameters, "PS", day),
                    "wind_speed_m_s": _series_value(parameters, "WS10M", day),
                }
            )
        return {
            "source": "NASA POWER",
            "location": "Freetown, Sierra Leone",
            "latitude": FREETOWN_LAT,
            "longitude": FREETOWN_LON,
            "records": records,
            "record_count": len(records),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": "Analysis-ready public reference series; operational use still requires CRAM governance.",
        }

    return _cached(f"nasa-power-{days}", 3600, load)  # type: ignore[return-value]


def _series_value(parameters: dict[str, object], code: str, day: str) -> object:
    series = parameters.get(code)
    return _clean_number(series.get(day)) if isinstance(series, dict) else None


def world_bank_sierra_leone() -> dict[str, object]:
    indicators = {
        "SP.POP.TOTL": "Population, total",
        "SP.URB.TOTL.IN.ZS": "Urban population (% of total)",
        "AG.LND.FRST.ZS": "Forest area (% of land area)",
        "EN.ATM.PM25.MC.M3": "PM2.5 air pollution, mean annual exposure",
    }

    def load() -> dict[str, object]:
        records: list[dict[str, object]] = []
        for code, label in indicators.items():
            payload = _request_json(
                f"https://api.worldbank.org/v2/country/SLE/indicator/{code}",
                query={"format": "json", "per_page": "12", "mrv": "12"},
            )
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            if not isinstance(rows, list):
                continue
            latest = next(
                (
                    row
                    for row in rows
                    if isinstance(row, dict) and isinstance(row.get("value"), (int, float))
                ),
                None,
            )
            if latest:
                records.append(
                    {
                        "indicator_code": code,
                        "indicator": label,
                        "year": latest.get("date"),
                        "value": latest.get("value"),
                        "unit": latest.get("unit") or "",
                        "geography": "Sierra Leone",
                    }
                )
        return {
            "source": "World Bank Indicators API",
            "scope": "Sierra Leone national context",
            "records": records,
            "record_count": len(records),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": (
                "Reference socio-economic context only. CRAM does not convert these values into a "
                "vulnerability score without an approved methodology."
            ),
        }

    return _cached("world-bank-sle", 21600, load)  # type: ignore[return-value]


def osm_freetown() -> dict[str, object]:
    south, west, north, east = (
        FREETOWN_BBOX[1],
        FREETOWN_BBOX[0],
        FREETOWN_BBOX[3],
        FREETOWN_BBOX[2],
    )

    def load() -> dict[str, object]:
        query = f"""
[out:json][timeout:25];
(
  node[\"natural\"=\"tree\"]({south},{west},{north},{east});
  way[\"waterway\"]({south},{west},{north},{east});
  relation[\"boundary\"=\"administrative\"][\"name\"~\"Freetown\",i]({south},{west},{north},{east});
);
out geom;
""".strip()
        encoded = urllib.parse.urlencode({"data": query}).encode("utf-8")
        request = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=encoded,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                payload: object = json.load(response)
        except Exception as exc:  # pragma: no cover - network/environment specific
            raise PublicDataError(f"OpenStreetMap Overpass request failed: {exc}") from exc
        payload_dict = _as_dict(payload)
        elements = _as_list(payload_dict.get("elements"))
        features: list[dict[str, object]] = []
        tree_count = 0
        waterway_count = 0
        boundary_segments = 0
        for element in elements:
            if not isinstance(element, dict):
                continue
            tags = _as_dict(element.get("tags"))
            element_type = element.get("type")
            if element_type == "node" and tags.get("natural") == "tree":
                lat = element.get("lat")
                lon = element.get("lon")
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    tree_count += 1
                    features.append(
                        _feature(
                            "Point",
                            [lon, lat],
                            {"kind": "tree", "source": "OpenStreetMap", "name": tags.get("name")},
                        )
                    )
            elif element_type == "way" and "waterway" in tags:
                geometry = element.get("geometry")
                coords = _overpass_coords(geometry)
                if len(coords) >= 2:
                    waterway_count += 1
                    features.append(
                        _feature(
                            "LineString",
                            coords,
                            {
                                "kind": "waterway",
                                "source": "OpenStreetMap",
                                "name": tags.get("name") or tags.get("waterway"),
                                "waterway": tags.get("waterway"),
                            },
                        )
                    )
            elif element_type == "relation" and tags.get("boundary") == "administrative":
                members = _as_list(element.get("members"))
                for member in members:
                    if not isinstance(member, dict):
                        continue
                    coords = _overpass_coords(member.get("geometry"))
                    if len(coords) >= 2:
                        boundary_segments += 1
                        features.append(
                            _feature(
                                "LineString",
                                coords,
                                {
                                    "kind": "administrative-boundary",
                                    "source": "OpenStreetMap",
                                    "name": tags.get("name") or "Freetown",
                                },
                            )
                        )
        return {
            "source": "OpenStreetMap Overpass API",
            "query_extent": FREETOWN_BBOX,
            "tree_count": tree_count,
            "waterway_count": waterway_count,
            "boundary_segments": boundary_segments,
            "features": features,
            "record_count": len(features),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": (
                "Community-mapped reference data. It supplements but does not replace authoritative FCC/agency GIS layers."
            ),
        }

    return _cached("osm-freetown", 3600, load)  # type: ignore[return-value]


def _overpass_coords(value: object) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    coords: list[list[float]] = []
    for point in value:
        if not isinstance(point, dict):
            continue
        lat = point.get("lat")
        lon = point.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            coords.append([float(lon), float(lat)])
    return coords


def _feature(
    geometry_type: str, coordinates: object, properties: dict[str, object]
) -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": {"type": geometry_type, "coordinates": coordinates},
        "properties": properties,
    }


def copernicus_stac_freetown(limit: int = 12) -> dict[str, object]:
    def load() -> dict[str, object]:
        end = datetime.now(UTC)
        start = end - timedelta(days=90)
        payload = _request_json(
            "https://stac.dataspace.copernicus.eu/v1/search",
            body={
                "collections": ["sentinel-2-l2a"],
                "bbox": FREETOWN_BBOX,
                "datetime": f"{start.isoformat().replace('+00:00', 'Z')}/{end.isoformat().replace('+00:00', 'Z')}",
                "limit": max(1, min(limit, 50)),
            },
        )
        payload_dict = _as_dict(payload)
        features = _as_list(payload_dict.get("features"))
        records = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            props = _as_dict(feature.get("properties"))
            records.append(
                {
                    "id": feature.get("id"),
                    "collection": feature.get("collection"),
                    "datetime": props.get("datetime") or props.get("start_datetime"),
                    "cloud_cover": props.get("eo:cloud_cover"),
                    "geometry": feature.get("geometry"),
                }
            )
        return {
            "source": "Copernicus Data Space STAC",
            "scope": "Freetown 90-day Earth-observation catalogue preview",
            "records": records,
            "record_count": len(records),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": (
                "Catalogue metadata is public reference data. Climate Data Store retrieval requires a configured CDS personal access token and dataset terms acceptance."
            ),
        }

    return _cached("copernicus-stac-freetown", 3600, load)  # type: ignore[return-value]


def usgs_stac_freetown(limit: int = 10) -> dict[str, object]:
    def load() -> dict[str, object]:
        end = datetime.now(UTC)
        start = end - timedelta(days=365)
        payload = _request_json(
            "https://landsatlook.usgs.gov/stac-server/search",
            body={
                "collections": ["landsat-c2l2-sr"],
                "bbox": FREETOWN_BBOX,
                "datetime": f"{start.isoformat().replace('+00:00', 'Z')}/{end.isoformat().replace('+00:00', 'Z')}",
                "limit": max(1, min(limit, 50)),
            },
        )
        payload_dict = _as_dict(payload)
        features = _as_list(payload_dict.get("features"))
        records = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            props = _as_dict(feature.get("properties"))
            records.append(
                {
                    "id": feature.get("id"),
                    "collection": feature.get("collection"),
                    "datetime": props.get("datetime"),
                    "cloud_cover": props.get("eo:cloud_cover"),
                    "geometry": feature.get("geometry"),
                }
            )
        return {
            "source": "USGS EROS STAC",
            "scope": "Freetown Landsat catalogue preview",
            "records": records,
            "record_count": len(records),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "governance": "Public Earth-observation catalogue reference; selected products should be governed as CRAM datasets before operational use.",
        }

    return _cached("usgs-stac-freetown", 3600, load)  # type: ignore[return-value]


def gis_reference_features() -> dict[str, object]:
    osm = osm_freetown()
    weather = open_meteo_freetown()
    features = _as_list(osm.get("features"))
    current = _as_dict(weather.get("current"))
    features.append(
        _feature(
            "Point",
            [FREETOWN_LON, FREETOWN_LAT],
            {
                "kind": "weather-reference",
                "source": "Open-Meteo",
                "name": "Freetown weather reference point",
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
            },
        )
    )
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "CRAM live public reference aggregation",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "authoritative": False,
        },
    }


PUBLIC_CONNECTORS: tuple[dict[str, object], ...] = (
    {
        "code": "OPEN-METEO-FREETOWN",
        "institution": "Open-Meteo",
        "connector_type": "OPEN_METEO",
        "base_url": "https://api.open-meteo.com/v1/forecast",
        "interval_minutes": 60,
    },
    {
        "code": "NASA-POWER-FREETOWN",
        "institution": "NASA POWER",
        "connector_type": "NASA_POWER",
        "base_url": "https://power.larc.nasa.gov/api/temporal/daily/point",
        "interval_minutes": 1440,
    },
    {
        "code": "OSM-FREETOWN",
        "institution": "OpenStreetMap",
        "connector_type": "OVERPASS_OSM",
        "base_url": "https://overpass-api.de/api/interpreter",
        "interval_minutes": 1440,
    },
    {
        "code": "WORLD-BANK-SLE",
        "institution": "World Bank",
        "connector_type": "WORLD_BANK",
        "base_url": "https://api.worldbank.org/v2",
        "interval_minutes": 1440,
    },
    {
        "code": "COPERNICUS-STAC-FREETOWN",
        "institution": "Copernicus Data Space",
        "connector_type": "COPERNICUS_STAC",
        "base_url": "https://stac.dataspace.copernicus.eu/v1/",
        "interval_minutes": 360,
    },
    {
        "code": "USGS-STAC-FREETOWN",
        "institution": "USGS EROS",
        "connector_type": "USGS_STAC",
        "base_url": "https://landsatlook.usgs.gov/stac-server",
        "interval_minutes": 720,
    },
)


def run_public_connector(connector_type: str) -> dict[str, object]:
    handlers: dict[str, Callable[[], dict[str, object]]] = {
        "OPEN_METEO": open_meteo_freetown,
        "OPEN_METEO_HISTORY": open_meteo_historical_freetown,
        "NASA_POWER": nasa_power_freetown,
        "OVERPASS_OSM": osm_freetown,
        "WORLD_BANK": world_bank_sierra_leone,
        "COPERNICUS_STAC": copernicus_stac_freetown,
        "USGS_STAC": usgs_stac_freetown,
    }
    try:
        return handlers[connector_type]()
    except KeyError as exc:
        raise PublicDataError(f"Unsupported public connector type: {connector_type}") from exc
