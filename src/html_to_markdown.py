"""Article HTML to Markdown, dropping editor noise on the way through.

Each cleaning rule is a small function over the parsed tree; RULES lists them in
the order they run, which is the place to add another.
"""

import re

from bs4 import BeautifulSoup
from markdownify import markdownify

KEEP_ATTRS = {"href", "src", "alt", "colspan", "rowspan"}
NOISE_TAGS = ("script", "style", "nav", "noscript")
STYLING_TAGS = ("span", "font")


def convert(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for rule in RULES:
        rule(soup)
    return _tidy(
        markdownify(
            str(soup),
            heading_style="ATX",
            bullets="-",
            escape_asterisks=False,
            escape_underscores=False,
        )
    )


def _drop_noise_tags(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()


def _unwrap_styling(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(STYLING_TAGS):
        tag.unwrap()


def _drop_anchor_targets(soup: BeautifulSoup) -> None:
    for anchor in soup.find_all("a"):
        if not anchor.get("href") and not anchor.get_text(strip=True):
            anchor.decompose()

    for para in soup.find_all("p"):
        if not para.get_text(strip=True) and not para.find(["img", "br"]):
            para.decompose()


def _drop_inpage_contents(soup: BeautifulSoup) -> None:
    for listing in soup.find_all(["ul", "ol"]):
        items = listing.find_all("li", recursive=False)
        links = [item.find("a") for item in items]
        if items and all(
            link is not None and (link.get("href") or "").startswith("#")
            for link in links
        ):
            listing.decompose()


def _quote_callouts(soup: BeautifulSoup) -> None:
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows or any(len(row.find_all(["td", "th"])) != 1 for row in rows):
            continue

        lines = [row.get_text(" ", strip=True) for row in rows]
        quote = soup.new_tag("blockquote")
        quote.string = " — ".join(line for line in lines if line)
        (table.find_parent("figure") or table).replace_with(quote)


def _link_embeds(soup: BeautifulSoup) -> None:
    for frame in soup.find_all("iframe"):
        src = frame.get("src", "")
        if not src:
            frame.decompose()
            continue
        link = soup.new_tag("a", href=src)
        link.string = frame.get("title") or "Embedded video"
        frame.replace_with(link)


def _drop_data_uris(soup: BeautifulSoup) -> None:
    """An inline base64 image is a binary blob, not content.

    One article carried a 125KB PNG this way, which made the file seven times
    larger than any other and timed out every upload attempt.
    """
    for tag in soup.find_all(["img", "a"]):
        target = tag.get("src") or tag.get("href") or ""
        if not target.startswith("data:"):
            continue

        label = tag.get("alt") or tag.get_text(strip=True)
        tag.replace_with(label) if label else tag.decompose()


def _demote_body_headings(soup: BeautifulSoup) -> None:
    for tag in soup.find_all("h1"):
        tag.name = "h2"


def _strip_attributes(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(True):
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in KEEP_ATTRS}


RULES = (
    _drop_noise_tags,
    _unwrap_styling,
    _drop_anchor_targets,
    _drop_inpage_contents,
    _quote_callouts,
    _link_embeds,
    _drop_data_uris,
    _demote_body_headings,
    _strip_attributes,
)


def _tidy(text: str) -> str:
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
