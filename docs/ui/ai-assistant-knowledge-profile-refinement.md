# CRAM AI Assistant, Knowledge Hub and Profile Refinement

## Scope

This focused refinement changes only the account/profile experience, Knowledge Hub and a new authenticated CRAM AI Assistant. Existing GIS, datasets, processing, analytics, reporting, citizen reporting and governance workflows are not replaced.

## CRAM AI Assistant

The assistant is exposed through `POST /api/v1/assistant/ask` and is authenticated with the same CRAM access token as the rest of the application. The OpenAI key is used only by the FastAPI service and is never sent to the browser.

Server environment variables:

```text
OPENAI_API_KEY=<project API key>
OPENAI_MODEL=gpt-5-mini
OPENAI_TIMEOUT_SECONDS=45
```

The implementation calls the OpenAI Responses API from the backend. Grounding context is assembled before the model call from:

- permission-filtered governed Knowledge Hub records;
- a concise CRAM application/module guide;
- live Open-Meteo context for weather/heat/rain questions;
- World Bank Sierra Leone indicators for socio-economic/vulnerability questions.

Responses include source labels and the UI exposes a Sources used section. The assistant is deliberately instructed not to invent approved methodologies, operational thresholds, permissions, risk scores or official values.

AI requests are audit logged as `assistant.ask` without storing the full question text. Only metadata such as question length, route, model and grounding source labels is written to the audit trail.

## Knowledge Hub

The Knowledge Hub now distinguishes:

- governed CRAM records;
- live World Bank Documents & Reports references;
- curated authoritative references from NASA POWER, Copernicus CDS, USGS EROS and the World Bank Climate Change Knowledge Portal.

The service tries multiple World Bank climate queries and deduplicates results. Curated official references keep the demonstration useful if the external search API is temporarily unavailable. Public references do not become governed CRAM content automatically; an authorized user must select **Save to CRAM**.

Users with `reports.manage` can add governed knowledge items with title, type, summary, tags and an approved external/object reference.

## Profile

The profile page is now an account workspace rather than an identity/debug dump. It presents account details, role badges, session state, a collapsible effective-permissions view, access-management action where authorized and a single sign-out action.

## Deployment

After overlaying this patch, preserve the existing server `.env`, add `OPENAI_API_KEY`, optionally set `OPENAI_MODEL`, rebuild `api` and `web`, then validate:

```bash
docker compose build api web
docker compose up -d --force-recreate api web
docker compose exec api sh -c 'test -n "$OPENAI_API_KEY" && echo PASS || echo FAIL'
curl -s http://127.0.0.1:8000/api/v1/health
```

Do not place the OpenAI key in `apps/web/.env*`, React code, browser storage or source control.
