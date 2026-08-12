from app.services.assistant import _openai_text, _score


def test_assistant_keyword_score_prefers_overlap() -> None:
    query = {"flood", "rainfall", "freetown"}
    assert _score(query, "Freetown flood monitoring uses rainfall context") > _score(
        query, "User administration and password controls"
    )


def test_assistant_extracts_responses_api_output_text() -> None:
    payload: dict[str, object] = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Grounded CRAM answer."},
                ],
            }
        ]
    }
    assert _openai_text(payload) == "Grounded CRAM answer."
