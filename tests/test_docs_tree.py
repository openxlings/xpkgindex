"""A docs tree is discovered, not listed: numbered chapters in reading order,
each with its translation from the language's directory (the layout mcpp,
xlings and xim-pkgindex share)."""

from __future__ import annotations

import os

import pytest

from xpkgindex.build import BuildError, build
from xpkgindex.config import load_config

from conftest import commit, init_repo, write_config, write_descriptor


def _write(root, rel, text):
    full = os.path.join(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


@pytest.fixture
def repo(tmp_path):
    root = str(tmp_path / "index")
    os.makedirs(root)
    init_repo(root)
    write_config(root, languages=["en", "zh"], docs={"tree": {
        "root": "docs", "translations": {"zh": "docs/zh"}, "exclude": ["specs/legacy"]}})
    _write(root, "docs/README.md", "# Documentation\n\n**English** | [简体中文](zh/README.md)\n\n[start](01-getting-started.md)\n")
    _write(root, "docs/zh/README.md", "# 文档\n\n[English](../README.md) | **简体中文**\n\n[开始](01-getting-started.md)\n")
    _write(root, "docs/01-getting-started.md", "# Getting Started\n\n**English** | [简体中文](zh/01-getting-started.md)\n")
    _write(root, "docs/zh/01-getting-started.md", "# 快速开始\n\n[English](../01-getting-started.md) | **简体中文**\n")
    _write(root, "docs/00-what-it-is.md", "# What It Is\n")
    _write(root, "docs/zh/00-what-it-is.md", "# 是什么\n")
    _write(root, "docs/specs/format.md", "# The Format\n")
    _write(root, "docs/specs/legacy/v0.md", "# V0\n")
    write_descriptor(root, "alpha", "widget")
    commit(root, "a docs tree")
    return root


def test_the_tree_is_found_in_reading_order_with_translations(repo):
    config = load_config(repo)
    paths = [g.path for g in config.guides]
    assert paths == ["docs/README.md", "docs/00-what-it-is.md", "docs/01-getting-started.md", "docs/specs/format.md"]
    by_path = {g.path: g for g in config.guides}
    assert by_path["docs/README.md"].slug == "docs-index"
    assert by_path["docs/01-getting-started.md"].slug == "01-getting-started"
    assert by_path["docs/specs/format.md"].slug == "specs-format"
    assert by_path["docs/01-getting-started.md"].translations == {"zh": "docs/zh/01-getting-started.md"}
    assert by_path["docs/01-getting-started.md"].title == "Getting Started"
    assert "docs/specs/legacy/v0.md" not in paths, "an excluded directory"
    assert any("docs/specs/format.md has no zh translation" in w for w in config.docs_tree_warnings)


def test_strict_refuses_what_does_not_render(repo):
    with pytest.raises(BuildError, match="no zh translation"):
        build(repo, offline=True, strict=True)
    site, _ = build(repo, offline=True)
    assert any("no zh translation" in w for w in site.warnings)
