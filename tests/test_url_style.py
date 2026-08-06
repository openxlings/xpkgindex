"""Directory URLs are the canonical form; `file` style is for hosts that
serve files and never resolve a directory to its index.

Bilibili's Toy hosting is one: `/stats/` is a 404 there and only
`/stats/index.html` exists, so a site whose every internal link ends in `/`
renders its homepage and 404s on the first click. The pages written to disk
are identical in both styles — only the links differ.
"""

from __future__ import annotations

import os
import re
import urllib.parse

import pytest

from xpkgindex.build import build
from xpkgindex.render import render

from conftest import commit, init_repo, write_config, write_descriptor

HREF = re.compile(r'(?:href|src|action)="([^"]+)"')


@pytest.fixture
def repo(tmp_path):
    root = str(tmp_path / "index")
    os.makedirs(root)
    init_repo(root)
    write_config(root, docs={"landing": "guide", "entries": [
        {"slug": "guide", "title": "Guide", "path": "docs/guide.md"},
        {"slug": "other", "title": "Other", "path": "docs/other.md"}]})
    os.makedirs(os.path.join(root, "docs"))
    # A link between two docs — rewritten by guides.py, not by a template,
    # which is exactly where the suffix was missed the first time.
    open(os.path.join(root, "docs", "guide.md"), "w", encoding="utf-8").write(
        "# Guide\n\nSee [the other one](other.md).\n")
    open(os.path.join(root, "docs", "other.md"), "w", encoding="utf-8").write("# Other\n\nHi.\n")
    write_descriptor(root, "alpha", "widget")
    commit(root, "one package and two docs")
    return root


def _links(out: str, page: str) -> list[str]:
    text = open(os.path.join(out, page), encoding="utf-8").read()
    return [h for h in HREF.findall(text)
            if h and not h.startswith(("http://", "https://", "//", "#", "mailto:", "data:"))]


def _dangling(out: str, file_only: bool) -> list[str]:
    """Every internal link, resolved the way the host would resolve it."""
    bad = []
    for dirpath, _, files in os.walk(out):
        for name in files:
            if not name.endswith(".html"):
                continue
            page = os.path.join(dirpath, name)
            for raw in _links(out, os.path.relpath(page, out)):
                target = urllib.parse.unquote(raw.split("#")[0].split("?")[0])
                if not target:
                    continue
                dest = os.path.normpath(os.path.join(os.path.dirname(page), target))
                ok = os.path.isfile(dest) if file_only else (
                    os.path.isfile(dest) or os.path.isfile(os.path.join(dest, "index.html")))
                if not ok:
                    bad.append(f"{os.path.relpath(page, out)} -> {raw}")
    return bad


def test_directory_style_is_the_default(tmp_path, repo):
    site, config = build(repo, offline=True)
    assert config.url_style == "directory"
    out = str(tmp_path / "out")
    render(site, config, out)

    home = _links(out, "index.html")
    assert "packages/widget/" in home
    assert "stats/" in home
    assert not any(h.endswith("index.html") for h in home)


def test_file_style_points_at_the_page_itself(tmp_path, repo):
    site, config = build(repo, offline=True, url_style="file")
    out = str(tmp_path / "out")
    render(site, config, out)

    home = _links(out, "index.html")
    assert "packages/widget/index.html" in home
    assert "stats/index.html" in home
    # The homepage link is a real file rather than an empty href.
    assert "index.html" in home

    # A link between two documents is rewritten by guides.py, which renders
    # while the site is being built — a style applied at render time only
    # would arrive too late for it.
    guide = _links(out, os.path.join("docs", "guide", "index.html"))
    assert any(h.endswith("docs/other/index.html") for h in guide), guide


def test_a_file_only_host_can_serve_every_link(tmp_path, repo):
    """The point of the option: no dangling links when nothing resolves a
    directory to its index."""
    site, config = build(repo, offline=True, url_style="file")
    out = str(tmp_path / "out")
    render(site, config, out)
    assert _dangling(out, file_only=True) == []


def test_directory_style_would_not_survive_that_host(tmp_path, repo):
    """Pins why the option exists: the default form is fine everywhere else
    and broken there."""
    site, config = build(repo, offline=True)
    out = str(tmp_path / "out")
    render(site, config, out)
    assert _dangling(out, file_only=False) == []
    assert _dangling(out, file_only=True) != []


def test_the_pages_themselves_are_identical(tmp_path, repo):
    """Only links change: the same files are written either way, so switching
    styles is a re-render, not a different site."""
    site_a, config_a = build(repo, offline=True)
    out_a = str(tmp_path / "dir")
    render(site_a, config_a, out_a)

    site_b, config_b = build(repo, offline=True, url_style="file")
    out_b = str(tmp_path / "file")
    render(site_b, config_b, out_b)

    def tree(root):
        return sorted(os.path.relpath(os.path.join(d, f), root)
                      for d, _, fs in os.walk(root) for f in fs)

    assert tree(out_a) == tree(out_b)
