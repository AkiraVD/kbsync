"""The cleaning rules: what survives conversion and what must not."""

from src.html_to_markdown import convert


def test_keeps_headings_lists_and_emphasis():
    html = "<h2>Add a Screen</h2><ul><li>Open <strong>Media Library</strong></li></ul>"
    assert convert(html) == "## Add a Screen\n\n- Open **Media Library**\n"


def test_keeps_code_blocks_and_relative_links():
    html = '<pre><code>docker run app</code></pre><p><a href="/hc/en-us/articles/42">next</a></p>'
    out = convert(html)
    assert "docker run app" in out
    assert "[next](/hc/en-us/articles/42)" in out


def test_keeps_images_with_their_alt_text():
    html = '<p><img src="https://example.test/a.png" alt="Add Screen button" width="80"></p>'
    assert convert(html) == "![Add Screen button](https://example.test/a.png)\n"


def test_unwraps_styling_spans():
    assert convert('<p><span style="color: #434343;">Plain words</span></p>') == "Plain words\n"


def test_drops_in_page_table_of_contents():
    html = (
        '<ul><li><a href="#Setup">Setup</a></li><li><a href="#Fix">Fix</a></li></ul>'
        "<h2>Setup</h2><p>Body.</p>"
    )
    out = convert(html)
    assert "Setup](#" not in out
    assert out.startswith("## Setup")


def test_keeps_lists_that_link_elsewhere():
    html = '<ul><li><a href="/hc/en-us/articles/7">Real article</a></li></ul>'
    assert "Real article" in convert(html)


def test_drops_empty_anchor_targets():
    assert convert('<p><a name="Setup"></a></p><h2>Setup</h2>') == "## Setup\n"


def test_single_column_table_becomes_a_quote():
    html = (
        '<figure class="wysiwyg-table"><table><tbody>'
        "<tr><td><strong>TIP</strong></td></tr><tr><td>Use a service account.</td></tr>"
        "</tbody></table></figure>"
    )
    assert convert(html) == "> TIP — Use a service account.\n"


def test_real_table_stays_a_table():
    html = (
        "<table><thead><tr><th>Player</th><th>OS</th></tr></thead>"
        "<tbody><tr><td>Stick 4K</td><td>Android</td></tr></tbody></table>"
    )
    out = convert(html)
    assert "| Player | OS |" in out
    assert "| Stick 4K | Android |" in out


def test_embedded_video_survives_as_a_link():
    html = '<iframe src="https://video.example.test/x" title="Walkthrough"></iframe>'
    assert convert(html) == "[Walkthrough](https://video.example.test/x)\n"


def test_body_h1_is_demoted_so_the_title_stays_unique():
    assert convert("<h1>Overview</h1>") == "## Overview\n"


def test_empty_body_is_handled():
    assert convert("") == "\n"


def test_inline_base64_image_is_dropped():
    html = '<p><img src="data:image/png;base64,iVBORw0KGgoAAAANS" alt=""></p><p>Scan it.</p>'

    out = convert(html)

    assert "base64" not in out
    assert out == "Scan it.\n"


def test_inline_base64_image_keeps_its_alt_text():
    html = '<p><img src="data:image/png;base64,iVBORw0K" alt="The QR code"></p>'

    assert convert(html) == "The QR code\n"


def test_a_normal_image_url_is_untouched():
    html = '<p><img src="https://example.test/a.png" alt="Add"></p>'

    assert convert(html) == "![Add](https://example.test/a.png)\n"
