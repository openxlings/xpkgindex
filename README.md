# xpkgindex

A static site framework for package indexes. The core knows what a *package
index* is — identities, versions, platforms, mirrors, history, contributors —
and nothing about any particular package manager. Everything ecosystem-specific
lives in a plugin owned by the index repository itself.

```bash
pip install xpkgindex
xpkgindex generate . --output site      # build
xpkgindex serve . --port 8000           # build, then serve for review
```

The output is a plain directory of HTML and JSON. It deploys to GitHub Pages
as-is, and the JSON is shaped like an API response so a server can take over
later without changing a single URL.

---

## What it produces

| Path | Contents |
|---|---|
| `/` | Hero · growth curve · history line · faceted package listing |
| `/packages/<id>/` | Detail: how to use it, build semantics, versions, mirrors, people, history |
| `/packages/<id>/index.json` | The same package as data |
| `/stats/` | Growth over time, composition, full history line |
| `/contributors/` | Index contributors · upstream thanks · ecosystem union |
| `/guides/<slug>/` | The repo's own markdown docs, rendered in place |
| `/index.json` | Everything (schema 1) — the API contract |
| `/search-index.json`, `/sitemap.xml`, `/feed.xml` | Search payload, sitemap, Atom feed |

Package URLs are directories, not `<name>.html`: that is the shape a server
route can adopt unchanged, and it leaves room for sub-pages later.

---

## Used by

Two live indexes drive the design, and they disagree with each other in ways
that keep the core honest.

### [`mcpplibs/mcpp-index`](https://github.com/mcpplibs/mcpp-index) — 81 packages

