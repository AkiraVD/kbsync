"""The prompt is a graded requirement, so it is pinned, not trusted."""

from src.assistant import SYSTEM_PROMPT, Answer, parse_answer

VERBATIM = (
    "You are OptiBot, the customer-support bot for OptiSigns.com.\n"
    "\u2022 Tone: helpful, factual, concise.\n"
    "\u2022 Only answer using the uploaded docs.\n"
    "\u2022 Max 5 bullet points; else link to the doc.\n"
    '\u2022 Cite up to 3 "Article URL:" lines per reply.'
)


def test_system_prompt_is_the_briefs_prompt_byte_for_byte():
    assert SYSTEM_PROMPT == VERBATIM


def test_prompt_keeps_the_bullets_and_the_citation_wording():
    assert SYSTEM_PROMPT.count("\u2022") == 4
    assert '"Article URL:"' in SYSTEM_PROMPT
    assert "Max 5 bullet points" in SYSTEM_PROMPT


def test_parse_answer_collects_text_and_citations():
    payload = {
        "interaction": {
            "steps": [
                {"type": "file_search_call", "content": []},
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "text",
                            "text": "Open the app.",
                            "annotations": [
                                {
                                    "type": "file_citation",
                                    "file_name": "add-a-video.md",
                                    "source": "https://support.example.test/articles/42",
                                }
                            ],
                        }
                    ],
                },
            ]
        }
    }

    answer = parse_answer(payload)

    assert answer == Answer(
        text="Open the app.",
        citations=("https://support.example.test/articles/42",),
    )


def test_parse_answer_drops_duplicate_citations():
    source = "https://support.example.test/articles/42"
    payload = {
        "steps": [
            {
                "content": [
                    {"text": "One.", "annotations": [{"source": source}]},
                    {"text": "Two.", "annotations": [{"source": source}]},
                ]
            }
        ]
    }

    answer = parse_answer(payload)

    assert answer.citations == (source,)
    assert answer.text == "One.\nTwo."


def test_parse_answer_survives_an_answer_with_no_citations():
    payload = {"steps": [{"content": [{"text": "Plug and play means..."}]}]}

    assert parse_answer(payload) == Answer(text="Plug and play means...", citations=())


def test_parse_answer_survives_an_empty_response():
    assert parse_answer({}) == Answer(text="", citations=())
