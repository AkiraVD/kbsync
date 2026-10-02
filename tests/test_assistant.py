"""The prompt is a graded requirement, so it is pinned, not trusted."""

from src.assistant import SYSTEM_PROMPT, Answer, Citation, parse_answer

VERBATIM = (
    "You are OptiBot, the customer-support bot for OptiSigns.com.\n"
    "\u2022 Tone: helpful, factual, concise.\n"
    "\u2022 Only answer using the uploaded docs.\n"
    "\u2022 Max 5 bullet points; else link to the doc.\n"
    '\u2022 Cite up to 3 "Article URL:" lines per reply.'
)

URL = "https://support.example.test/hc/en-us/articles/42-Add-A-Video"
CHUNK_WITH_URL = (
    '---\ntitle: "How to Use the Weather Radar App"\n'
    f'url: "{URL}"\n---\n\n# How to Use the Weather Radar App\n\n'
    f"Article URL: {URL}\n\nBody."
)
CHUNK_WITHOUT_URL = "- **Zoom** - how much of the area is shown."


def _payload(*annotations, text="Open the app."):
    return {
        "steps": [
            {"type": "file_search_call", "signature": "x"},
            {
                "type": "model_output",
                "content": [
                    {"type": "text", "text": text, "annotations": list(annotations)}
                ],
            },
        ]
    }


def test_system_prompt_is_the_briefs_prompt_byte_for_byte():
    assert SYSTEM_PROMPT == VERBATIM


def test_prompt_keeps_the_bullets_and_the_citation_wording():
    assert SYSTEM_PROMPT.count("\u2022") == 4
    assert '"Article URL:"' in SYSTEM_PROMPT
    assert "Max 5 bullet points" in SYSTEM_PROMPT


def test_citation_url_is_read_out_of_the_retrieved_chunk():
    """`source` is the chunk text, not a link, so the URL comes from the body."""
    payload = _payload(
        {"file_name": "add-a-video.md", "source": CHUNK_WITH_URL, "type": "file_citation"}
    )

    assert parse_answer(payload) == Answer(
        text="Open the app.",
        citations=(Citation(file_name="add-a-video.md", url=URL),),
    )


def test_chunks_from_one_file_collapse_to_the_one_carrying_the_url():
    payload = _payload(
        {"file_name": "add-a-video.md", "source": CHUNK_WITHOUT_URL},
        {"file_name": "add-a-video.md", "source": CHUNK_WITH_URL},
    )

    citations = parse_answer(payload).citations

    assert citations == (Citation(file_name="add-a-video.md", url=URL),)


def test_a_file_with_no_url_in_any_chunk_is_still_reported():
    payload = _payload({"file_name": "add-a-video.md", "source": CHUNK_WITHOUT_URL})

    assert parse_answer(payload).citations == (
        Citation(file_name="add-a-video.md", url=""),
    )


def test_parse_answer_survives_an_answer_with_no_citations():
    payload = {"steps": [{"content": [{"text": "Plug and play means..."}]}]}

    assert parse_answer(payload) == Answer(text="Plug and play means...", citations=())


def test_parse_answer_survives_an_empty_response():
    assert parse_answer({}) == Answer(text="", citations=())
