"""One bad upload must not cost the run."""

from pathlib import Path

import pytest

from src.config import Settings
from src.models import Status
from src.sync import sync
from src.vectorstore import Chunking, UploadError

PAYLOADS = [
    {
        "id": n,
        "title": f"Article {n}",
        "html_url": f"https://support.example.test/hc/en-us/articles/{n}-Article-{n}",
        "body": f"<p>Body {n}</p>",
        "section_id": 1,
        "updated_at": "2026-09-01T00:00:00Z",
    }
    for n in (1, 2, 3)
]


class FakeHelpCenter:
    def __init__(self, host, locale="en-us"):
        pass

    def fetch_sections(self):
        return {1: "Setup"}

    def fetch_articles(self, limit=None):
        return PAYLOADS[:limit] if limit else PAYLOADS


class FakeVectorStore:
    def __init__(self, *args, failing=(), **kwargs):
        self.chunking = Chunking(512, 128)
        self.failing = set(failing)
        self.uploaded: list[str] = []

    def fetch_files(self):
        return {}

    def put(self, document, replacing=None):
        if document.article.id in self.failing:
            raise UploadError(f"{document.filename}: boom")
        self.uploaded.append(document.slug)
        return "operations/ok"


@pytest.fixture
def settings(tmp_path):
    return Settings(
        zendesk_host="support.example.test",
        locale="en-us",
        out_dir=tmp_path,
        max_articles=None,
        api_key="key",
        store_name="fileSearchStores/x",
        base_url="https://api.test/v1beta",
        model="model",
        embedding_model="embedding",
        chunking=Chunking(512, 128),
    )


@pytest.fixture
def wire(monkeypatch):
    def _wire(failing=()):
        store = FakeVectorStore(failing=failing)
        monkeypatch.setattr("src.sync.HelpCenter", FakeHelpCenter)
        monkeypatch.setattr("src.sync.VectorStore", lambda *a, **k: store)
        return store

    return _wire


def test_every_article_uploads_when_nothing_fails(settings, wire):
    store = wire()

    report = sync(settings)

    assert report.count(Status.ADDED) == 3
    assert report.failed == []
    assert len(store.uploaded) == 3


def test_a_failed_upload_is_reported_and_the_rest_continue(settings, wire):
    store = wire(failing={2})

    report = sync(settings)

    assert store.uploaded == ["article-1", "article-3"]
    assert report.failed == ["article-2"]
    assert report.count(Status.ADDED) == 2
    assert report.written == 3, "the Markdown is written even when the upload fails"


def test_a_failed_article_is_retried_next_run(settings, wire):
    wire(failing={2})
    sync(settings)

    store = wire()
    report = sync(settings)

    assert "article-2" in store.uploaded
    assert report.failed == []


def test_markdown_is_written_for_every_article(settings, wire):
    wire()

    sync(settings)

    assert sorted(p.name for p in Path(settings.out_dir).glob("*.md")) == [
        "article-1.md",
        "article-2.md",
        "article-3.md",
    ]


def test_summary_mentions_failures_only_when_there_are_some(settings, wire):
    wire()
    assert "failed" not in sync(settings).summary()

    wire(failing={1})
    assert "failed=1" in sync(settings).summary()
