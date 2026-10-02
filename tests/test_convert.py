"""Conversion is pure string work, so these run offline."""

from src.convert import article_slug, content_hash, render, slugify, to_markdown


def test_keeps_headings_lists_and_emphasis():
    html = "<h2>Add a Screen</h2><ul><li>Open <strong>Media Library</strong></li></ul>"
    assert to_markdown(html) == "## Add a Screen\n\n- Open **Media Library**\n"


def test_keeps_code_blocks_and_relative_links():
    html = '<pre><code>docker run app</code></pre><p><a href="/hc/en-us/articles/42">next</a></p>'
    out = to_markdown(html)
    assert "docker run app" in out
    assert "[next](/hc/en-us/articles/42)" in out


def test_keeps_images_with_their_alt_text():
    html = '<p><img src="https://example.test/a.png" alt="Add Screen button" width="80"></p>'
    assert to_markdown(html) == "![Add Screen button](https://example.test/a.png)\n"


def test_unwraps_styling_spans():
    html = '<p><span style="color: #434343;">Plain words</span></p>'
    assert to_markdown(html) == "Plain words\n"


def test_drops_in_page_table_of_contents():
    html = (
        '<ul><li><a href="#Setup">Setup</a></li><li><a href="#Fix">Fix</a></li></ul>'
        "<h2>Setup</h2><p>Body.</p>"
    )
    out = to_markdown(html)
    assert "Setup](#" not in out
    assert out.startswith("## Setup")


def test_keeps_lists_that_link_elsewhere():
    html = '<ul><li><a href="/hc/en-us/articles/7">Real article</a></li></ul>'
    assert "Real article" in to_markdown(html)


def test_drops_empty_anchor_targets():
    html = '<p><a name="Setup"></a></p><h2>Setup</h2>'
    assert to_markdown(html) == "## Setup\n"


def test_single_column_table_becomes_a_quote():
    html = (
        '<figure class="wysiwyg-table"><table><tbody>'
        "<tr><td><strong>TIP</strong></td></tr><tr><td>Use a service account.</td></tr>"
        "</tbody></table></figure>"
    )
    assert to_markdown(html) == "> TIP — Use a service account.\n"


def test_real_table_stays_a_table():
    html = (
        "<table><thead><tr><th>Player</th><th>OS</th></tr></thead>"
        "<tbody><tr><td>Stick 4K</td><td>Android</td></tr></tbody></table>"
    )
    out = to_markdown(html)
    assert "| Player | OS |" in out
    assert "| Stick 4K | Android |" in out


def test_body_h1_is_demoted_so_the_title_stays_unique():
    assert to_markdown("<h1>Overview</h1>") == "## Overview\n"


def test_slug_comes_from_the_help_center_url():
    article = {
        "html_url": "https://support.example.test/hc/en-us/articles/123-How-To-Add-A-Screen",
        "title": "How To Add A Screen",
    }
    assert article_slug(article) == "how-to-add-a-screen"


def test_slugify_strips_punctuation_and_folds_accents():
    assert slugify("Refer ’ Earn: a Program") == "refer-earn-a-program"
    assert slugify("Café Menü") == "cafe-menu"


def test_render_writes_front_matter_and_a_citable_url():
    article = {
        "id": 42,
        "title": "How do I add a YouTube video?",
        "html_url": "https://support.example.test/hc/en-us/articles/42-YouTube",
        "label_names": ["video"],
        "updated_at": "2026-09-01T00:00:00Z",
        "body": "<p>Pick <strong>Add</strong>.</p>",
    }
    contents, digest = render(article, section_name="Assets")

    assert contents.startswith("---\n")
    assert '"How do I add a YouTube video?"' in contents
    assert 'section: "Assets"' in contents
    assert "\n# How do I add a YouTube video?\n" in contents
    # Repeated in the body so a chunk that misses the front matter can still cite.
    assert "Article URL: https://support.example.test/hc/en-us/articles/42-YouTube" in contents
    assert digest == content_hash("Pick **Add**.\n")


def test_hash_tracks_the_body_not_the_metadata():
    base = {"id": 1, "title": "T", "html_url": "u", "body": "<p>One</p>"}
    edited = {**base, "updated_at": "2026-10-01T00:00:00Z"}
    retitled = {**base, "title": "Different"}

    assert render(base)[1] == render(edited)[1]
    assert render(base)[1] == render(retitled)[1]
    assert render(base)[1] != render({**base, "body": "<p>Two</p>"})[1]
