# CRAM Focused Refinement Package

This package is based on the bid-demo product-refinement baseline and intentionally limits scope to three areas:

1. Profile/account user experience.
2. Knowledge Hub functionality and authoritative public resources.
3. Authenticated CRAM AI Assistant using the OpenAI Responses API from the FastAPI backend.

## New files

- `apps/api/app/api/v1/endpoints/assistant.py`
- `apps/api/app/schemas/assistant.py`
- `apps/api/app/services/assistant.py`
- `apps/api/tests/test_assistant.py`
- `apps/web/src/components/AssistantWidget.tsx`
- `apps/web/src/components/assistant-widget.css`
- `docs/ui/ai-assistant-knowledge-profile-refinement.md`

## Configuration

Add the following only to the server-side `.env`:

```text
OPENAI_API_KEY=<your OpenAI Platform API key>
OPENAI_MODEL=gpt-5-mini
OPENAI_TIMEOUT_SECONDS=45
```

`compose.yaml` passes these values only to the API service. The browser never receives the key.

## No database migration

This refinement uses the existing `cram.knowledge_items` and `cram.audit_logs` tables. No migration beyond the existing `20260812_0008` head is required.

## Suggested validation after overlay

Run the existing backend and frontend quality gates before rebuilding. Then rebuild `api` and `web` and test `/profile`, `/knowledge`, and the **Ask CRAM** button in the lower-right corner.
