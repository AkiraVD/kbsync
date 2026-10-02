"""The eval set, drawn from real conversations with the live bot.

These hit the API and need a populated store, so they skip unless a key is set:
    GEMINI_API_KEY=... python -m pytest -m eval -v
Assertions check the contract the prompt asks for, not the exact wording.
"""

import json
import os
import re
from pathlib import Path

import pytest

from src.assistant import Assistant
from src.config import Settings

ARTICLE_URL = re.compile(r"https?://\S+?/hc/\S*articles/[\w-]+")

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.environ.get("GEMINI_API_KEY"),
        reason="needs GEMINI_API_KEY and a populated store",
    ),
]


@pytest.fixture(scope="module")
def assistant() -> Assistant:
    settings = Settings.from_env()
    return Assistant(
        settings.api_key, settings.store_name, settings.model, base_url=settings.base_url
    )


@pytest.fixture(scope="module")
def known_urls() -> set[str]:
    manifest = Path("articles/manifest.json")
    if not manifest.exists():
        pytest.skip("run main.py first so the corpus is on disk")
    stored = json.loads(manifest.read_text(encoding="utf-8"))["articles"]
    return {entry["url"] for entry in stored.values()}


def test_youtube_question_answers_with_a_citation(assistant):
    answer = assistant.ask("How do I add a YouTube video?")

    assert answer.text
    assert answer.citations, "the brief's own sanity check expects sources"


def test_getting_started_cites_an_article(assistant):
    answer = assistant.ask("How do I get started?")

    assert answer.text
    assert answer.citations


def test_definition_follow_up_stays_short(assistant):
    answer = assistant.ask("What's HDMI plug and play?")

    assert answer.text
    assert answer.text.count("•") + answer.text.count("\n- ") <= 5


def test_pairing_code_problem_is_handled(assistant):
    answer = assistant.ask("I can't get the 6 digit pairing code")

    assert answer.text
    assert "?" in answer.text or "support" in answer.text.lower()


def test_unsupported_hardware_invents_no_article_url(assistant, known_urls):
    """The hallucination guard: SmartBridge is not a product."""
    answer = assistant.ask("I'm using my SmartBridge")

    cited = set(ARTICLE_URL.findall(answer.text)) | set(answer.citations)
    invented = {url for url in cited if url.rstrip(".,)") not in known_urls}

    assert not invented, f"invented article urls: {invented}"
    assert answer.text


def test_typo_still_gets_an_answer(assistant):
    answer = assistant.ask("what's HDMI olug n play")

    assert answer.text
