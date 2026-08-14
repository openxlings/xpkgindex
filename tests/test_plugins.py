"""Plugin contract: a broken plugin degrades, it does not take the site down.

An index repo's own extension block failing to parse must never turn the
whole package browser into a red CI run.
"""

from conftest import write_config, write_descriptor, write_plugin
from xpkgindex.build import build


def test_failing_hook_is_a_warning_not_a_failure(repo):
    plugin = write_plugin(repo, '''
        from xpkgindex.models import Identity
        from xpkgindex.plugins import Plugin

        class P(Plugin):
            name = "boom"
            def identity(self, raw, path):
                return Identity.joined(raw.get("namespace", ""), raw.get("name", ""))
            def on_package(self, pkg, raw):
                raise RuntimeError("extension block is malformed")
    ''')
    write_config(repo, plugins=[plugin])

    site, _ = build(repo, offline=True)
    assert site.total_packages == 2
    assert any("boom" in w and "on_package" in w for w in site.warnings)


def test_api_version_mismatch_refuses_to_load(repo):
    plugin = write_plugin(repo, '''
        from xpkgindex.plugins import Plugin

        class P(Plugin):
            name = "future"
            api_version = 99
    ''')
    write_config(repo, plugins=[plugin])

    # Identity falls back to the core default, so the two widgets now clash;
    # what matters here is the warning, so use distinct names instead.
    import os
    os.remove(os.path.join(repo, "pkgs", "w", "beta.widget.lua"))
    site, _ = build(repo, offline=True)
    assert any("api_version" in w for w in site.warnings)


def test_missing_plugin_file_is_reported(repo):
    write_config(repo, plugins=[".xpkgindex/plugins/nope.py"])
    import os
    os.remove(os.path.join(repo, "pkgs", "w", "beta.widget.lua"))
    site, _ = build(repo, offline=True)
    assert any("failed to load" in w for w in site.warnings)


def test_row_spec_is_plugin_owned(repo):
    """The listing row is a plugin decision, with a working default."""
    plugin = write_plugin(repo, '''
        from xpkgindex.models import Identity, RowSpec
        from xpkgindex.plugins import Plugin

        class P(Plugin):
            name = "rows"
            def identity(self, raw, path):
                return Identity.joined(raw.get("namespace", ""), raw.get("name", ""))
            def row(self, pkg):
                return RowSpec(variant="card", tone="tool", lead="tool",
                               code="$ " + pkg.name, badges=["custom"])
    ''')
    write_config(repo, plugins=[plugin])

    site, _ = build(repo, offline=True)
    row = site.packages[0].row
    assert (row.variant, row.tone, row.lead) == ("card", "tool", "tool")
    assert row.code == "$ widget"
    assert row.badges == ["custom"]


def test_row_default_falls_back_to_install_command(repo):
    """Without a plugin there is no interface line, so the row must still say
    something actionable rather than rendering blank."""
    import os
    os.remove(os.path.join(repo, "pkgs", "w", "beta.widget.lua"))
    site, _ = build(repo, offline=True)
    row = site.packages[0].row
    assert row.variant == "code"
    assert row.code == ""
    assert row.install == "tool add widget@1.0.0"


def test_plugin_may_own_the_install_command(repo):
    """A per-package install command survives the index-wide template.

    The template runs after every plugin hook, so without an explicit
    precedence rule it silently overwrote whatever the plugin set -- and a
    plugin that can shape every other part of the page but not this line has
    no way to show a spec that differs per package.
    """
    plugin = write_plugin(repo, '''
        from xpkgindex.models import Identity
        from xpkgindex.plugins import Plugin

        class P(Plugin):
            name = "installs"
            def identity(self, raw, path):
                return Identity.joined(raw.get("namespace", ""), raw.get("name", ""))
            def on_package(self, pkg, raw):
                if raw.get("namespace") == "alpha":
                    pkg.extensions.setdefault("_core", {})["install_command"] = \\
                        "native add widget#deadbeef"
    ''')
    write_config(repo, plugins=[plugin])

    site, _ = build(repo, offline=True)
    by_ref = {p.identity.install_ref: p for p in site.packages}
    assert by_ref["alpha.widget"].install_command == "native add widget#deadbeef"
    # The package the plugin did not claim still gets the template, so opting
    # one package in does not opt the whole index out.
    assert by_ref["beta.widget"].install_command == "tool add beta.widget@1.0.0"


def test_blocks_and_facets_reach_the_model(repo):
    plugin = write_plugin(repo, '''
        from xpkgindex.models import Block, Facet, FacetValue, Identity
        from xpkgindex.plugins import Plugin

        class P(Plugin):
            name = "demo"
            def identity(self, raw, path):
                return Identity.joined(raw.get("namespace", ""), raw.get("name", ""))
            def on_package(self, pkg, raw):
                pkg.extensions["demo"] = {"ok": True}
                pkg.facets["surface"] = "module"
            def facets(self):
                return [Facet(key="surface", label="how you use it",
                              values=[FacetValue(key="module", label="import")])]
            def detail_blocks(self, pkg):
                return [Block(kind="code", weight=10,
                              data={"role": "interface", "code": "import demo;",
                                    "tone": "module", "label": "import"})]
    ''')
    write_config(repo, plugins=[plugin])

    site, _ = build(repo, offline=True)
    pkg = site.packages[0]
    assert pkg.extensions["demo"] == {"ok": True}
    assert pkg.interface.data["code"] == "import demo;"
    assert pkg.tone == "module"
    surface = [f for f in site.facets if f.key == "surface"][0]
    assert surface.values[0].count == 2
