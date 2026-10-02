"""Turn an article's HTML body into clean Markdown.

The API hands us editor-generated HTML: colour spans, empty anchor targets, an
in-page table of contents, and callouts built as one-column tables. Headings,
lists, code, links and images are kept; the rest is tidied away before the
Markdown conversion so the output reads like something a person wrote.
"""

import hashlib
import json
import re
import unicodedata

from bs4 import BeautifulSoup
from markdownify import markdownify

# Attributes worth keeping; everything else is styling or editor bookkeeping.
KEEP_ATTRS = {"href", "src", "alt", "colspan", "rowspan"}

DROP_TAGS = ["script", "style", "nav", "noscript"]


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()

    # Colour/font wrappers carry no meaning once the styling is gone.
    for tag in soup.find_all(["span", "font"]):
        tag.unwrap()

    _drop_anchor_targets(soup)
    _drop_inpage_toc(soup)
    _callout_tables_to_quotes(soup)
    _embeds_to_links(soup)

    # One H1 per file, and that one is the title we write ourselves.
    for tag in soup.find_all("h1"):
        tag.name = "h2"

    for tag in soup.find_all(True):
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in KEEP_ATTRS}

    return str(soup)


def _drop_anchor_targets(soup) -> None:
    """Remove <a name="x"></a> jump targets, and any paragraph left empty."""
    for anchor in soup.find_all("a"):
        if not anchor.get("href") and not anchor.get_text(strip=True):
            anchor.decompose()

    for para in soup.find_all("p"):
        if not para.get_text(strip=True) and not para.find(["img", "br"]):
            para.decompose()


def _drop_inpage_toc(soup) -> None:
    """Remove lists that are purely links to anchors on the same page."""
    for listing in soup.find_all(["ul", "ol"]):
        items = listing.find_all("li", recursive=False)
        if not items:
            continue
        links = [item.find("a") for item in items]
        if all(
            link is not None and (link.get("href") or "").startswith("#")
            for link in links
        ):
            listing.decompose()


def _callout_tables_to_quotes(soup) -> None:
    """A one-column table is a TIP/NOTE box, not tabular data — quote it."""
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows or any(len(row.find_all(["td", "th"])) != 1 for row in rows):
            continue

        lines = [row.get_text(" ", strip=True) for row in rows]
        quote = soup.new_tag("blockquote")
        quote.string = " — ".join(line for line in lines if line)

        target = table.find_parent("figure") or table
        target.replace_with(quote)


def _embeds_to_links(soup) -> None:
    """Keep embedded videos as a plain link rather than losing them."""
    for frame in soup.find_all("iframe"):
        src = frame.get("src", "")
        if not src:
            frame.decompose()
            continue
        link = soup.new_tag("a", href=src)
        link.string = frame.get("title") or "Embedded video"
        frame.replace_with(link)


def to_markdown(html: str) -> str:
    text = markdownify(
        clean_html(html),
        heading_style="ATX",
        bullets="-",
        escape_asterisks=False,
        escape_underscores=False,
    )

    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def slugify(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug[:80].strip("-") or "article"


def article_slug(article: dict) -> str:
    """Prefer the slug the Help Center already uses in its own URLs."""
    tail = (article.get("html_url") or "").rstrip("/").rsplit("/", 1)[-1]
    tail = re.sub(r"^\d+-", "", tail)
    return slugify(tail or article.get("title", ""))


def content_hash(markdown_body: str) -> str:
    return hashlib.sha256(markdown_body.encode("utf-8")).hexdigest()


def render(article: dict, section_name: str | None = None) -> tuple[str, str]:
    """Return (file contents, body hash) for one article.

    The article URL is repeated as a body line, not only in the front matter, so
    that whichever chunk a search lands on still carries the citation.
    """
    body = to_markdown(article.get("body", ""))
    digest = content_hash(body)

    front = {
        "title": article.get("title", ""),
        "article_id": article.get("id"),
        "url": article.get("html_url", ""),
        "section": section_name or "",
        "labels": article.get("label_names") or [],
        "updated_at": article.get("updated_at", ""),
        "content_hash": digest,
    }
    # JSON is valid YAML, which keeps quoting correct without a YAML dependency.
    lines = [f"{key}: {json.dumps(value)}" for key, value in front.items()]

    contents = (
        "---\n"
        + "\n".join(lines)
        + "\n---\n\n"
        + f"# {article.get('title', '').strip()}\n\n"
        + f"Article URL: {article.get('html_url', '')}\n\n"
        + body
    )
    return contents, digest
