"""Upload behaviour, with the HTTP layer stubbed out."""

import pytest

from src.documents import build
from src.models import Status
from src.state import VectorStoreState
from src.vectorstore import (
    Chunking,
    RemoteFile,
    UploadError,
    VectorStore,
    _metadata,
    _read_metadata,
)

STORE = "fileSearchStores/kb-1"


class FakeResponse:
    def __init__(self, headers: dict):
        self.headers = headers


class FakeClient:
    def __init__(self, pages: list[dict] | None = None, operations: list[dict] | None = None):
        self.pages = list(pages or [])
        self.operations = list(operations or [])
        self.calls: list[tuple] = []

    def get(self, url, params=None):
        self.calls.append(("GET", url, params))
        if self.operations:
            return self.operations.pop(0)
        return self.pages.pop(0) if self.pages else {"documents": []}

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return {"name": "operations/import-1", "done": True}

    def post_raw(self, url, **kwargs):
        self.calls.append(("POST_RAW", url, kwargs))
        return FakeResponse({"x-goog-upload-url": "https://upload.test/session"})

    def delete(self, url):
        self.calls.append(("DELETE", url, None))
        return {}


@pytest.fixture
def store():
    vector_store = VectorStore("key", STORE, Chunking(512, 128))
    vector_store.client = FakeClient()
    return vector_store


def test_chunking_sends_a_whitespace_config():
    assert Chunking(512, 128).as_param() == {
        "whiteSpaceConfig": {"maxTokensPerChunk": 512, "maxOverlapTokens": 128}
    }


def test_chunk_size_above_the_service_cap_is_refused():
    """File Search rejects anything over 512, so fail before the API does."""
    with pytest.raises(ValueError, match="must be 1-512"):
        Chunking(800, 200)


def test_overlap_beyond_half_the_chunk_is_refused():
    with pytest.raises(ValueError, match="half"):
        Chunking(512, 300)


@pytest.mark.parametrize(
    "characters, expected", [(100, 1), (512 * 4, 1), (1400 * 4, 4), (3000 * 4, 8)]
)
def test_chunk_estimate_grows_with_the_document(characters, expected):
    assert Chunking(512, 128).estimate_chunks("x" * characters) == expected


def test_metadata_carries_the_hash_the_next_run_compares(make_article):
    document = build(make_article())
    pairs = _read_metadata(_metadata(document))

    assert pairs["article_id"] == "42"
    assert pairs["content_hash"] == document.content_hash
    assert pairs["slug"] == "add-a-video"
    assert all(len(value) <= 256 for key, value in pairs.items() if key != "content_hash")


def test_metadata_round_trips_through_the_api_shape(make_article):
    entries = _metadata(build(make_article()))

    assert all(set(entry) == {"key", "stringValue"} for entry in entries)
    assert _read_metadata(entries)["url"].endswith("42-Add-A-Video")


def test_upload_endpoint_targets_the_resumable_route(store):
    assert store._upload_endpoint() == (
        "https://generativelanguage.googleapis.com/upload/v1beta"
        f"/{STORE}:uploadToFileSearchStore"
    )


def test_put_starts_then_finalises_the_upload(store, make_article):
    store.put(build(make_article()))

    assert [method for method, _, _ in store.client.calls] == ["POST_RAW", "POST"]
    start, finalise = store.client.calls
    assert start[2]["headers"]["X-Goog-Upload-Command"] == "start"
    assert finalise[1] == "https://upload.test/session"
    assert finalise[2]["headers"]["X-Goog-Upload-Command"] == "upload, finalize"


def test_start_sends_chunking_and_metadata(store, make_article):
    store.put(build(make_article()))

    body = store.client.calls[0][2]["json"]
    assert body["displayName"] == "add-a-video.md"
    assert body["chunkingConfig"]["whiteSpaceConfig"]["maxTokensPerChunk"] == 512
    assert {"key": "article_id", "stringValue": "42"} in body["customMetadata"]


def test_put_discards_the_document_it_replaces(store, make_article):
    previous = RemoteFile(f"{STORE}/documents/old", "stale")
    store.put(build(make_article()), replacing=previous)

    deletes = [url for method, url, _ in store.client.calls if method == "DELETE"]
    assert deletes == [
        f"https://generativelanguage.googleapis.com/v1beta/{STORE}/documents/old?force=true"
    ]


def test_import_is_polled_until_done(monkeypatch, make_article):
    monkeypatch.setattr("src.vectorstore.time.sleep", lambda _: None)
    store = VectorStore("key", STORE, Chunking(512, 128))
    store.client = FakeClient(operations=[{"done": False}, {"done": True}])
    store.client.post = lambda url, **kwargs: {"name": "operations/i1", "done": False}

    assert store.put(build(make_article())) == "operations/i1"


def test_failed_import_raises(monkeypatch, make_article):
    monkeypatch.setattr("src.vectorstore.time.sleep", lambda _: None)
    store = VectorStore("key", STORE, Chunking(512, 128))
    store.client = FakeClient(operations=[{"done": True, "error": {"message": "nope"}}])
    store.client.post = lambda url, **kwargs: {"name": "operations/i1", "done": False}

    with pytest.raises(UploadError, match="import failed"):
        store.put(build(make_article()))


def test_fetch_files_follows_pagination_and_skips_foreign_documents():
    store = VectorStore("key", STORE, Chunking(512, 128))
    store.client = FakeClient(
        pages=[
            {
                "documents": [
                    {
                        "name": f"{STORE}/documents/d1",
                        "customMetadata": [
                            {"key": "article_id", "stringValue": "1"},
                            {"key": "content_hash", "stringValue": "a"},
                        ],
                    },
                    {"name": f"{STORE}/documents/d2", "customMetadata": []},
                ],
                "nextPageToken": "page-2",
            },
            {
                "documents": [
                    {
                        "name": f"{STORE}/documents/d3",
                        "customMetadata": [
                            {"key": "article_id", "stringValue": "2"},
                            {"key": "content_hash", "stringValue": "b"},
                        ],
                    }
                ]
            },
        ]
    )

    files = store.fetch_files()

    assert files == {
        "1": RemoteFile(f"{STORE}/documents/d1", "a"),
        "2": RemoteFile(f"{STORE}/documents/d3", "b"),
    }


def test_remote_state_decides_the_delta(make_article):
    document = build(make_article())
    name = f"{STORE}/documents/d1"
    unchanged = VectorStoreState({"42": RemoteFile(name, document.content_hash)})
    changed = VectorStoreState({"42": RemoteFile(name, "stale")})

    assert VectorStoreState({}).status(document) is Status.ADDED
    assert changed.status(document) is Status.UPDATED
    assert unchanged.status(document) is Status.SKIPPED
    assert changed.existing(document).remote_id == name
