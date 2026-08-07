# Theming

**English** | [简体中文](zh/theming.md)

Three layers, in increasing order of how much you take on:

1. **Tokens** — `theme` in `.xpkgindex.json`. Colours only, no CSS.
2. **Structure** — the listing variant and what a plugin puts in a row.
3. **Templates** — `Block.template` / `RowSpec.styles`, the declared escape
   hatch, for the case the first two genuinely cannot express.

Most indexes never leave layer 1.

## Tokens

`theme` is compiled into `static/css/theme.css`, which loads after
`site.css`, so it overrides without touching the framework's stylesheet. Only
what you configure is emitted — everything else keeps its built-in value,
including the dark-mode adjustments.

```jsonc
"theme": {
  "accent": "#5b46d6",
  "style":  "auto",
  "tones":  { "module": "#5b46d6", "header": "#52606d", "tool": "#b8690f" },
  "dark":   { "accent": "#9b8bfa",
              "tones": { "module": "#9b8bfa", "header": "#a7b6c7", "tool": "#e0a260" } },
  "transition": { "duration": "2s", "easing": "cubic-bezier(.45, .05, .25, 1)" }
}
```

### The tokens that exist

| Group | Tokens |
|---|---|
| Surfaces | `--bg`, `--bg-sunken`, `--bg-raised`, `--bg-code` |
| Lines | `--line`, `--line-soft` |
| Text | `--ink`, `--ink-2`, `--ink-3`, `--ink-4` |
| Semantic | `--tone-accent`, `--tone-module`, `--tone-header`, `--tool`, `--tone-neutral` |
| Chart | `--series-1`, `--series-2`, `--series-3` |
| Geometry | `--radius`, `--radius-sm`, `--gap`, `--maxw`, `--shadow` |

`theme.accent` sets `--tone-accent`; every key under `theme.tones` sets
`--tone-<key>`. That is how a plugin's `tone="module"` on a `RowSpec` or a
`FacetValue` becomes a colour without the plugin knowing any colours.

A tone is a *name for a meaning*, not a decoration: the same tone marks a
package's row, its type pill and its growth-chart line, so those three agree
by construction.

### Light, dark, and the switch

`style` is `auto` (follow the OS), `light` or `dark`. A visitor's explicit
choice is remembered and wins over the OS from then on; the choice is applied
in a small script in `<head>`, before first paint, so the page never flashes
the wrong theme.

The switch itself cross-fades:

```jsonc
"transition": { "duration": "2s", "easing": "cubic-bezier(.45, .05, .25, 1)" }
```

`"0s"` switches instantly, which is also what a visitor with
`prefers-reduced-motion` always gets.

How it works is worth knowing, because the obvious implementation does not
survive a real listing. A `transition` on `*` puts an animation on every
element and pseudo-element — tens of thousands of them on a page of a few
hundred packages — and the switch stutters at around 20fps. Instead:

- Where the browser supports **view transitions**, the switch is a compositor
  cross-fade of two snapshots. Its cost does not depend on how big the page
  is; measured at a flat 60fps on the same listing. Because the page on screen
  is a still image while it runs, the first scroll, tap or keypress ends the
  fade at once.
- Everywhere else, the **colour tokens themselves** are interpolated. They are
  registered with `@property` as `<color>` precisely so they can be — an
  unregistered custom property jumps from one value to the next. That is one
  transition on `<html>` rather than thousands, and it is attached only while
  the switch is running.

## Listing variants

The listing row is where ecosystems disagree most, so it is data, not markup.
Two layouts ship:

**`code`** — three lines, each with a fixed meaning:

```
// nlohmann.json 3.12.0 — JSON for Modern C++
import nlohmann.json;
mcpp add nlohmann.json@3.12.0          MIT · 3 platforms · ✓ example
```

**`card`** — name and metadata on the header line, one copyable command in a
tinted strip:

```
gcc 15.1.0   tool   GPL-3.0 · 2 platforms · xvm
The GNU Compiler Collection
xlings install gcc@15.1.0                                    $ gcc
```

Set the default with `list.variant`; a plugin overrides it per package with
`RowSpec.variant`. Whichever you pick, the row keeps three lines at every
screen width — anything that does not fit truncates with an ellipsis rather
than wrapping, because a row that becomes four lines on a phone breaks the
scan pattern the listing is built on.

## Density and width

`--maxw` (default `1140px`) sets the content width; `--gap` and the two radius
tokens carry most of the rest of the feel. Overriding them in
`theme.tones` is not possible — they are geometry, not colour — so an index
that wants a different width ships a small CSS file of its own alongside the
generated one, or uses the template escape hatch.

## The escape hatch

`Block.template` and `RowSpec.template` / `RowSpec.styles` let a plugin supply
its own markup for one block or one row. They exist so that "the five block
kinds cannot express this" has an answer that is visible in the plugin rather
than smuggled in as an HTML string inside a caption.

Using them costs you the guarantee that every consumer site looks like one
system, so reach for them last.