Modular C++23 packages for the [mcpp](https://github.com/mcpp-community/mcpp)
build tool. Its plugin (`.xpkgindex/plugins/mcpp.py`):

- **Namespaces are part of the identity.** mcpp resolves `nlohmann.json`, so
  the plugin returns `Identity.joined(...)`. Without it the site advertised
  `mcpp add json@3.12.0`, which the client rejects, and three different
  `imgui` packages collapsed onto one page.
- **Classifies packages by how you consume them** — `import` (7), `#include`
  (55), a tool binary (1), or an upstream-provided `mcpp.toml` (18). That axis
  comes from the `mcpp = {}` extension block and is what a C++ user actually
  browses by.
- **Reads `mcpp = {}`** into build-semantics blocks: modules, targets,
  language, `import_std`, sources, features, generated files.
- **Links each package to the test project that uses it.** The repo is also an
  mcpp workspace whose members are per-library test projects, so the usage
  snippet on a package page is code CI compiles and runs, not something
  written for the website.

### [`openxlings/xim-pkgindex`](https://github.com/openxlings/xim-pkgindex) — 155 packages

The official index for the [xlings](https://github.com/openxlings/xlings)
package manager. Its plugin (`.xpkgindex/plugins/xim.py`) inverts two mcpp
assumptions, which is precisely why both consumers exist:

- **Namespaces are labels, not identity.** xlings resolves
  `[index:]name[@version]` against the *index repo*, so a descriptor's
  `namespace` (`config`, `xim`) must stay out of the install command. The
  plugin returns `Identity.plain(...)`.
- **xvm, programs and archs are xlings concepts**, rendered by the plugin
  rather than the core. They used to live in the core model, where they leaked
  onto mcpp pages as a meaningless "XVM Managed: No".
- Facets come from the fields this index actually populates: kind, category,
  status.

The two sites also look different: `theme.accent` and `theme.tones` re-tone the
whole design system from `.xpkgindex.json` — no fork, no CSS edit.

---

## Configuration

`.xpkgindex.json` at the index repo root:

```jsonc
{
  "site":  { "title": "…", "description": "…", "logo": "…" },
  "links": { "github": "…", "custom": [{ "label": "…", "url": "…" }] },
  "about": { "project_name": "…", "project_url": "…", "license": "…" },

  "theme": {
    "accent": "#5b46d6",
    "style":  "auto",                       // auto | light | dark
    "tones":  { "module": "…", "header": "…", "tool": "…" },
    "dark":   { "accent": "#9b8bfa", "tones": {} }
  },

  "pkgs_dir": "pkgs",
  "base_url": "https://example.github.io/index",
  "install_command_template": "mcpp add {ref}@{version}",

  "install": {
    "primary": { "label": "Install mcpp", "command": "xlings install mcpp -y" },
    "summary": "Don't have xlings yet?",
    "os": [                                 // auto-selected by the visitor's platform
      { "id": "unix",    "os": "Linux / macOS",        "command": "…" },
      { "id": "windows", "os": "Windows · PowerShell", "command": "…" }
    ]
  },

  "plugins": [".xpkgindex/plugins/mcpp.py"],

  "guides": {
    "nav_label": "Contribute",
    "entries": [{ "slug": "contributing", "title": "Adding a package",
                  "path": "docs/README.md",
                  "translations": { "zh": "docs/zh/README.md" } }]
  },

  "ecosystem": {
    "owners": ["mcpplibs"],                 // your own orgs — excluded from "upstream thanks"
    "repos":  ["mcpp-community/mcpp"]       // union for "ecosystem contributors"
  }
}
```

`install_command_template` placeholders: `{ref}` (what the CLI accepts),
`{name}`, `{namespace}`, `{display}`, `{version}`.

Guides render the repository's existing markdown rather than a copy, so the
site cannot drift from the docs. Install commands are all rendered into the
HTML and the matching one is selected client-side, so a JS-less visitor still
sees every platform.

Older configs keep working: `primary_color`, `install_commands`,
`install.fallback.commands` and `{name}` in the template are all still honoured.

---

## Writing a plugin

A plugin is a Python file in the index repo. The build already executes that
repo's own `.lua` descriptors in its own workflow, so executing its Python adds
no new trust boundary. `pip` entry points (group `xpkgindex.plugins`) work too,
for plugins you want to distribute.

```python
from xpkgindex.models import Block, Facet, FacetValue, Identity
from xpkgindex.plugins import Plugin

class MyPlugin(Plugin):
    api_version = 1
    name = "my-ecosystem"

    def on_index(self, ctx):             ...  # repo-level config → ctx.meta
    def identity(self, raw, path):       ...  # canonical id / slug / install ref
    def on_package(self, pkg, raw):      ...  # extensions, facets, deps
    def facets(self):                    ...  # declare facet axes
    def detail_blocks(self, pkg):        ...  # structured detail-page content
    def row(self, pkg):                  ...  # how the listing row reads
    def enrich_remote(self, pkgs, http): ...  # optional, must be skippable
```

The listing row is a `RowSpec`, not a fixed template — what belongs on the
densest surface of the site differs per ecosystem (mcpp leads with the line
you write, xlings with the binary you get):

```python
RowSpec(variant="",                 # "" = site default; else code | card
        tone="module",              # colours the pill and the strip
        lead="import",              # the labelled type pill
        code="import nlohmann.json;",   # how you consume it
        code_muted=False,               # True when `code` is a placeholder
        install="mcpp add nlohmann.json@3.12.0",   # how you add it
        badges=["✓ example"])
```

`code` and `install` answer two different questions and always land in the
same place, so a reader does not have to re-parse each row:

**`code` variant** — three lines, used by `mcpp-index`:

```
// nlohmann.json 3.12.0 — JSON for Modern C++
import nlohmann.json;                              ← how you consume it
mcpp add nlohmann.json@3.12.0   MIT · 3 platforms  ← click the command to copy
```

When a descriptor never names its module or header, line 2 still appears as a
muted `import …;` / `#include <…>` — the shape without an invented identifier,
so the rhythm holds and no row claims something untrue.

**`card` variant** — used by `xim-pkgindex`, where "what do I type to get it"
is the whole question:

```
gcc  15.1.0  [package]                    GPL · 3 platforms · xvm
The GNU Compiler Collection
┌────────────────────────────────────────────────────┐
│ xlings install gcc@15.1.0            $ gcc         │  ← click to copy
└────────────────────────────────────────────────────┘
```

`"list": {"variant": "card"}` sets the default site-wide; a plugin's
`RowSpec.variant` overrides it per package. Return `None` from `row()` to take
the default entirely. Type is signalled by a *labelled* pill plus a tinted
strip rather than a colour bar, so it still reads for anyone who cannot
separate the hues.

**Plugins return data, not HTML.** A `Block` (`kv` / `code` / `table` / `list`
/ `callout`) is rendered by the core's design system and travels verbatim into
`index.json`, so consumer sites stay visually consistent and a future API
carries the same fields. When a block genuinely needs its own markup, set
`template` and `styles` explicitly — the escape hatch is deliberate and its CSS
is scoped to that plugin.

Mark the one line a user writes to consume a package with
`data["role"] = "interface"`; it becomes the headline of the listing row and
the top of the detail page.

`on_index` should set `default_namespace`: a descriptor that omits `namespace`
is not un-namespaced, it belongs to the index's default one, and grouping it
under "—" invents a bucket that does not exist.

---

## Failure model

Data-correctness problems fail the build. External-dependency problems degrade.

| Situation | Result |
|---|---|
| Two packages resolve to the same slug | **build fails**, naming both descriptors |
| Growth curve disagrees with the tree | **build fails** (warning if the tree is dirty; `--strict` forces) |
| Plugin raises, fails to load, or targets another `api_version` | warning; that plugin's contribution is dropped |
| A descriptor fails to parse | warning; that package is skipped |
| No GitHub token / rate limited / offline | committed cache is used; missing sections omitted |
| Shallow clone | growth, history and contributors skipped |
| A guide's markdown is missing | warning; that guide is skipped |

The first two rules exist because both bugs shipped: three `imgui` packages
once collapsed onto one page, and counting only additions reported 86 packages
for a tree holding 81.

---

## Descriptor parsing

Descriptors execute in a sandboxed Lua runtime kept in lockstep with
[`libxpkg`](https://github.com/mcpplibs/libxpkg), the C++23 reference
implementation of the xpkg spec — specifically its `register_loader_sandbox`.
Parity is the point: a more permissive sandbox would advertise packages the
toolchain cannot load; a stricter one would silently drop valid ones.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

Apache-2.0
