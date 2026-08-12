from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.identity import User
from app.models.outputs import KnowledgeItem
from app.services.auth import permission_codes
from app.services.public_data import (
    PublicDataError,
    open_meteo_freetown,
    world_bank_sierra_leone,
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")

APP_GUIDE: tuple[tuple[str, str, str], ...] = (
    (
        "Overview",
        "/",
        "Executive entry point for CRAM platform health, governance and climate-risk modules.",
    ),
    (
        "Data Catalogue",
        "/datasets",
        "Register datasets, upload CSV versions, validate, submit for approval and publish governed releases.",
    ),
    (
        "GIS Explorer",
        "/map",
        "Explore MapLibre spatial layers including live-reference weather surfaces, trees, waterways and administrative boundaries.",
    ),
    (
        "Processing",
        "/processing",
        "Inspect ETL jobs, connector schedules, integration runs, retries and processing health.",
    ),
    (
        "Heat Analytics",
        "/heat",
        "Review governed observations plus live weather and historical temperature context. Official indicators require an approved methodology.",
    ),
    (
        "Flood Monitoring",
        "/flood",
        "Combine rainfall context, mapped waterways, governed incidents and approved flood-risk indicators.",
    ),
    (
        "Tree Monitoring",
        "/trees",
        "Track governed tree inventory, planting batches, inspections, species and community-mapped reference trees.",
    ),
    (
        "Vulnerability",
        "/vulnerability",
        "Review socio-economic context and approved vulnerability indicators without inventing unapproved scores.",
    ),
    (
        "Citizen Reports",
        "/citizen-reports",
        "Moderate citizen-submitted hazard observations. Public reporting supports GPS, optional evidence and offline queueing.",
    ),
    (
        "Reporting",
        "/reports",
        "Generate reproducible climate-risk reports through background processing and retain source-version provenance.",
    ),
    (
        "Knowledge Hub",
        "/knowledge",
        "Search governed methods, policies, climate studies and reports alongside authoritative public references.",
    ),
    (
        "User Management",
        "/users",
        "Administrators create, edit, activate/deactivate users and assign institutions and CRAM RBAC roles.",
    ),
    (
        "Approvals",
        "/approvals",
        "Permission-separated review and approval of validated dataset versions.",
    ),
    (
        "Audit Trail",
        "/audit",
        "Append-only trace of security, governance, dataset and operational activity.",
    ),
    (
        "Advanced Analytics",
        "/analytics",
        "Historical climate exploration, Earth-observation catalogues and engineering predictive demonstrations. Operational thresholds remain methodology-governed.",
    ),
)


@dataclass(frozen=True)
class ContextItem:
    label: str
    title: str
    text: str
    source_type: str
    url: str | None = None


def _terms(value: str) -> set[str]:
    return set(_WORD_RE.findall(value.lower()))


def _score(query: set[str], text: str) -> float:
    if not query:
        return 0.0
    words = _terms(text)
    overlap = len(query & words)
    if overlap == 0:
        return 0.0
    return overlap / math.sqrt(max(1, len(words)))


def _allowed_knowledge(session: Session, user: User) -> list[KnowledgeItem]:
    rows = list(
        session.scalars(
            select(KnowledgeItem)
            .where(KnowledgeItem.is_active.is_(True))
            .order_by(KnowledgeItem.updated_at.desc())
            .limit(250)
        ).all()
    )
    perms = permission_codes(user)
    can_restricted = bool(perms & {"reports.read", "datasets.read"})
    return [item for item in rows if item.visibility == "PUBLIC" or can_restricted]


def _knowledge_context(session: Session, user: User, question: str) -> list[ContextItem]:
    query = _terms(question)
    ranked: list[tuple[float, KnowledgeItem]] = []
    for item in _allowed_knowledge(session, user):
        haystack = " ".join(
            [
                item.title,
                item.summary or "",
                item.content_type,
                " ".join(item.tags or []),
            ]
        )
        ranked.append((_score(query, haystack), item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    result: list[ContextItem] = []
    for _, item in ranked[:5]:
        result.append(
            ContextItem(
                label=f"CRAM-{len(result) + 1}",
                title=item.title,
                text=(item.summary or "No summary provided.")[:1800],
                source_type="CRAM Knowledge Hub",
                url=item.file_reference,
            )
        )
    return result


def _guide_context(question: str, current_path: str | None) -> list[ContextItem]:
    query = _terms(question)
    ranked: list[tuple[float, tuple[str, str, str]]] = []
    for row in APP_GUIDE:
        title, path, description = row
        bonus = 1.5 if current_path and current_path.startswith(path) and path != "/" else 0.0
        ranked.append((_score(query, f"{title} {description}") + bonus, row))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    selected = [row for score, row in ranked if score > 0][:4]
    if not selected:
        selected = [row for _, row in ranked[:2]]
    return [
        ContextItem(
            label=f"APP-{index + 1}",
            title=title,
            text=f"Route: {path}. {description}",
            source_type="CRAM application guide",
        )
        for index, (title, path, description) in enumerate(selected)
    ]


def _live_context(question: str) -> list[ContextItem]:
    lower = question.lower()
    result: list[ContextItem] = []
    if any(
        word in lower
        for word in ("weather", "temperature", "rain", "rainfall", "heat", "humidity", "today")
    ):
        try:
            payload = open_meteo_freetown()
            current = payload.get("current")
            if isinstance(current, dict):
                result.append(
                    ContextItem(
                        label="LIVE-WEATHER",
                        title="Open-Meteo Freetown current weather",
                        text=json.dumps(current, default=str)[:1800],
                        source_type="Open-Meteo public API",
                        url="https://open-meteo.com/",
                    )
                )
        except PublicDataError:
            pass
    if any(
        word in lower
        for word in ("population", "vulnerability", "poverty", "urban", "sierra leone", "socio")
    ):
        try:
            payload = world_bank_sierra_leone()
            records = payload.get("records")
            if isinstance(records, list):
                result.append(
                    ContextItem(
                        label="LIVE-WB",
                        title="World Bank Sierra Leone indicators",
                        text=json.dumps(records[:8], default=str)[:2200],
                        source_type="World Bank Indicators API",
                        url="https://data.worldbank.org/country/sierra-leone",
                    )
                )
        except PublicDataError:
            pass
    return result


def build_context(
    session: Session, user: User, question: str, current_path: str | None
) -> list[ContextItem]:
    items = _knowledge_context(session, user, question)
    items.extend(_guide_context(question, current_path))
    items.extend(_live_context(question))
    return items[:10]


def _openai_text(payload: dict[str, object]) -> str:
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    pieces: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    pieces.append(text)
    return "\n".join(pieces).strip()


def ask_openai(*, question: str, context: list[ContextItem], username: str) -> tuple[str, str]:
    settings = get_settings()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value().strip():
        raise RuntimeError(
            "CRAM AI Assistant is not configured. Add OPENAI_API_KEY to the server environment."
        )

    context_text = "\n\n".join(
        f"[{item.label}] {item.title}\nSource: {item.source_type}\n{item.text}" for item in context
    )
    instructions = (
        "You are the CRAM AI Assistant for Freetown City Council's Climate Risk Analytics Management Platform. "
        "Help authenticated users operate CRAM and understand climate-risk concepts using the supplied grounding context. "
        "For CRAM application questions, give direct and practical guidance based on the CRAM application guide and governed Knowledge Hub context. "
        "When a relevant CRAM route is supplied, mention the human-readable module name and route naturally, for example Data Catalogue (/datasets). "
        "Do not invent buttons, fields, workflow states, operational values, approvals, methodologies, thresholds, permissions or risk scores that are not supported by the supplied context. "
        "Do not place grounding labels such as [APP-1], [CRAM-1], [LIVE-WEATHER] or [LIVE-WB] in the answer text; the application displays sources separately. "
        "Do not use hyphen or dash bullets. Prefer short paragraphs and numbered steps when a sequence is useful. "
        "Avoid unnecessary nested lists and avoid a separate limitations section unless an important limitation materially affects the answer. "
        "When information is unavailable, state the limitation briefly and naturally rather than listing everything you do not know. "
        "Clearly distinguish public-reference information from governed or approved CRAM records. "
        "Keep responses concise, practical, professional and easy to read inside a compact chat interface."
    )
    input_text = (
        f"Authenticated user: {username}\n\nGrounding context:\n{context_text or 'No matching CRAM context was found.'}\n\n"
        f"Question: {question}"
    )
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(
            {
                "model": settings.openai_model,
                "instructions": instructions,
                "input": input_text,
                "store": False,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.openai_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"OpenAI request failed ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("OpenAI service is currently unreachable from the CRAM server.") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("OpenAI returned an unexpected response.")
    answer = _openai_text(payload)
    if not answer:
        raise RuntimeError("OpenAI returned no answer text.")
    model = str(payload.get("model") or settings.openai_model)
    return answer, model
