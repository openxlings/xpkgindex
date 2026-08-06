# Plugins

**English** | [简体中文](zh/plugins.md)

The core knows what a package index is. It does not know what a package
*means* in your ecosystem — whether the namespace is part of the name, what a
reader should type to use a library, which of a package's properties are worth
faceting. That is a plugin's job, and the plugin belongs to the index
repository, not to the framework.

```jsonc
"plugins": [".xpkgindex/plugins/mine.py"]
```

A repo-relative `.py` path is imported directly; any other string is looked up
as an entry point in the group `xpkgindex.plugins`. Every `Plugin` subclass in
the module is instantiated.

Executing the repo's own Python is no new risk: the build already executes the
repo's own `.lua` descriptors, in the repo's own workflow.

## Shape

```python
from xpkgindex.plugins import Plugin
from xpkgindex.models import Block, Facet, FacetValue, Identity, RowSpec


class MyPlugin(Plugin):
    api_version = 1
    name = "mine"          # namespaces pkg.extensions[name]

    def on_package(self, pkg, raw):
        pkg.facets["kind"] = raw.get("type", "library")
```

Every hook is optional and the defaults do nothing. `api_version` is checked at
load; a mismatch is a warning, and the plugin still loads.

## Hooks, in the order the build calls them

| Hook | When | Returns |
|---|---|---|
| `on_index(ctx)` | Once, before any package is read | — |
| `identity(raw, path)` | Per descriptor, before anything else about it | `Identity` or `None` |
| `on_package(pkg, raw)` | Per package, after it is parsed | — |
| `enrich_remote(packages, http)` | Once, after every package exists | — |
| `facets()` | Once, after enrichment | `list[Facet]` |
| `detail_blocks(pkg)` | Per package | `list[Block]` |
| `row(pkg)` | Per package | `RowSpec` or `None` |

The order matters in one place in particular: `enrich_remote` runs **before**
facets, blocks and rows. A plugin that resolves something it could not read
from the descriptor alone — an upstream manifest, say — must be able to change
how the package is classified and rendered, and it cannot once those are
computed.

### `on_index(ctx)`

Repo-level configuration: a workspace manifest, an index-wide TOML, a curated
overrides file.

```python
def on_index(self, ctx):
    text = ctx.read_text("mcpp.toml")        # None if absent
    ctx.meta.set("hero_stats", [{"label": "with examples", "value": 64}])
```

`ctx` gives you `root`, `path(*parts)`, `read_text(relative)`, the parsed
`config`, and `meta` — an `IndexMeta` whose fields land in `index.json` under
`index`, and whose `hero_stats` are rendered beside the core's counts.

### `identity(raw, path)`

The single most consequential hook. Three fields that must not be derived from
one another:

| Field | Is |
|---|---|
| `display` | What a human reads |
| `slug` | The URL segment, unique across the whole site |
| `install_ref` | What the client CLI actually accepts |

```python
def identity(self, raw, path):
    pkg = raw.get("package", {})
    return Identity.joined(pkg.get("namespace", ""), pkg.get("name", ""))
```

`Identity.plain(ns, name)` is the core default: the namespace is metadata, and
all three fields are the bare name. `Identity.joined(ns, name)` makes the
namespace part of the identity — `nlohmann.json` — in the display, the URL and
the install command alike.

The core will never join the namespace for you. mcpp wants
`mcpp add nlohmann.json`; xlings resolves a name against the *index repo* and
would reject `xlings install xim.gcc`. Guessing wrong produces install commands
that do not work, so the choice is explicit.

Two packages that end up with the same `slug` abort the build. It is the one
plugin-adjacent failure that is not a warning: a duplicate slug means one
package's page silently overwrites another's, which is the bug this framework
was built to remove.

### `on_package(pkg, raw)`

Populate `pkg.extensions[self.name]`, `pkg.facets`, `pkg.deps`. `raw` is the
descriptor exactly as the Lua sandbox produced it.

```python
def on_package(self, pkg, raw):
    ext = raw.get("package", {}).get("mine", {})
    pkg.extensions["mine"] = {"programs": ext.get("programs", [])}
    pkg.facets["kind"] = "tool" if ext.get("programs") else "library"
```

