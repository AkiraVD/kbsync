"""Types the pipeline stages pass between each other."""

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    ADDED = "added"
    UPDATED = "updated"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Article:
    id: int
    title: str
    url: str
    body_html: str
    section: str
    labels: tuple[str, ...]
    updated_at: str

    @classmethod
    def from_api(cls, payload: dict, sections: dict[int, str]) -> "Article":
        return cls(
            id=payload["id"],
            title=payload.get("title") or "",
            url=payload.get("html_url") or "",
            body_html=payload.get("body") or "",
            section=sections.get(payload.get("section_id"), ""),
            labels=tuple(payload.get("label_names") or ()),
            updated_at=payload.get("updated_at") or "",
        )


@dataclass(frozen=True)
class Document:
    article: Article
    slug: str
    text: str
    content_hash: str

    @property
    def filename(self) -> str:
        return f"{self.slug}.md"


@dataclass
class SyncReport:
    by_status: dict[Status, list[str]] = field(
        default_factory=lambda: {status: [] for status in Status}
    )
    stale: list[str] = field(default_factory=list)

    def record(self, status: Status, slug: str) -> None:
        self.by_status[status].append(slug)

    def count(self, status: Status) -> int:
        return len(self.by_status[status])

    @property
    def total(self) -> int:
        return sum(len(slugs) for slugs in self.by_status.values())

    def summary(self) -> str:
        return " ".join(f"{s.value}={self.count(s)}" for s in Status)
