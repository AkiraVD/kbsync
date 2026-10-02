"""Status is what the daily job uses to upload only the delta."""

from src.documents import build
from src.manifest import Manifest
from src.models import Status


def test_unknown_article_is_added(make_article):
    assert Manifest().status(build(make_article())) is Status.ADDED


def test_same_hash_is_skipped(make_article):
    document = build(make_article())
    manifest = Manifest({"42": {"content_hash": document.content_hash}})

    assert manifest.status(document) is Status.SKIPPED


def test_changed_body_is_updated(make_article):
    manifest = Manifest({"42": {"content_hash": "stale"}})

    assert manifest.status(build(make_article())) is Status.UPDATED


def test_round_trip_through_disk(tmp_path, make_article):
    document = build(make_article())
    written = Manifest()
    written.record(document)
    written.save(tmp_path)

    reloaded = Manifest.load(tmp_path)

    assert reloaded.status(document) is Status.SKIPPED
    assert reloaded.previous["42"]["slug"] == "add-a-video"


def test_unreadable_manifest_is_ignored(tmp_path, make_article):
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")

    assert Manifest.load(tmp_path).status(build(make_article())) is Status.ADDED
