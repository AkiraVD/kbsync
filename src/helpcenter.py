"""Read-only client for a Zendesk Help Center's public API.

Articles come back as JSON with their body as an HTML string, so there is no page
scraping here: one GET per 100 articles, plus one pass over sections for their names.
"""

import logging
import time

import requests

log = logging.getLogger(__name__)

PER_PAGE = 100
MAX_RETRIES = 4


class HelpCenter:
    def __init__(self, host: str, locale: str = "en-us", timeout: int = 30):
        self.base = f"https://{host}/api/v2/help_center"
        self.locale = locale
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"

    def _get(self, url: str, params: dict | None = None) -> dict:
        """GET with a retry on rate limits and transient server errors."""
        for attempt in range(1, MAX_RETRIES + 1):
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == MAX_RETRIES:
                    response.raise_for_status()
                wait = int(response.headers.get("Retry-After", 2**attempt))
                log.warning("%s on %s, retrying in %ss", response.status_code, url, wait)
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        raise RuntimeError("unreachable")

    def _paginate(self, path: str, key: str):
        """Yield every record from a paginated collection endpoint."""
        url = f"{self.base}/{path}"
        params = {"per_page": PER_PAGE}

        while url:
            payload = self._get(url, params=params)
            yield from payload.get(key, [])
            url = payload.get("next_page")
            params = None  # next_page already carries the query string

    def articles(self, max_articles: int | None = None) -> list[dict]:
        """Published articles, newest edit first, drafts excluded."""
        collected = []

        for article in self._paginate(f"{self.locale}/articles.json", "articles"):
            if article.get("draft"):
                continue
            collected.append(article)
            if max_articles and len(collected) >= max_articles:
                break

        log.info("fetched %d articles from the Help Center API", len(collected))
        return collected

    def section_names(self) -> dict[int, str]:
        """section id -> name, so each file can record where it sits."""
        names = {
            section["id"]: section["name"]
            for section in self._paginate(f"{self.locale}/sections.json", "sections")
        }
        log.info("fetched %d section names", len(names))
        return names
