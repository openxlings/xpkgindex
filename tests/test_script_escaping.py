"""Values interpolated into a <script> must be valid JavaScript.

Autoescaping does not stop at HTML text nodes: it applies inside `<script>`
too. But a classic script is not HTML-parsed, so `&#34;` never decodes back to
a quote — it is a SyntaxError, and a syntax error takes down the *entire*
script element.

That is what `theme.style: "dark"` did. The template built the value by hand
as `'"' + config.style + '"'`, which reached the page as

    var fixed = &#34;dark&#34;;

so the pre-paint IIFE failed to parse. The visible symptom was only "dark mode
does not apply", but the same IIFE also carries the language redirect, and that
died too — a theming option silently disabling i18n. Neither is covered by
looking at the rendered HTML for the right *text*; the check has to be that the
script parses.
"""

from __future__ import annotations

import json
import os
import re

import pytest

from xpkgindex.build import build
from xpkgindex.render import render

from conftest import commit, init_repo, write_config, write_descriptor

SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)
# Entities that are meaningful in JS source and never legal inside it.
BROKEN = re.compile(r"&(?:#34|quot|#39|apos|amp|lt|gt);")


def _site(tmp_path, **config):
    root = str(tmp_path / "index")
    os.makedirs(root)
    init_repo(root)
    write_config(root, **config)
    write_descriptor(root, "alpha", "widget")
    commit(root, "add widget", date="2026-01-01")
    out = str(tmp_path / "site")
    site, config = build(root, offline=True)
    render(site, config, out)
    return out


def _inline_scripts(site):
    for dirpath, _, names in os.walk(site):
        for n in names:
            if not n.endswith(".html"):
                continue
            path = os.path.join(dirpath, n)
            with open(path, encoding="utf-8") as f:
                html = f.read()
            for m in SCRIPT.finditer(html):
                yield os.path.relpath(path, site), m.group(1)


@pytest.mark.parametrize("style", ["auto", "dark", "light"])
def test_inline_scripts_carry_no_html_entities(tmp_path, style):
    site = _site(tmp_path, theme={"style": style})
    for page, body in _inline_scripts(site):
        found = BROKEN.search(body)
        assert not found, (
            f"{page}: inline script contains {found.group(0)!r}; HTML entities "
            f"do not decode inside <script>, so this is a SyntaxError that "
            f"disables every statement in the element"
        )


@pytest.mark.parametrize("style,expected", [("dark", "dark"), ("light", "light")])
def test_fixed_theme_reaches_the_page_as_a_js_string(tmp_path, style, expected):
    site = _site(tmp_path, theme={"style": style})
    with open(os.path.join(site, "index.html"), encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"var fixed = (.+?);", html)
    assert m, "the pre-paint theme bootstrap is gone"
    assert json.loads(m.group(1)) == expected


def test_auto_leaves_the_theme_to_the_visitor(tmp_path):
    site = _site(tmp_path, theme={"style": "auto"})
    with open(os.path.join(site, "index.html"), encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"var fixed = (.+?);", html)
    assert m and json.loads(m.group(1)) is None
