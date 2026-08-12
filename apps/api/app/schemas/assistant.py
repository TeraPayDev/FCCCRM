from pydantic import BaseModel, Field


class AssistantAsk(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    current_path: str | None = Field(default=None, max_length=300)


class AssistantCitation(BaseModel):
    label: str
    title: str
    source_type: str
    url: str | None = None


class AssistantAnswer(BaseModel):
    answer: str
    model: str
    grounded: bool
    citations: list[AssistantCitation] = Field(default_factory=list)
