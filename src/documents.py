"""Build the Markdown file for an article: slug, front matter, body, hash."""

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable

from .html_to_markdown import convert
from .models import Article, Document

SLUG_MAX_LENGTH = 80


def build_all(articles: Iterable[Article]) -> list[Document]:
    documents: list[Document] = []
    taken: set[str] = set()

    for article in articles:
        slug = slug_for(article)
        if slug in taken:
            slug = f"{slug}-{article.id}"
        taken.add(slug)
        documents.append(build(article, slug))

    return documents


def build(article: Article, slug: str | None = None) -> Document:
    body = convert(article.body_html)
    content_hash = hash_body(body)
    return Document(
        article=article,
        slug=slug or slug_for(article),
        text=_file_text(article, body, content_hash),
        content_hash=content_hash,
    )


def hash_body(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def slug_for(article: Article) -> str:
    tail = article.url.rstrip("/").rsplit("/", 1)[-1]
    return slugify(re.sub(r"^\d+-", "", tail) or article.title)


def slugify(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug[:SLUG_MAX_LENGTH].strip("-") or "article"


def _file_text(article: Article, body: str, content_hash: str) -> str:
    return (
        _front_matter(article, content_hash)
        + f"\n\n# {article.title.strip()}\n\n"
        # Repeated outside the front matter so a chunk that misses it can still cite.
        + f"Article URL: {article.url}\n\n"
        + body
    )


def _front_matter(article: Article, content_hash: str) -> str:
    fields = {
        "title": article.title,
        "article_id": article.id,
        "url": article.url,
        "section": article.section,
        "labels": list(article.labels),
        "updated_at": article.updated_at,
        "content_hash": content_hash,
    }
    # JSON is valid YAML, so quoting stays correct without a YAML dependency.
    lines = "\n".join(f"{key}: {json.dumps(value)}" for key, value in fields.items())
    return f"---\n{lines}\n---"
