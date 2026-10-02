import pytest

from src.models import Article


@pytest.fixture
def make_article():
    def _make(**overrides) -> Article:
        fields = {
            "id": 42,
            "title": "How do I add a video?",
            "url": "https://support.example.test/hc/en-us/articles/42-Add-A-Video",
            "body_html": "<p>Pick <strong>Add</strong>.</p>",
            "section": "Assets",
            "labels": ("video",),
            "updated_at": "2026-09-01T00:00:00Z",
        }
        return Article(**{**fields, **overrides})

    return _make
