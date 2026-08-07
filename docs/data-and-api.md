# Data and API

**English** | [简体中文](zh/data-and-api.md)

Every build emits machine-readable documents alongside the pages. They are
shaped like API responses on purpose: when a server later replaces the static
build, it serves the same documents at the same URLs and every consumer keeps
working.

| URL | Contents |
|---|---|
| `/index.json` | Everything — schema 1 |
| `/packages/<slug>/index.json` | One package, the same object as in `packages[]` |
| `/search-index.json` | Small payload for the header search |
| `/packages.json` | Schema 0, kept one release cycle for existing consumers |
| `/sitemap.xml`, `/feed.xml` | All locales; the history line as an Atom feed |

They are written once, in the site's default locale.

## `/index.json`

```jsonc
{
  "schema": 1,
  "site":  { "title", "description", "github", "time"?, "commit"?, "commit_url"?, "generator"? },
  "index": { },                    // whatever a plugin put in IndexMeta
  "stats": { "packages", "namespaces", "versions" },
  "facets":  [ { "key", "label", "values": [ { "key", "label", "count", "tone" } ] } ],
  "growth":  [ { "date", "count", "added", "removed" } ],   // one point per day with activity
  "history": [ { "date", "at", "kind", "slug", "display", "by", "subject" } ],   // newest 200
  "guides":  [ { "slug", "title", "source" } ],
  "packages": [ /* see below */ ]
}
```

`site.time`, `site.commit` and `site.commit_url` are build provenance, present
when CI supplies them — see [Deployment](deployment.md).

`history[].kind` is `added`, `updated` or `removed`; `at` is the full ISO 8601
author timestamp and `date` is the day the growth curve groups by.

`growth[].count` is the number of packages in the index on that date; `added`
and `removed` are that day's movements. Only days with activity produce a
point.

### A package

```jsonc
{
  "id": "nlohmann.json",
  "namespace": "nlohmann",
  "namespace_effective": "nlohmann",   // falls back to the index default
  "namespace_implicit": false,         // true when the descriptor did not say
  "name": "json",
  "display": "nlohmann.json",
  "slug": "nlohmann.json",
  "install_ref": "nlohmann.json",
  "description": "...",
  "homepage": "...", "repo": "...", "docs": "...",
  "licenses": ["MIT"],
  "type": "package", "status": "",
  "latest": "3.12.0",
  "platforms": { "linux": { "versions": [...], "latest": "...", "deps": [...] } },
  "versions": [ { "version", "platforms": [...], "urls": { "GLOBAL": "..." }, "sha256" } ],
  "deps": [...], "required_by": [...],
  "facets": { "surface": "module header" },
  "people": {
    "upstream":   { "owner", "url", "avatar", "description", "stars", "host" },
    "descriptor": [ { "login", "name", "avatar", "url", "added" } ]
  },
  "history": [ { "date", "at", "clock", "kind", "by", "subject" } ],   // newest 12

  "extensions": { "mcpp": { } },       // plugin-owned, namespaced by plugin name
  "blocks": [ { "kind", "title", "data", "plugin", "collapsed", "weight" } ],
  "source_file": "pkgs/n/nlohmann.json.lua"
}
```

The three identity fields are separate on purpose and must not be derived from
one another — `display` is for humans, `slug` is the URL, `install_ref` is what
the client CLI accepts. See
[Architecture](architecture.md#identity-and-slugs).

`facets` values are whitespace-separated: `"module header"` means the package
belongs under both values of the `surface` axis.

`extensions` is where a plugin's own data lives, namespaced by plugin name. It
travels verbatim, which is what makes a plugin's work available to anything
that reads the JSON, not only to the site.

### Stability

Schema 1 promises: the keys above, their types, and directory-shaped URLs. Two
consequences worth stating:

- Per-locale text is flattened to the default language here. A label is always
  a string.
- New keys may appear. Read defensively; do not assume the set is closed.

`/packages.json` is the pre-redesign shape. It is kept so the day the new site
ships nothing that consumed the old one breaks, and it is the one document with
an expiry date on it.

## `/search-index.json`

Deliberately small — the header search fetches it on first keystroke:

```jsonc
[ { "s": "slug", "d": "display", "n": "name", "ns": "namespace",
    "t": "description, 160 chars", "f": { facets }, "v": "latest" } ]
```

## `/feed.xml`

The history line as Atom: the newest 40 events, each linking to the package
page. It is how someone follows an index without watching the repository.
