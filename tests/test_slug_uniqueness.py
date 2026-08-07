"""Duplicate slugs used to overwrite each other's pages in silence: three
`imgui` packages produced one HTML file and two of them vanished from the
live site. That must be a build failure, not a surprise."""

import os

import pytest

from conftest import write_plugin, write_config
from xpkgindex.build import BuildError, build


def test_duplicate_slugs_fail_the_build(repo):
    with pytest.raises(BuildError) as exc:
        build(repo, offline=True)
    message = str(exc.value)
    assert "duplicate package slugs" in message
    assert "widget" in message
    # The error has to name the files, or it is not actionable.
    assert "alpha.widget.lua" in message
    assert "beta.widget.lua" in message


def test_plugin_identity_resolves_the_clash(repo):
    plugin = write_plugin(repo, '''
        from xpkgindex.models import Identity
        from xpkgindex.plugins import Plugin

        class P(Plugin):
            name = "test"
            def identity(self, raw, path):
                return Identity.joined(raw.get("namespace", ""), raw.get("name", ""))
    ''')
    write_config(repo, plugins=[plugin],
                 install_command_template="tool add {ref}@{version}")

    site, _ = build(repo, offline=True)
    slugs = sorted(p.identity.slug for p in site.packages)
    assert slugs == ["alpha.widget", "beta.widget"]
    assert site.packages[0].install_command == "tool add alpha.widget@1.0.0"


def test_pages_are_written_per_package(repo, tmp_path):
    from xpkgindex.render import render

    plugin = write_plugin(repo, '''
        from xpkgindex.models import Identity
        from xpkgindex.plugins import Plugin

        class P(Plugin):
            name = "test"
            def identity(self, raw, path):
                return Identity.joined(raw.get("namespace", ""), raw.get("name", ""))
    ''')
    write_config(repo, plugins=[plugin])
    site, config = build(repo, offline=True)
    out = str(tmp_path / "site")
    render(site, config, out)

    assert os.path.isfile(os.path.join(out, "packages", "alpha.widget", "index.html"))
    assert os.path.isfile(os.path.join(out, "packages", "beta.widget", "index.html"))
    # The ambiguous short name gets a disambiguation page, not a guess.
    with open(os.path.join(out, "packages", "widget.html"), encoding="utf-8") as f:
        html = f.read()
    assert "alpha.widget" in html and "beta.widget" in html
    assert "http-equiv=\"refresh\"" not in html
