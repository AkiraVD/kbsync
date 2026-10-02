"""Upload behaviour, with the HTTP layer stubbed out."""

import pytest

from src.documents import build
from src.models import Status
from src.state import VectorStoreState
from src.vectorstore import Chunking, RemoteFile, VectorStore, _attributes


class FakeClient:
    def __init__(self, pages: list[dict] | None = None):
        self.pages = pages or [{"data": [], "has_more": False}]
        self.calls: list[tuple] = []

    def get(self, url, params=None):
        self.calls.append(("GET", url, params))
        return self.pages.pop(0) if self.pages else {"data": [], "has_more": False}

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return {"id": "file-new"}

    def delete(self, url):
        self.calls.append(("DELETE", url, None))
        return {"deleted": True}


@pytest.fixture
def store():
    vector_store = VectorStore("key", "vs_1", Chunking(800, 200))
    vector_store.client = FakeClient()
    return vector_store


def test_chunking_sends_a_static_strategy():
    assert Chunking(800, 200).as_param() == {
        "type": "static",
        "static": {"max_chunk_size_tokens": 800, "chunk_overlap_tokens": 200},
    }


@pytest.mark.parametrize(
    "characters, expected",
    [(100, 1), (800 * 4, 1), (1400 * 4, 2), (3000 * 4, 5)],
)
def test_chunk_estimate_grows_with_the_document(characters, expected):
    assert Chunking(800, 200).estimate_chunks("x" * characters) == expected


def test_attributes_carry_the_hash_the_next_run_compares(make_article):
    document = build(make_article())
    attributes = _attributes(document)

    assert attributes["article_id"] == "42"
    assert attributes["content_hash"] == document.content_hash
    assert attributes["slug"] == "add-a-video"
    assert len(attributes) <= 16
    assert all(len(str(value)) <= 512 for value in attributes.values())


def test_put_creates_the_file_then_attaches_it(store, make_article):
    store.put(build(make_article()))

    methods = [(method, url.rsplit("/v1/", 1)[-1]) for method, url, _ in store.client.calls]
    assert methods == [
        ("POST", "files"),
        ("POST", "vector_stores/vs_1/files"),
    ]


def test_put_discards_the_version_it_replaces(store, make_article):
    store.put(build(make_article()), replacing=RemoteFile("file-old", "stale"))

    deletes = [url for method, url, _ in store.client.calls if method == "DELETE"]
    assert deletes == [
        "https://api.openai.com/v1/vector_stores/vs_1/files/file-old",
        "https://api.openai.com/v1/files/file-old",
    ]


def test_attach_sends_the_chunking_strategy_and_attributes(store, make_article):
    store.put(build(make_article()))

    _, _, kwargs = store.client.calls[1]
    assert kwargs["json"]["chunking_strategy"]["static"]["max_chunk_size_tokens"] == 800
    assert kwargs["json"]["attributes"]["article_id"] == "42"


def test_fetch_files_follows_pagination_and_skips_foreign_files():
    store = VectorStore("key", "vs_1", Chunking(800, 200))
    store.client = FakeClient(
        [
            {
                "data": [
                    {"id": "f1", "attributes": {"article_id": "1", "content_hash": "a"}},
                    {"id": "f2", "attributes": None},
                ],
                "has_more": True,
            },
            {
                "data": [
                    {"id": "f3", "attributes": {"article_id": "2", "content_hash": "b"}}
                ],
                "has_more": False,
            },
        ]
    )

    files = store.fetch_files()

    assert files == {"1": RemoteFile("f1", "a"), "2": RemoteFile("f3", "b")}


def test_remote_state_decides_the_delta(make_article):
    document = build(make_article())
    unchanged = VectorStoreState({"42": RemoteFile("f1", document.content_hash)})
    changed = VectorStoreState({"42": RemoteFile("f1", "stale")})

    assert VectorStoreState({}).status(document) is Status.ADDED
    assert changed.status(document) is Status.UPDATED
    assert unchanged.status(document) is Status.SKIPPED
    assert changed.existing(document).file_id == "f1"
