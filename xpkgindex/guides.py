"""Render the index repo's own markdown docs as site pages.

Guides are not authored here: a repo that already documents how to contribute
should not have to keep a second copy in sync. The config points at existing
files and this module renders them with anchors, a table of contents and
language switching.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from markdown_it import MarkdownIt

_SLUG_STRIP = re.compile(r"[^\w一-鿿\- ]+")


def _anchor(text: str) -> str:
    s = _SLUG_STRIP.sub("", text).strip().lower().replace(" ", "-")
    return s or "section"


def _render(text: str, base_dir: str, guide_slugs: Dict[str, str],
            depth: int) -> Dict[str, Any]:
    md = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table")
    tokens = md.parse(text)

    toc: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for i, tok in enumerate(tokens):
        if tok.type != "heading_open" or tok.tag not in ("h2", "h3"):
            continue
        inline = tokens[i + 1]
        title = inline.content.strip()
        base = _anchor(title)
        counts[base] = counts.get(base, 0) + 1
        anchor = base if counts[base] == 1 else f"{base}-{counts[base]}"
        tok.attrSet("id", anchor)
        toc.append({"level": int(tok.tag[1]), "title": title, "anchor": anchor})

    html = md.renderer.render(tokens, md.options, {})
    html = _rewrite_links(html, base_dir, guide_slugs, depth)
    return {"html": html, "toc": toc}


def _rewrite_links(html: str, base_dir: str, guide_slugs: Dict[str, str],
                   depth: int) -> str:
    """Point relative markdown links at the rendered guide, or at the repo."""
    up = "../" * depth

    def repl(match: re.Match) -> str:
        href = match.group(1)
        if href.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        target = os.path.normpath(os.path.join(base_dir, href.split("#")[0]))
        target = target.replace(os.sep, "/")
        slug = guide_slugs.get(target)
        if slug:
            frag = href.split("#", 1)[1] if "#" in href else ""
            return f'href="{up}guides/{slug}/{("#" + frag) if frag else ""}"'
        return match.group(0)

    return re.sub(r'href="([^"]+)"', repl, html)


def load(root: str, entries: List[Any]) -> (List[Dict[str, Any]], List[str]):
    """Render every configured guide (plus its translations)."""
    warnings: List[str] = []
    slug_by_path = {e.path.replace(os.sep, "/"): e.slug for e in entries}
    for e in entries:
        for path in e.translations.values():
            slug_by_path[path.replace(os.sep, "/")] = e.slug

    out: List[Dict[str, Any]] = []
    for entry in entries:
        full = os.path.join(root, entry.path)
        if not os.path.isfile(full):
            warnings.append(f"guide source missing: {entry.path}")
            continue
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        base_dir = os.path.dirname(entry.path)
        rendered = _render(text, base_dir, slug_by_path, depth=2)

        langs: Dict[str, Dict[str, Any]] = {}
        for lang, rel in (entry.translations or {}).items():
            lpath = os.path.join(root, rel)
            if not os.path.isfile(lpath):
                warnings.append(f"guide translation missing: {rel}")
                continue
            with open(lpath, "r", encoding="utf-8", errors="replace") as f:
                langs[lang] = _render(f.read(), os.path.dirname(rel), slug_by_path,
                                      depth=3)

        out.append({
            "slug": entry.slug,
            "title": entry.title,
            "source": entry.path,
            "html": rendered["html"],
            "toc": rendered["toc"],
            "translations": langs,
        })
    return out, warnings
