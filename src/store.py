"""Where documents land on disk."""

from pathlib import Path

from .models import Document


class ArticleStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def prepare(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    def write(self, document: Document) -> None:
        path = self.directory / document.filename
        path.write_text(document.text, encoding="utf-8")

    def stale_files(self, keep: set[str]) -> list[str]:
        return sorted(
            path.name for path in self.directory.glob("*.md") if path.stem not in keep
        )
