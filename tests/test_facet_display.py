"""A multi-valued facet must render as separate values, not one blob.

`build.py` filters facets with `str(value).split()`, so a facet is
multi-valued *by contract*. The package page rendered the raw value instead, so
a two-value facet came out as `tui web-ui` -- read as one odd token rather than
two. Filtering and display have to split the same way.
"""

from __future__ import annotations

import os
import re

import pytest

from xpkgindex.build import build
from xpkgindex.render import render

from conftest import commit, init_repo, write_config, write_descriptor, write_plugin

PLUGIN = '''
    from xpkgindex.models import Facet
    from xpkgindex.plugins import Plugin

    class P(Plugin):
        api_version = 1
        name = "multi"

        def on_package(self, pkg, raw):
            pkg.facets["kind"] = "tui web-ui"
            pkg.facets["single"] = "solo"

        def facets(self):
            return [Facet(key="kind", label="kind", weight=10),
                    Facet(key="single", label="single", weight=20)]
'''


@pytest.fixture
def site(tmp_path):
    root = str(tmp_path / "index")
    os.makedirs(root)
    init_repo(root)
    rel = write_plugin(root, PLUGIN)
    write_config(root, plugins=[rel])
    write_descriptor(root, "alpha", "widget")
    commit(root, "add widget", date="2026-01-01")
    out = str(tmp_path / "site")
    data, config = build(root, offline=True)
    render(data, config, out)
    with open(os.path.join(out, "packages", "widget", "index.html"),
              encoding="utf-8") as f:
        return f.read()


def _facet_block(html: str, key: str) -> str:
    m = re.search(rf"<dt>{key}</dt>\s*<dd>(.*?)</dd>", html, re.S)
    assert m, f"facet {key!r} is not on the page"
    return m.group(1)


def test_multi_valued_facet_renders_each_value_separately(site):
    block = _facet_block(site, "kind")
    values = re.findall(r"<span class=\"plat\">([^<]+)</span>", block)
    assert values == ["tui", "web-ui"], \
        f"expected two rendered values, got {values!r}"


def test_a_single_valued_facet_is_unchanged(site):
    block = _facet_block(site, "single")
    assert re.findall(r"<span class=\"plat\">([^<]+)</span>", block) == ["solo"]


def test_the_joined_form_never_reaches_the_page(site):
    """The bug's signature: both values inside one element."""
    assert "tui web-ui" not in re.sub(r"\s+", " ", site)
