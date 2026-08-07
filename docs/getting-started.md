# Getting started

**English** | [简体中文](zh/getting-started.md)

## Requirements

Python 3.9 or newer. Three dependencies, installed with the package: `jinja2`
(templates), `lupa` (the descriptor sandbox), `markdown-it-py` (your docs).

```bash
pip install xpkgindex
# or, until it is on PyPI for your platform:
pip install git+https://github.com/openxlings/xpkgindex.git
```

## What the framework expects to find

```
your-index/
├── pkgs/                     # descriptors — any nesting, *.lua
│   └── n/nlohmann.json.lua
├── .xpkgindex.json           # site configuration (optional but expected)
├── .xpkgindex/
│   ├── plugins/yours.py      # your ecosystem's semantics (optional)
│   ├── identities.json       # manual contributor merges (optional)
│   └── cache/github.json     # committed network cache (generated)
└── docs/*.md                 # your existing docs, rendered as site pages
```

Only `pkgs/` is required — a build with no configuration at all produces a
working, if anonymous, site. `pkgs_dir` moves the directory if yours is called
something else.

## First build

```bash
xpkgindex generate .              # writes ./site
xpkgindex serve . --port 8000     # builds, then serves it for review
```

`generate` prints what it produced and any warnings:

```
generated 81 packages -> site
  16 namespaces, 119 versions, 2 facet axes, 8 contributors
```

### Flags

| Flag | Effect |
|---|---|
| `--output`, `-o` | Output directory (default `site`) |
| `--config`, `-c` | Explicit path to `.xpkgindex.json` |
| `--offline` | Never touch the network; use the committed cache only |
| `--strict` | Treat reconciliation warnings as errors — use in CI |
| `--refresh` | Re-fetch every cached upstream lookup, ignoring freshness |
| `--base-url` | Absolute base URL for `sitemap.xml` and `feed.xml` |
| `--url-style` | `directory` (default) or `file` — see [Deployment](deployment.md#a-host-that-does-not-resolve-directories) |
| `--port` | `serve` only (default 8000) |

Warnings are not failures. A descriptor that will not parse, a missing guide
file, a plugin hook that raised — the build says so and carries on. Two things
do abort it: no packages parsed at all, and two packages claiming the same URL
(see [Architecture](architecture.md#identity-and-slugs)).

## What comes out

```
site/
├── index.html                     # listing, growth curve, history
├── packages/<slug>/index.html     # one page per package
├── packages/<slug>/index.json     # the same package as data
├── packages/<short>.html          # alias/disambiguation for older links
├── stats/, contributors/, about/
├── docs/<slug>/                   # your markdown, rendered
├── index.json                     # everything (schema 1)
├── search-index.json, sitemap.xml, feed.xml
├── static/                        # css, js, generated theme.css
└── zh/, zh-Hant/                  # further locales, if configured
```

Package URLs are directories rather than `<name>.html` so a server route can
adopt them unchanged later, and so sub-pages don't need another migration.

## What to commit

Commit `.xpkgindex/cache/github.json`. It holds only projected fields —
avatars, logins, descriptions, star counts — and committing it means CI builds
are reproducible, fast, and survive an unauthenticated rate limit. Refresh it
deliberately (`--refresh`), not on every build.

Do not commit `site/`. It is a build product; CI publishes it.

## Next

- [Configuration](configuration.md) — name the site, theme it, wire up install commands
- [Plugins](plugins.md) — when the core has no word for something your ecosystem cares about
- [Deployment](deployment.md) — GitHub Pages in about twenty lines of workflow
