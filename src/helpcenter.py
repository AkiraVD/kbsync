"""Read-only client for a Zendesk Help Center's public API.

Articles come back as JSON with their body as an HTML string, so there is no page
scraping here: one request per 100 records, and raw payloads out.
"""

import logging
import time

import requests

log = logging.getLogger(__name__)

PER_PAGE = 100
MAX_ATTEMPTS = 4
RETRY_STATUSES = (429, 500, 502, 503, 504)


class HelpCenter:
    def __init__(self, host: str, locale: str = "en-us", timeout: int = 30):
        self.base = f"https://{host}/api/v2/help_center"
        self.locale = locale
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"

    def fetch_articles(self, limit: int | None = None) -> list[dict]:
        articles = []
        for payload in self._paginate(f"{self.locale}/articles.json", "articles"):
            if payload.get("draft"):
                continue
            articles.append(payload)
            if limit and len(articles) >= limit:
                break

        log.info("fetched %d articles from the Help Center API", len(articles))
        return articles

    def fetch_sections(self) -> dict[int, str]:
        sections = {
            payload["id"]: payload["name"]
            for payload in self._paginate(f"{self.locale}/sections.json", "sections")
        }
        log.info("fetched %d section names", len(sections))
        return sections

    def _paginate(self, path: str, key: str):
        url = f"{self.base}/{path}"
        params: dict | None = {"per_page": PER_PAGE}

        while url:
            payload = self._get(url, params)
            yield from payload.get(key, [])
            url = payload.get("next_page")
            params = None

    def _get(self, url: str, params: dict | None = None) -> dict:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                wait = int(response.headers.get("Retry-After", 2**attempt))
                log.warning("%s on %s, retrying in %ss", response.status_code, url, wait)
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        raise RuntimeError("unreachable")
