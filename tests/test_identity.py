"""Identity is three separate strings. Conflating them is exactly how
mcpp-index shipped `mcpp add json@3.12.0` (issue #170) while xim-pkgindex
would have shipped the opposite bug, `xlings install config.claude-llm`."""

from xpkgindex.models import Identity


def test_plain_keeps_namespace_out_of_every_string():
    ident = Identity.plain("config", "claude-llm")
    assert ident.display == "claude-llm"
    assert ident.slug == "claude-llm"
    assert ident.install_ref == "claude-llm"
    assert ident.namespace == "config"          # still available as metadata


def test_joined_puts_namespace_into_the_identity():
    ident = Identity.joined("nlohmann", "json")
    assert ident.display == "nlohmann.json"
    assert ident.slug == "nlohmann.json"
    assert ident.install_ref == "nlohmann.json"


def test_joined_without_namespace_is_just_the_name():
    assert Identity.joined("", "cmdline").display == "cmdline"


def test_multi_segment_namespace():
    ident = Identity.joined("mcpplibs.capi", "lua")
    assert ident.slug == "mcpplibs.capi.lua"


def test_slug_disambiguation_never_touches_install_ref():
    ident = Identity.plain("", "widget").with_slug("alpha.widget")
    assert ident.slug == "alpha.widget"
    assert ident.install_ref == "widget"        # the CLI still takes the short name


def test_display_parts_splits_prefix_for_rendering():
    assert Identity.joined("nlohmann", "json").display_parts == ("nlohmann.", "json")
    assert Identity.plain("", "gcc").display_parts == ("", "gcc")
