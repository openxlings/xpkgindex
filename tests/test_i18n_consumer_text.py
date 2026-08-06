"""Text an index writes itself — in the config or from a plugin — renders in
the reader's language.

The framework never translates anything; it only resolves `{"en": …, "zh": …}`
maps that the consumer wrote. These tests pin that contract, including the two
places it is easy to get wrong: `index.json`, which promises plain strings, and
a doc's hand-written language line, which must not survive next to the site's
own switcher.
"""

from __future__ import annotations

import json
import os

import pytest

from xpkgindex.build import build
from xpkgindex.i18n import localize
from xpkgindex.render import render

from conftest import commit, init_repo, write_config, write_descriptor, write_plugin


@pytest.fixture
def repo(tmp_path):
    """One package, so these tests are about text rather than about slugs."""
    root = str(tmp_path / "index")
    os.makedirs(root)
    init_repo(root)
    write_config(root)
    write_descriptor(root, "alpha", "widget")
    commit(root, "add widget")
    return root


def test_localize_falls_back_through_subtag_then_default():
    value = {"en": "Docs", "zh": "文档"}
    assert localize(value, "zh") == "文档"
    assert localize(value, "zh-Hant") == "文档"       # primary subtag
    assert localize(value, "ja", default="en") == "Docs"
    assert localize("plain", "zh") == "plain"        # untouched


def test_localize_never_returns_a_dict_for_a_partial_translation():
    assert localize({"zh": "只有中文"}, "en") == "只有中文"
    assert localize({}, "en") == ""


PLUGIN = '''
    from xpkgindex.plugins import Plugin
    from xpkgindex.models import Block, Facet, FacetValue

    def _t(en, zh):
        return {"en": en, "zh": zh}

    class SitePlugin(Plugin):
        api_version = 1

        def facets(self):
            return [Facet(key="kind", label=_t("kind", "类型"),
                          values=[FacetValue(key="lib", label=_t("library", "库"))])]

        def on_package(self, pkg, raw):
            pkg.facets["kind"] = "lib"

        def detail_blocks(self, pkg):
            return [Block(kind="callout", title=_t("Build", "构建"),
                          data={"text": _t("Built by CI.", "由 CI 构建。")})]
'''


def _site(root):
    plugin = write_plugin(root, PLUGIN)
    write_config(
        root,
        site={"title": {"en": "Test Index", "zh": "测试索引"},
              "description": {"en": "packages", "zh": "包"}},
        languages=["en", "zh"],
        plugins=[plugin],
        install={"primary": {"label": {"en": "Install", "zh": "安装"},
                             "command": "tool install"}},
    )
    write_descriptor(root, "alpha", "widget")
    commit(root, "localized index")
    site, config = build(root, offline=True)
    return config, site


def test_each_locale_renders_the_consumers_own_words(tmp_path, repo):
    config, site = _site(repo)
    out = str(tmp_path / "out")
    render(site, config, out)

    en = open(os.path.join(out, "index.html"), encoding="utf-8").read()
    zh = open(os.path.join(out, "zh", "index.html"), encoding="utf-8").read()

    assert "Test Index" in en and "测试索引" not in en
    assert "测试索引" in zh and "Install" not in zh
    assert "安装" in zh
    # Plugin-authored labels follow too — facet axis and facet value.
    assert "kind" in en and "library" in en
    assert "类型" in zh and "库" in zh

    en_pkg = open(os.path.join(out, "packages", "widget", "index.html"),
                  encoding="utf-8").read()
    zh_pkg = open(os.path.join(out, "zh", "packages", "widget", "index.html"),
                  encoding="utf-8").read()
    assert "Built by CI." in en_pkg
    assert "由 CI 构建。" in zh_pkg


def test_index_json_stays_plain_strings(tmp_path, repo):
    """schema 1 promises strings; a consumer parsing it must not suddenly get
    a per-locale map where a label used to be."""
    config, site = _site(repo)
    out = str(tmp_path / "out")
    render(site, config, out)

    data = json.load(open(os.path.join(out, "index.json"), encoding="utf-8"))
    assert data["site"]["title"] == "Test Index"          # default locale
    assert isinstance(data["site"]["description"], str)
    kind = [f for f in data["facets"] if f["key"] == "kind"][0]
    assert kind["label"] == "kind"
    assert kind["values"][0]["label"] == "library"
    block = data["packages"][0]["blocks"][0]
    assert block["title"] == "Build"
    assert block["data"]["text"] == "Built by CI."


DOC_EN = """# Quick start

**English** | [简体中文](quick-start.zh.md)

Install it.
"""

DOC_ZH = """# 快速开始

[English](quick-start.md) | **简体中文**

装上它。
"""


def test_a_docs_own_language_line_is_dropped(tmp_path, repo):
    """It exists for GitHub. On the site the header switcher does the job, and
    the line would point at raw .md files."""
    docs = os.path.join(repo, "docs")
    os.makedirs(docs, exist_ok=True)
    open(os.path.join(docs, "quick-start.md"), "w", encoding="utf-8").write(DOC_EN)
    open(os.path.join(docs, "quick-start.zh.md"), "w", encoding="utf-8").write(DOC_ZH)
    write_config(
        repo,
        languages=["en", "zh"],
        docs={"landing": "quick-start",
              "entries": [{"slug": "quick-start", "title": "Quick start",
                           "path": "docs/quick-start.md",
                           "translations": {"zh": "docs/quick-start.zh.md"}}]},
    )
    commit(repo, "add docs")
    site, config = build(repo, offline=True)
    out = str(tmp_path / "out")
    render(site, config, out)

    en = open(os.path.join(out, "docs", "quick-start", "index.html"), encoding="utf-8").read()
    zh = open(os.path.join(out, "zh", "docs", "quick-start", "index.html"), encoding="utf-8").read()
    body_en = en.split('class="prose"')[1]
    body_zh = zh.split('class="prose"')[1]

    assert "quick-start.zh.md" not in body_en
    assert "<strong>English</strong>" not in body_en
    assert "Install it." in body_en
    # The page still follows the switcher: zh gets the translated body.
    assert "装上它。" in body_zh
    assert "<strong>简体中文</strong>" not in body_zh


def test_an_ordinary_link_between_docs_survives(tmp_path, repo):
    """Only a *language* line is dropped — a link to another doc is content."""
    docs = os.path.join(repo, "docs")
    os.makedirs(docs, exist_ok=True)
    open(os.path.join(docs, "a.md"), "w", encoding="utf-8").write(
        "# A\n\nSee [B](b.md) for the rest.\n")
    open(os.path.join(docs, "b.md"), "w", encoding="utf-8").write("# B\n\nThe rest.\n")
    write_config(repo, docs={"landing": "a", "entries": [
        {"slug": "a", "title": "A", "path": "docs/a.md"},
        {"slug": "b", "title": "B", "path": "docs/b.md"}]})
    commit(repo, "add docs")
    site, config = build(repo, offline=True)
    out = str(tmp_path / "out")
    render(site, config, out)

    page = open(os.path.join(out, "docs", "a", "index.html"), encoding="utf-8").read()
    assert "See" in page and "docs/b/" in page
