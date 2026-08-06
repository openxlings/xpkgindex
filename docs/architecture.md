# Architecture

**English** | [简体中文](zh/architecture.md)

A build is one function — `build(root)` → `SiteData` — followed by one
renderer per locale. This document is the order it runs in and the reasoning
behind the parts that are not obvious.

```
descriptors ─▶ identities ─▶ plugins ─▶ remote enrichment ─▶ facets/blocks/rows
                                                                    │
git history ──▶ growth · history · contributors ────────────────────┤
GitHub cache ─▶ upstream projects · logins · ecosystem ─────────────┤
your markdown ─▶ guides ────────────────────────────────────────────┤
                                                                    ▼
                                                  SiteData ─▶ one site per locale
```

## Reading descriptors

`readers/xpkg_lua.py` executes each `pkgs/**/*.lua` in a Lua sandbox and takes
the `package` table out of it.

The sandbox is kept **in lockstep with `libxpkg`'s `register_loader_sandbox`**,
which is the reference implementation the actual package manager uses. Same
globals, same stubs, same `import()` behaviour. This is a design rule, not an
accident: a descriptor that loads in one and not the other means the website
and the client disagree about what the index contains, and a website that
quietly parses more than the client does is worse than one that parses less.

A descriptor that fails to parse is a warning, and the build continues. No
descriptors at all is an error.

## Identity and slugs

Three fields, never derived from one another:

| Field | Is | Wrong value looks like |
|---|---|---|
| `display` | What a human reads | cosmetic |
| `slug` | The URL segment | one package's page overwrites another's |
| `install_ref` | What the client CLI accepts | a copy-paste command that fails |

The core defaults to `Identity.plain`: the namespace is metadata, and all three
are the bare name. A plugin opts into `Identity.joined` explicitly.

This split exists because the two live indexes genuinely disagree. mcpp treats
the namespace as part of the identity — you type `mcpp add nlohmann.json`.
xlings treats it as a classification label and resolves a name against the
*index repository*, so `xlings install xim.gcc` is not a thing. A core that
joined namespaces "helpfully" would break the second; a core that never joined
would break the first's URLs.

After identities are assigned, `_check_slugs` runs. A duplicate aborts the
build with the colliding descriptors named. It is the only hard failure in the
plugin path, and it is hard because the failure it prevents is silent: before
this framework, two packages sharing a short name produced one page and no
error.

## Plugins

Loaded from the config, then called in a fixed order — see
[Plugins](plugins.md). Two properties are worth restating here:

- Every hook is isolated. It raises, the core warns, drops that contribution
  and carries on.
- `enrich_remote` runs **before** facets, blocks and rows, so a plugin that
  resolves data from the network can still change how a package is classified.

## Growth, history and contributors

`data/git_history.py` replays the log of `pkgs/`:

```
git log --follow-less --name-status --format="C\t%H\t%aI\t%an\t%ae\t%s"
```

Additions, deletions and renames are applied in order, producing a set of live
descriptor paths after each commit and a daily snapshot of that set. From it:
the growth curve, the history line, and — because the snapshots are sets of
paths rather than counts — per-facet growth series computed after the fact.

**The replay verifies itself.** The set of paths at the end must equal the
`.lua` files actually on disk. If it does not, the curve is lying about
something, and the build says so: an error when the working tree is clean (or
under `--strict`), a warning when it is dirty, because uncommitted local edits
legitimately explain a mismatch.

### Who is one person

`data/identities.py` merges git authors by login, email and name with a
union-find, folds in the GitHub commits API's author→login map when a token is
available, filters bots, and applies `.xpkgindex/identities.json` for the cases
automation cannot resolve. A `Person` keeps every name it merged, which is what
lets "who added this package" match a person who has committed under three
spellings of their own name.

## The network, and doing without it

`data/github.py` is a small cache with a committed JSON file behind it
(`.xpkgindex/cache/github.json`). It stores **projected fields only** — the
handful of values the site renders — not raw API responses.

- `--offline` never touches the network and uses the cache as-is.
- `--refresh` re-fetches everything, ignoring freshness. Run it deliberately
  and commit the result.
- Otherwise entries refresh when stale.

Every fetch returns `None` on failure instead of raising. A rate-limited or
disconnected build produces a complete site with less decoration, which is the
right trade for a site that has to build in CI on every merge.

Plugins get the same cache handed to `enrich_remote`. Cache facts, not
conclusions: a cached "this is a modular package" freezes today's rule into
last month's data, while a cached module name lets the rule change and be
recomputed offline.

## Guides

`guides.py` renders the repository's existing markdown — the config points at
files that already exist, so the site cannot drift from the docs. Raw HTML is
allowed (these documents are written to render on GitHub too, where
`<details>` is idiomatic); the trust level is the same as the repo's `.lua`
descriptors and its plugin, both of which the build already executes.

## Rendering

`render.py` produces one complete static site per configured locale — the
default at the root, the rest under `/<tag>/`. URLs are directory-shaped
(`/packages/<slug>/`) because that is the form a server route can adopt
unchanged.

Two things are generated rather than static: `theme.css`, from the config's
tokens, and a content hash appended to the CSS and JS URLs. The hash is not
premature optimisation — a stale cached stylesheet made a working feature look
broken twice during development.

`serialize.py` is the boundary between data and rendering: everything the site
knows goes through it into `index.json`, so the JSON cannot quietly fall behind
the pages.
