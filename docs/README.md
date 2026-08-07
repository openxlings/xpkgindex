# xpkgindex documentation

**English** | [简体中文](zh/README.md)

xpkgindex turns a directory of xpkg descriptors into a static website. The core
knows what a *package index* is — identities, versions, platforms, mirrors,
history, contributors. It knows nothing about any particular package manager;
that lives in a plugin owned by the index repository.

These documents describe the framework. If you maintain an index and want a
site, start with [Getting started](getting-started.md) and
[Configuration](configuration.md). If your ecosystem needs the site to say
things the core has no word for, read [Plugins](plugins.md).

## The documents

| Document | What it covers |
|---|---|
| [Getting started](getting-started.md) | Install, expected repository layout, first build, preview, what to commit |
| [Configuration](configuration.md) | Every `.xpkgindex.json` key, its default, and what it changes |
| [Plugins](plugins.md) | Plugin API v1 — hooks, call order, the data models, failure behaviour |
| [Theming](theming.md) | Design tokens, dark mode, listing variants, the template escape hatch |
| [Internationalisation](i18n.md) | UI locales, per-locale text, translated docs, language detection |
| [Data and API](data-and-api.md) | `index.json` schema 1 and the other machine-readable outputs |
| [Architecture](architecture.md) | How a build actually runs, stage by stage, and why in that order |
| [Deployment](deployment.md) | GitHub Pages, build provenance, the network cache, CI flags |

## Where things live

| Path | Responsibility |
|---|---|
| `xpkgindex/cli.py` | `generate` and `serve` |
| `xpkgindex/build.py` | The pipeline: descriptors → `SiteData` |
| `xpkgindex/config.py` | `.xpkgindex.json` → `SiteConfig` |
| `xpkgindex/models.py` | `Identity`, `Package`, `Block`, `RowSpec`, `Facet`, `Person`, … |
| `xpkgindex/readers/xpkg_lua.py` | The descriptor sandbox, kept in step with `libxpkg` |
| `xpkgindex/plugins/__init__.py` | Plugin base class, loading, per-hook isolation |
| `xpkgindex/data/` | git history replay, GitHub cache, identity merging |
| `xpkgindex/guides.py` | The repo's own markdown, rendered as site pages |
| `xpkgindex/charts.py` | The growth curve, drawn as inline SVG |
| `xpkgindex/render.py` | One locale's worth of pages |
| `xpkgindex/serialize.py` | The `index.json` contract |
| `xpkgindex/i18n.py` | Framework chrome catalogs and locale resolution |
| `xpkgindex/templates/`, `xpkgindex/static/` | Jinja templates, CSS and JS |

## Two working examples

The design is kept honest by two indexes that disagree with each other:

- [`mcpplibs/mcpp-index`](https://github.com/mcpplibs/mcpp-index) — mcpp treats
  the namespace as part of the identity (`nlohmann.json`), leads its rows with
  the line you write (`import nlohmann.json;`), and enriches packages from
  upstream `mcpp.toml` manifests.
- [`openxlings/xim-pkgindex`](https://github.com/openxlings/xim-pkgindex) —
  xlings treats the namespace as a *label* and resolves names against the index
  repo, so the namespace must never enter the install command. Rows lead with
  the binary you get (`$ gcc`).

Where a design decision looks arbitrary, it is usually the point where those
two ecosystems pulled in opposite directions.
