"""Settings, read once from the environment (or a local .env)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    zendesk_host: str
    locale: str
    out_dir: Path
    max_articles: int | None


def load_config() -> Config:
    host = os.environ.get("ZENDESK_HOST", "").strip()
    if not host:
        raise SystemExit(
            "ZENDESK_HOST is not set. Copy .env.sample to .env and fill it in."
        )

    # Accept a bare host or a pasted URL; we only ever need the host.
    host = host.removeprefix("https://").removeprefix("http://").strip("/")

    raw_max = os.environ.get("MAX_ARTICLES", "").strip()

    return Config(
        zendesk_host=host,
        locale=os.environ.get("ZENDESK_LOCALE", "en-us").strip() or "en-us",
        out_dir=Path(os.environ.get("OUT_DIR", "articles")),
        max_articles=int(raw_max) if raw_max else None,
    )
