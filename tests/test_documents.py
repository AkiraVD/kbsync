"""Slugs, front matter and the body hash that drives the delta."""

from src.documents import build, build_all, hash_body, slug_for, slugify


def test_slug_comes_from_the_help_center_url(make_article):
    assert slug_for(make_article()) == "add-a-video"


def test_slug_falls_back_to_the_title(make_article):
    assert slug_for(make_article(url="")) == "how-do-i-add-a-video"


def test_slugify_strips_punctuation_and_folds_accents():
    assert slugify("Refer ’ Earn: a Program") == "refer-earn-a-program"
    assert slugify("Café Menü") == "cafe-menu"


def test_colliding_slugs_fall_back_to_the_article_id(make_article):
    documents = build_all([make_article(id=1), make_article(id=2)])
    assert [document.slug for document in documents] == ["add-a-video", "add-a-video-2"]


def test_file_has_front_matter_a_title_and_a_citable_url(make_article):
    document = build(make_article())

    assert document.filename == "add-a-video.md"
    assert document.text.startswith("---\n")
    assert 'title: "How do I add a video?"' in document.text
    assert 'section: "Assets"' in document.text
    assert 'labels: ["video"]' in document.text
    assert "\n# How do I add a video?\n" in document.text
    assert (
        "Article URL: https://support.example.test/hc/en-us/articles/42-Add-A-Video"
        in document.text
    )


def test_hash_covers_the_body_only(make_article):
    baseline = build(make_article())

    assert baseline.content_hash == hash_body("Pick **Add**.\n")
    assert build(make_article(title="Renamed")).content_hash == baseline.content_hash
    assert build(make_article(updated_at="2026-10-02T00:00:00Z")).content_hash == (
        baseline.content_hash
    )
    assert build(make_article(body_html="<p>Other</p>")).content_hash != (
        baseline.content_hash
    )
