"""Upload documents to an OpenAI vector store over the REST API.

The brief rules out the dashboard, so every call here is explicit: create the
file, attach it to the store with our chunking strategy and attributes, then
drop the version it replaced.
"""

import logging
import math
from dataclasses import dataclass

from .http import Client
from .models import Document

log = logging.getLogger(__name__)

API_ROOT = "https://api.openai.com/v1"
FILE_PURPOSE = "assistants"
PER_PAGE = 100
CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class RemoteFile:
    file_id: str
    content_hash: str


@dataclass(frozen=True)
class Chunking:
    max_tokens: int
    overlap_tokens: int

    def as_param(self) -> dict:
        return {
            "type": "static",
            "static": {
                "max_chunk_size_tokens": self.max_tokens,
                "chunk_overlap_tokens": self.overlap_tokens,
            },
        }

    def estimate_chunks(self, text: str) -> int:
        tokens = len(text) / CHARS_PER_TOKEN
        stride = self.max_tokens - self.overlap_tokens
        return max(1, math.ceil((tokens - self.overlap_tokens) / stride))


class VectorStore:
    def __init__(self, api_key: str, vector_store_id: str, chunking: Chunking):
        self.id = vector_store_id
        self.chunking = chunking
        self.client = Client({"Authorization": f"Bearer {api_key}"}, timeout=120)

    def fetch_files(self) -> dict[str, RemoteFile]:
        """Article id -> the file the store already holds for it."""
        files: dict[str, RemoteFile] = {}

        for payload in self._paginate(f"{API_ROOT}/vector_stores/{self.id}/files"):
            attributes = payload.get("attributes") or {}
            article_id = attributes.get("article_id")
            if article_id is None:
                continue
            files[str(article_id)] = RemoteFile(
                file_id=payload["id"],
                content_hash=str(attributes.get("content_hash", "")),
            )

        log.info("vector store holds %d files with known article ids", len(files))
        return files

    def put(self, document: Document, replacing: RemoteFile | None = None) -> str:
        file_id = self._create_file(document)
        self._attach(file_id, document)
        if replacing:
            self._discard(replacing.file_id)
        return file_id

    def _create_file(self, document: Document) -> str:
        payload = self.client.post(
            f"{API_ROOT}/files",
            files={
                "file": (
                    document.filename,
                    document.text.encode("utf-8"),
                    "text/markdown",
                )
            },
            data={"purpose": FILE_PURPOSE},
        )
        return payload["id"]

    def _attach(self, file_id: str, document: Document) -> None:
        self.client.post(
            f"{API_ROOT}/vector_stores/{self.id}/files",
            json={
                "file_id": file_id,
                "chunking_strategy": self.chunking.as_param(),
                "attributes": _attributes(document),
            },
        )

    def _discard(self, file_id: str) -> None:
        self.client.delete(f"{API_ROOT}/vector_stores/{self.id}/files/{file_id}")
        self.client.delete(f"{API_ROOT}/files/{file_id}")

    def _paginate(self, url: str):
        params: dict = {"limit": PER_PAGE}

        while True:
            payload = self.client.get(url, params)
            data = payload.get("data", [])
            yield from data
            if not payload.get("has_more") or not data:
                return
            params = {"limit": PER_PAGE, "after": data[-1]["id"]}


def _attributes(document: Document) -> dict:
    article = document.article
    return {
        "article_id": str(article.id),
        "slug": document.slug,
        "title": article.title[:512],
        "url": article.url[:512],
        "updated_at": article.updated_at,
        "content_hash": document.content_hash,
    }
