"""Write one Markdown file per article and remember what was written.

The manifest records each article's body hash, which is what lets a later run
tell new from updated from unchanged without re-uploading the whole corpus.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .convert import article_slug, render

log = logging.getLogger(__name__)

MANIFEST_NAME = "manifest.json"


@dataclass
class Result:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"added={len(self.added)} updated={len(self.updated)} "
            f"skipped={len(self.skipped)}"
        )


def load_manifest(out_dir: Path) -> dict:
    path = out_dir / MANIFEST_NAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("articles", {})
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("ignoring unreadable manifest (%s)", exc)
        return {}


def save_manifest(out_dir: Path, articles: dict) -> None:
    path = out_dir / MANIFEST_NAME
    payload = {"count": len(articles), "articles": articles}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _unique_slug(article: dict, taken: set[str]) -> str:
    """Two articles can share a title; keep the id out of the name until then."""
    slug = article_slug(article)
    if slug not in taken:
        return slug
    return f"{slug}-{article['id']}"


def write_articles(
    articles: list[dict], section_names: dict[int, str], out_dir: Path
) -> Result:
    out_dir.mkdir(parents=True, exist_ok=True)
    previous = load_manifest(out_dir)
    result = Result()
    taken: set[str] = set()

    for article in articles:
        article_id = str(article["id"])
        slug = _unique_slug(article, taken)
        taken.add(slug)

        contents, digest = render(article, section_names.get(article.get("section_id")))
        path = out_dir / f"{slug}.md"

        was = previous.get(article_id)
        if was is None:
            result.added.append(slug)
        elif was.get("content_hash") != digest:
            result.updated.append(slug)
        else:
            result.skipped.append(slug)

        # Unchanged articles are still written, so a fresh checkout has the full
        # corpus; the hash decides what gets re-uploaded, not what gets saved.
        path.write_text(contents, encoding="utf-8")

        result.manifest[article_id] = {
            "slug": slug,
            "title": article.get("title", ""),
            "url": article.get("html_url", ""),
            "updated_at": article.get("updated_at", ""),
            "content_hash": digest,
        }

    save_manifest(out_dir, result.manifest)

    stale = sorted(
        path.name
        for path in out_dir.glob("*.md")
        if path.stem not in taken
    )
    if stale:
        log.info("%d file(s) no longer in the Help Center: %s", len(stale), ", ".join(stale))

    return result
