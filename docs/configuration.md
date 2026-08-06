# Configuration

**English** | [简体中文](zh/configuration.md)

Everything lives in `.xpkgindex.json` at the index repository root. Every key is
optional. Any string an index supplies here may also be written as a per-locale
map — see [Internationalisation](i18n.md).

```jsonc
{
  "site":  { "title": "…", "description": "…", "logo": "…" },
  "links": { "github": "…", "website": "…", "forum": "…", "docs": "…",
             "custom": [{ "label": "…", "url": "…" }] },
  "about": { "project_name": "…", "project_url": "…", "description": "…",
             "maintainers": ["…"], "license": "Apache-2.0" },

  "theme": {
    "accent": "#5b46d6",
    "style":  "auto",
    "tones":  { "module": "…", "header": "…", "tool": "…", "neutral": "…" },
    "dark":   { "accent": "#9b8bfa", "tones": { } },
    "transition": { "duration": "2s", "easing": "cubic-bezier(.45, .05, .25, 1)" }
  },

  "pkgs_dir": "pkgs",
  "base_url": "https://example.github.io/index",
  "languages": ["en", "zh", "zh-Hant"],
  "install_command_template": "mcpp add {ref}@{version}",
  "list": { "variant": "code" },

  "install": {
    "primary": { "label": "Install mcpp", "command": "xlings install mcpp -y" },
    "summary": "Don't have xlings yet?",
    "os": [
      { "id": "unix",    "os": "Linux / macOS",        "command": "…" },
      { "id": "windows", "os": "Windows · PowerShell", "command": "…" }
    ]
  },

  "growth": {
    "total_label": "all packages",
    "series": [{ "label": "import", "facet": "surface", "value": "module", "tone": "module" }]
  },

  "plugins": [".xpkgindex/plugins/mcpp.py"],

  "docs": {
    "nav_label": "Docs",
    "landing": "quick-start",
    "entries": [{ "slug": "quick-start", "title": "Quick start",
                  "path": "docs/quick-start.md",
                  "translations": { "zh": "docs/zh/quick-start.md" } }],
    "cta": { "eyebrow": "New here?", "title": "Quick start",
             "description": "…", "lines": ["…"], "action": "Read the guide" }
  },

  "ecosystem": { "owners": ["mcpplibs"], "repos": ["mcpp-community/mcpp"] },

  "identities": ".xpkgindex/identities.json",
  "cache": ".xpkgindex/cache/github.json"
}
```

## `site`

| Key | Default | Notes |
|---|---|---|
| `title` | `Package Index` | Page titles, hero heading, footer |
| `description` | — | Hero lede, `<meta name=description>`, feed subtitle |
| `logo` | `Package Index` | The wordmark in the header |

## `links`

Each produces one icon in the header; omit a key and its icon is not rendered.

| Key | Icon | Meaning |
|---|---|---|
| `github` | mark | This index's repository. Also parsed for `owner/name`, which the contributor lookup needs |
| `website` | globe | The *project's* own site — not this index |
| `forum` | speech bubble | Community forum |
| `docs` | book | External documentation |
| `custom` | — | Extra text links, rendered in the footer |

## `about`

Fills the About page: `project_name`, `project_url`, `description`,
`maintainers` (list), `license`.

## `theme`

| Key | Default | Notes |
|---|---|---|
| `accent` | built-in | Primary accent. Legacy spelling `primary_color` still works |
| `style` | `auto` | `auto` follows the OS; `light` / `dark` pin it |
| `tones` | `{}` | Semantic colour tokens: `module`, `header`, `tool`, `neutral`, … A `RowSpec.tone` or `FacetValue.tone` names one of these |
| `dark` | `{}` | `{ "accent": …, "tones": { … } }`, applied under `[data-theme=dark]` |
| `transition.duration` | `2s` | Day/night cross-fade. `0s` switches instantly |
| `transition.easing` | `cubic-bezier(.45, .05, .25, 1)` | Any CSS timing function |

See [Theming](theming.md) for the full token list and how the switch is
implemented.

## Build

| Key | Default | Notes |
|---|---|---|
| `pkgs_dir` | `pkgs` | Where descriptors live, relative to the repo root |
| `base_url` | — | Absolute URL, used by `sitemap.xml` and `feed.xml`. `--base-url` overrides |
| `languages` | `["en"]` | UI locales. The first is the default and lives at the root |
| `install_command_template` | `{ref}@{version}` | Placeholders: `{ref}`, `{name}`, `{namespace}`, `{display}`, `{version}` |
| `list.variant` | `code` | `code` or `card`; a plugin may override it per package |
| `plugins` | `[]` | Repo-relative `.py` paths, or entry-point names in group `xpkgindex.plugins` |
| `identities` | `.xpkgindex/identities.json` | Manual contributor merges |
| `cache` | `.xpkgindex/cache/github.json` | Committed network cache |

`{ref}` is `Identity.install_ref` — what the client CLI actually accepts. It is
deliberately not the same field as the display name; see
[Architecture](architecture.md#identity-and-slugs).

## `install`

The homepage install block. Every platform's command is rendered into the HTML
and the matching one is revealed client-side, so a visitor without JavaScript
still sees them all.

| Key | Notes |
|---|---|
| `primary.label`, `primary.command` | The headline command |
| `summary` | Label of the disclosure holding the per-OS commands |
| `os[]` | `{ id, os, command }`. `id` is matched against the detected platform: `unix`, `linux`, `macos`, `windows` |

With no `primary.command`, the per-OS list is shown directly instead of behind
a disclosure. The older spellings `install_commands` and
`install.fallback.commands` still work.

## `growth`

The homepage and stats curve. The total is always drawn; `series` adds lines.

| Key | Notes |
|---|---|
| `total_label` | Legend label for the total line |
| `series[].label` | Legend label |
| `series[].facet`, `series[].value` | Which packages count toward this line |
| `series[].tone` | A theme tone name for the line colour; a tone identical to the accent falls back to the palette so two lines never share a colour |

A series is computed from the same daily snapshots as the total, so a line can
answer "how many of these did we have last March", not just today.

## `docs`

Renders the repository's existing markdown as site pages — no second copy to
drift.

| Key | Notes |
|---|---|
| `nav_label` | Name of the section in the nav. A string, a per-locale map, or omitted to use the framework's translated label |
| `landing` | Slug of the doc the nav item and the homepage card point at |
| `entries[]` | `{ slug, title, path, translations }` |
| `entries[].translations` | `{ locale: path }` — the body follows the header's language switcher |
| `cta` | The homepage card: `eyebrow`, `title`, `description`, `lines[]`, `action` |

A doc's own `# H1` becomes the page heading and is removed from the body, so it
is never printed twice. `title` names it in the navigation; see
[Internationalisation](i18n.md#documents) for how the two interact across
locales. The older key `guides` is still accepted as a synonym for `docs`.

## `ecosystem`

| Key | Notes |
|---|---|
| `owners` | Your own orgs and accounts. Excluded from "upstream thanks" — you are not a third party to yourself |
| `repos` | Extra repositories whose contributors count as part of the ecosystem |
