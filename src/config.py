"""Settings, read once from the environment (or a local .env)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .vectorstore import Chunking

load_dotenv()

DEFAULT_LOCALE = "en-us"
DEFAULT_OUT_DIR = "articles"
DEFAULT_CHUNK_TOKENS = 800
DEFAULT_OVERLAP_TOKENS = 200


@dataclass(frozen=True)
class Settings:
    zendesk_host: str
    locale: str
    out_dir: Path
    max_articles: int | None
    openai_api_key: str
    vector_store_id: str
    chunking: Chunking

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            zendesk_host=_as_host(_required("ZENDESK_HOST")),
            locale=_text("ZENDESK_LOCALE", DEFAULT_LOCALE),
            out_dir=Path(_text("OUT_DIR", DEFAULT_OUT_DIR)),
            max_articles=_number("MAX_ARTICLES", None),
            openai_api_key=_text("OPENAI_API_KEY", ""),
            vector_store_id=_text("OPENAI_VECTOR_STORE_ID", ""),
            chunking=Chunking(
                max_tokens=_number("CHUNK_SIZE_TOKENS", DEFAULT_CHUNK_TOKENS),
                overlap_tokens=_number("CHUNK_OVERLAP_TOKENS", DEFAULT_OVERLAP_TOKENS),
            ),
        )

    @property
    def uploads_enabled(self) -> bool:
        return bool(self.openai_api_key and self.vector_store_id)


def _text(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


def _number(name: str, default):
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


def _required(name: str) -> str:
    value = _text(name, "")
    if not value:
        raise SystemExit(f"{name} is not set. Copy .env.sample to .env and fill it in.")
    return value


def _as_host(value: str) -> str:
    """Accept a bare host or a pasted URL; only the host is ever needed."""
    return value.removeprefix("https://").removeprefix("http://").strip("/")
