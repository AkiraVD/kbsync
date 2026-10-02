"""Upload documents to a Gemini File Search store over the REST API.

The brief rules out dashboard uploads, so every step is explicit: start a
resumable upload, finalise it, wait for the import operation, then drop the
document version it replaced. The API key travels as a header, never in a URL,
so nothing secret reaches the logs.
"""

import logging
import math
import time
from dataclasses import dataclass

import requests

from .http import Client
from .models import Document

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-2"
CHARS_PER_TOKEN = 4
PAGE_SIZE = 20
MAX_CHUNK_TOKENS = 512
REQUEST_TIMEOUT = 60
IMPORT_POLL_SECONDS = 3
IMPORT_TIMEOUT_SECONDS = 300


class UploadError(Exception):
    """One document could not be stored; the run should carry on without it."""


@dataclass(frozen=True)
class RemoteFile:
    remote_id: str
    content_hash: str


@dataclass(frozen=True)
class Chunking:
    max_tokens: int
    overlap_tokens: int

    def __post_init__(self) -> None:
        if not 1 <= self.max_tokens <= MAX_CHUNK_TOKENS:
            raise ValueError(
                f"CHUNK_SIZE_TOKENS must be 1-{MAX_CHUNK_TOKENS}, got {self.max_tokens}"
            )
        if self.overlap_tokens > self.max_tokens // 2:
            raise ValueError(
                "CHUNK_OVERLAP_TOKENS must not exceed half of CHUNK_SIZE_TOKENS"
            )

    def as_param(self) -> dict:
        return {
            "whiteSpaceConfig": {
                "maxTokensPerChunk": self.max_tokens,
                "maxOverlapTokens": self.overlap_tokens,
            }
        }

    def estimate_chunks(self, text: str) -> int:
        tokens = len(text) / CHARS_PER_TOKEN
        stride = self.max_tokens - self.overlap_tokens
        return max(1, math.ceil((tokens - self.overlap_tokens) / stride))


def create_store(
    api_key: str,
    display_name: str,
    base_url: str = DEFAULT_BASE_URL,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> str:
    """Create a store and return the resource name to put in .env."""
    client = Client({"x-goog-api-key": api_key})
    payload = client.post(
        f"{base_url.rstrip('/')}/fileSearchStores",
        json={"displayName": display_name, "embeddingModel": embedding_model},
    )
    return payload["name"]


class VectorStore:
    def __init__(
        self,
        api_key: str,
        store_name: str,
        chunking: Chunking,
        base_url: str = DEFAULT_BASE_URL,
    ):
        self.store = store_name
        self.chunking = chunking
        self.base_url = base_url.rstrip("/")
        self.client = Client({"x-goog-api-key": api_key}, timeout=REQUEST_TIMEOUT)

    def fetch_files(self) -> dict[str, RemoteFile]:
        """Article id -> the document the store already holds for it."""
        files: dict[str, RemoteFile] = {}

        for payload in self._paginate(f"{self.base_url}/{self.store}/documents"):
            metadata = _read_metadata(payload.get("customMetadata") or [])
            article_id = metadata.get("article_id")
            if article_id is None:
                continue
            files[str(article_id)] = RemoteFile(
                remote_id=payload["name"],
                content_hash=str(metadata.get("content_hash", "")),
            )

        log.info("store holds %d documents with known article ids", len(files))
        return files

    def put(self, document: Document, replacing: RemoteFile | None = None) -> str:
        try:
            operation = self._upload(document)
            name = self._await_import(operation)
        except (requests.RequestException, TimeoutError, RuntimeError) as exc:
            raise UploadError(f"{document.filename}: {exc}") from exc

        if replacing:
            self._discard(replacing.remote_id)
        return name

    def _upload(self, document: Document) -> dict:
        body = document.text.encode("utf-8")
        upload_url = self._start_upload(document, len(body))

        return self.client.post(
            upload_url,
            data=body,
            headers={
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": "upload, finalize",
            },
        )

    def _start_upload(self, document: Document, size: int) -> str:
        response = self.client.post_raw(
            self._upload_endpoint(),
            json={
                "displayName": document.filename,
                "customMetadata": _metadata(document),
                "chunkingConfig": self.chunking.as_param(),
            },
            headers={
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(size),
                "X-Goog-Upload-Header-Content-Type": "text/markdown",
            },
        )

        url = response.headers.get("x-goog-upload-url")
        if not url:
            raise RuntimeError(f"no upload url returned for {document.filename}")
        return url

    def _await_import(self, operation: dict) -> str:
        name = operation.get("name", "")
        if operation.get("done") or not name:
            return name

        deadline = time.monotonic() + IMPORT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            time.sleep(IMPORT_POLL_SECONDS)
            status = self.client.get(f"{self.base_url}/{name}")
            if status.get("done"):
                if "error" in status:
                    raise RuntimeError(f"import failed: {status['error']}")
                return name

        raise TimeoutError(f"import did not finish within {IMPORT_TIMEOUT_SECONDS}s")

    def _discard(self, document_name: str) -> None:
        self.client.delete(f"{self.base_url}/{document_name}?force=true")

    def _upload_endpoint(self) -> str:
        root, _, version = self.base_url.rpartition("/")
        return f"{root}/upload/{version}/{self.store}:uploadToFileSearchStore"

    def _paginate(self, url: str):
        params: dict = {"pageSize": PAGE_SIZE}

        while True:
            payload = self.client.get(url, params)
            yield from payload.get("documents", [])
            token = payload.get("nextPageToken")
            if not token:
                return
            params = {"pageSize": PAGE_SIZE, "pageToken": token}


def _metadata(document: Document) -> list[dict]:
    article = document.article
    pairs = {
        "article_id": str(article.id),
        "slug": document.slug,
        "title": article.title[:256],
        "url": article.url[:256],
        "updated_at": article.updated_at,
        "content_hash": document.content_hash,
    }
    return [{"key": key, "stringValue": value} for key, value in pairs.items()]


def _read_metadata(entries: list[dict]) -> dict[str, str]:
    return {
        entry["key"]: entry.get("stringValue", entry.get("numericValue", ""))
        for entry in entries
        if "key" in entry
    }
