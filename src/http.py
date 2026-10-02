"""HTTP with a retry on rate limits and transient server errors."""

import logging
import time

import requests

log = logging.getLogger(__name__)

RETRY_STATUSES = (429, 500, 502, 503, 504)
RETRY_ERRORS = (requests.Timeout, requests.ConnectionError)
MAX_ATTEMPTS = 4
MAX_RETRY_WAIT = 60


class Client:
    def __init__(self, headers: dict[str, str] | None = None, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"
        self.session.headers.update(headers or {})

    def get(self, url: str, params: dict | None = None) -> dict:
        return self._json("GET", url, params=params)

    def post(self, url: str, **kwargs) -> dict:
        return self._json("POST", url, **kwargs)

    def post_raw(self, url: str, **kwargs) -> requests.Response:
        """For calls whose answer is in the response headers."""
        return self._request("POST", url, **kwargs)

    def delete(self, url: str) -> dict:
        return self._json("DELETE", url)

    def _json(self, method: str, url: str, **kwargs) -> dict:
        response = self._request(method, url, **kwargs)
        return response.json() if response.content else {}

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
            except RETRY_ERRORS as exc:
                # A read timeout is as transient as a 503 and has to be retried;
                # without this one slow upload ends the whole run.
                if attempt == MAX_ATTEMPTS:
                    raise
                wait = 2**attempt
                log.warning("%s on %s, retrying in %ss", type(exc).__name__, url, wait)
                time.sleep(wait)
                continue

            if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                wait = int(response.headers.get("Retry-After", 2**attempt))
                # A daily quota answers Retry-After in hours. Waiting that out is
                # indistinguishable from a hang, so report it and stop.
                if wait > MAX_RETRY_WAIT:
                    log.error("%s on %s asks for a %ss wait", response.status_code, url, wait)
                    break
                log.warning("%s on %s, retrying in %ss", response.status_code, url, wait)
                time.sleep(wait)
                continue

            break

        if not response.ok:
            raise requests.HTTPError(
                f"{response.status_code} from {url}: {response.text[:300]}",
                response=response,
            )
        return response
