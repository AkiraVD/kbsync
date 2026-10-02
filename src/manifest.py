"""What the previous run produced, so this run can act on the delta alone."""

import json
import logging
from pathlib import Path

from .models import Document, Status

log = logging.getLogger(__name__)

FILENAME = "manifest.json"


class Manifest:
    def __init__(self, previous: dict[str, dict] | None = None):
        self.previous = previous or {}
        self.current: dict[str, dict] = {}

    @classmethod
    def load(cls, directory: Path) -> "Manifest":
        path = directory / FILENAME
        if not path.exists():
            return cls()
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("ignoring unreadable manifest (%s)", exc)
            return cls()
        return cls(stored.get("articles", {}))

    def status(self, document: Document) -> Status:
        previous = self.previous.get(str(document.article.id))
        if previous is None:
            return Status.ADDED
        if previous.get("content_hash") != document.content_hash:
            return Status.UPDATED
        return Status.SKIPPED

    def record(self, document: Document) -> None:
        self.current[str(document.article.id)] = {
            "slug": document.slug,
            "title": document.article.title,
            "url": document.article.url,
            "updated_at": document.article.updated_at,
            "content_hash": document.content_hash,
        }

    def save(self, directory: Path, prune: bool = True) -> None:
        """A partial run merges; only a full run may drop what it did not see."""
        articles = self.current if prune else {**self.previous, **self.current}
        payload = {"count": len(articles), "articles": articles}
        (directory / FILENAME).write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