Facet values are matched by the client-side filter as whitespace-separated
tokens, so `pkg.facets["surface"] = "module header"` puts one package under
both values of that axis.

### `enrich_remote(packages, http)`

Build-time enrichment from the network. `http` is the shared cache:

```python
def enrich_remote(self, packages, http):
    for pkg in packages:
        data = http.get_text(url, project="manifest")   # None when offline
        if data:
            pkg.extensions["mine"]["upstream"] = parse(data)
```

Both `get(url, project)` (JSON) and `get_text(url, project)` return `None`
rather than raising when the network is unavailable, when `--offline` is set,
or when the request fails. `project` groups entries in the committed cache.

Cache **facts, not conclusions**. Storing "this package is modular" means
changing that rule later requires a network refresh of every package; storing
the module name it declared means the rule can be recomputed offline, at any
time.

### `facets()`

Declare the axes. Counts are filled in by the core.

```python
def facets(self):
    return [Facet(key="kind", label="how you use it", weight=10, values=[
        FacetValue(key="tool", label="tool", tone="tool"),
        FacetValue(key="library", label="library", tone="module"),
    ])]
```

`weight` orders the axes; `tone` names a theme colour token. Values you do not
declare are still discovered from the packages and appended.

### `detail_blocks(pkg)`

Structured content for the package page. Never HTML — a block travels verbatim
into `index.json`, and every consumer site keeps one visual system.

| `kind` | `data` |
|---|---|
| `kv` | `{"items": [{"key", "value", "mono"?}]}` |
| `code` | `{"code", "caption"?, "source"?}` |
| `table` | `{"head": [...], "rows": [[...]]}` |
| `list` | `{"items": [...]}` |
| `callout` | `{"text"}` |

```python
Block(kind="kv", title="Build", weight=30, collapsed=False,
      data={"items": [{"key": "modules", "value": "asio", "mono": True}]})
```

`weight` orders blocks; `collapsed` renders it behind a disclosure. A block
with `data["role"] == "interface"` is lifted out of the flow and rendered as
the page's headline usage line.

If a block genuinely cannot be expressed in those five kinds, `template` and
`styles` are the declared escape hatch — an explicit admission rather than an
HTML string smuggled through a caption.

### `row(pkg)`

The listing row, the densest and most-read surface on the site.

```python
def row(self, pkg):
    return RowSpec(variant="code", tone="module",
                   lead="import", code="import asio;",
                   install="mcpp add chriskohlhoff.asio@1.34.2",
                   badges=["✓ example"])
```

Two layouts ship. `code` is three lines with fixed meanings — the name as a
comment, how you consume it, how you add it — and mcpp-index uses it. `card`
leads with the name and metadata and ends in one copyable command, which suits
an index of tools; xim-pkgindex uses it. Returning `None` takes the site
default from `list.variant`.

`code_muted=True` marks the consumption line as a placeholder rather than a
fact — the shape of what you would write, on a package whose descriptor never
names a module or header. Do not invent identifiers: a wrong `#include` on a
package page is worse than none.

## Text in the reader's language

Any string a plugin produces — facet labels, block titles, badges, notes — may
be a per-locale map instead of a string:

```python
Facet(key="kind", label={"en": "how you use it", "zh": "怎么用"})
```

Identifiers should stay untranslated. See [Internationalisation](i18n.md).

## When a hook raises

The core logs a warning, drops that hook's contribution for that call, and
keeps building. A plugin bug degrades the page it touched; it does not take the
site down. Warnings are printed by `generate` and collected in
`site.warnings`; `--strict` is about growth reconciliation, not about plugin
failures.

The exception, again, is a duplicate slug: that aborts.

## Worked examples

Both live indexes ship a plugin worth reading:

- [`mcpp-index/.xpkgindex/plugins/mcpp.py`](https://github.com/mcpplibs/mcpp-index/blob/main/.xpkgindex/plugins/mcpp.py)
  — joined identities, upstream `mcpp.toml` enrichment, module names read from
  `export module` declarations, usage snippets taken from the repository's own
  test projects.
- [`xim-pkgindex/.xpkgindex/plugins/xim.py`](https://github.com/openxlings/xim-pkgindex/blob/main/.xpkgindex/plugins/xim.py)
  — plain identities, xvm/programs/architectures as facets and blocks, the
  card row variant.
