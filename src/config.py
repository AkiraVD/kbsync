"""Settings, read once from the environment (or a local .env)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_LOCALE = "en-us"
DEFAULT_OUT_DIR = "articles"


@dataclass(frozen=True)
class Settings:
    zendesk_host: str
    locale: str
    out_dir: Path
    max_articles: int | None

    @classmethod
    def from_env(cls) -> "Settings":
        host = _required("ZENDESK_HOST")
        limit = os.environ.get("MAX_ARTICLES", "").strip()
        return cls(
            zendesk_host=_as_host(host),
            locale=os.environ.get("ZENDESK_LOCALE", "").strip() or DEFAULT_LOCALE,
            out_dir=Path(os.environ.get("OUT_DIR", "").strip() or DEFAULT_OUT_DIR),
            max_articles=int(limit) if limit else None,
        )


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is not set. Copy .env.sample to .env and fill it in.")
    return value


def _as_host(value: str) -> str:
    """Accept a bare host or a pasted URL; only the host is ever needed."""
    return value.removeprefix("https://").removeprefix("http://").strip("/")
