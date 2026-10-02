"""Settings, read once from the environment (or a local .env)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .vectorstore import DEFAULT_BASE_URL, DEFAULT_EMBEDDING_MODEL, Chunking

load_dotenv()

DEFAULT_LOCALE = "en-us"
DEFAULT_OUT_DIR = "articles"
DEFAULT_CHUNK_TOKENS = 512
DEFAULT_OVERLAP_TOKENS = 128
DEFAULT_MODEL = "gemini-flash-lite-latest"


@dataclass(frozen=True)
class Settings:
    zendesk_host: str
    locale: str
    out_dir: Path
    max_articles: int | None
    api_key: str
    store_name: str
    base_url: str
    model: str
    embedding_model: str
    chunking: Chunking

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            zendesk_host=_as_host(_required("ZENDESK_HOST")),
            locale=_text("ZENDESK_LOCALE", DEFAULT_LOCALE),
            out_dir=Path(_text("OUT_DIR", DEFAULT_OUT_DIR)),
            max_articles=_number("MAX_ARTICLES", None),
            api_key=_text("GEMINI_API_KEY", ""),
            store_name=_text("GEMINI_FILE_SEARCH_STORE", ""),
            base_url=_text("GEMINI_BASE_URL", DEFAULT_BASE_URL),
            model=_text("GEMINI_MODEL", DEFAULT_MODEL),
            embedding_model=_text("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
            chunking=Chunking(
                max_tokens=_number("CHUNK_SIZE_TOKENS", DEFAULT_CHUNK_TOKENS),
                overlap_tokens=_number("CHUNK_OVERLAP_TOKENS", DEFAULT_OVERLAP_TOKENS),
            ),
        )

    @property
    def uploads_enabled(self) -> bool:
        return bool(self.api_key and self.store_name)


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
