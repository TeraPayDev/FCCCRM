from fastapi import APIRouter, HTTPException

from app.db.session import get_db_session
from app.schemas.assistant import AssistantAnswer, AssistantAsk, AssistantCitation
from app.security.dependencies import CurrentUser
from app.services.assistant import ask_openai, build_context
from app.services.audit import record_audit_event

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/ask", response_model=AssistantAnswer)
def ask(payload: AssistantAsk, user: CurrentUser) -> AssistantAnswer:
    session = get_db_session()
    try:
        context = build_context(session, user, payload.question, payload.current_path)
        try:
            answer, model = ask_openai(
                question=payload.question,
                context=context,
                username=user.username,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        record_audit_event(
            session,
            action="assistant.ask",
            resource_type="ai_assistant",
            actor=user,
            details={
                "question_length": len(payload.question),
                "current_path": payload.current_path,
                "model": model,
                "source_labels": [item.label for item in context],
            },
        )
        session.commit()
        return AssistantAnswer(
            answer=answer,
            model=model,
            grounded=bool(context),
            citations=[
                AssistantCitation(
                    label=item.label,
                    title=item.title,
                    source_type=item.source_type,
                    url=item.url,
                )
                for item in context
            ],
        )
    finally:
        session.close()
