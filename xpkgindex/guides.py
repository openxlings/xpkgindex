"""Render the index repo's own markdown docs as site pages.

Guides are not authored here: a repo that already documents how to contribute
should not have to keep a second copy in sync. The config points at existing
files and this module renders them with anchors, a table of contents and
language switching.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Set

from markdown_it import MarkdownIt

_SLUG_STRIP = re.compile(r"[^\w一-鿿\- ]+")


def _anchor(text: str) -> str:
    s = _SLUG_STRIP.sub("", text).strip().lower().replace(" ", "-")
    return s or "section"


def _permalink(anchor: str):
    from markdown_it.token import Token
    tok = Token("html_inline", "", 0)
    tok.content = f'<a class="anchor" href="#{anchor}" aria-hidden="true">#</a>'
    return tok


def _strip_language_line(tokens: List[Any], base_dir: str, siblings: Set[str]) -> List[Any]:
    """Drop a hand-written "English | 简体中文" line from the top of a doc.

    These documents are written to read on GitHub too, where a manual link
    between translations is the only way to switch. On the site the header
    already has a language switcher that follows the whole page, so the line
    is a second, worse switcher pointing at raw `.md` files.

    The test is exact rather than a guess at what a language line looks like:
    the doc entry declares its own translations, so a leading paragraph whose
    links *all* point at another translation of this same document is one.
    """
    if len(tokens) < 3 or tokens[0].type != "paragraph_open":
        return tokens
    links = [child for child in (tokens[1].children or []) if child.type == "link_open"]
    if not links:
        return tokens
    for link in links:
        href = (link.attrGet("href") or "").split("#")[0]
        target = os.path.normpath(os.path.join(base_dir, href)).replace(os.sep, "/")
        if target not in siblings:
            return tokens
    return tokens[3:]


def _render(text: str, base_dir: str, guide_slugs: Dict[str, str],
            depth: int, siblings: Optional[Set[str]] = None) -> Dict[str, Any]:
    # Raw HTML is allowed: these documents belong to the index repository and
    # are written to render on GitHub too, where `<details>` disclosures are
    # idiomatic. Escaping them printed the tags as text. The trust level is
    # the same as the repo's `.lua` descriptors and its plugin — the build
    # already runs those.
    md = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable("table")
    tokens = md.parse(text)

    # The document's own H1 becomes the page title and is dropped from the
    # body: otherwise every guide renders its heading twice, and in the wrong
    # language whenever the config title and the translation disagree.
    heading = ""
    if len(tokens) >= 3 and tokens[0].type == "heading_open" and tokens[0].tag == "h1":
        heading = tokens[1].content.strip()
        tokens = tokens[3:]

    tokens = _strip_language_line(tokens, base_dir, siblings or set())

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
        # Permalink, so a section of a guide can be linked to directly. Added
        # to the token stream rather than to the markdown, which stays plain.
        inline.children.append(_permalink(anchor))
        toc.append({"level": int(tok.tag[1]), "title": title, "anchor": anchor})

    html = md.renderer.render(tokens, md.options, {})
    html = _rewrite_links(html, base_dir, guide_slugs, depth)
    return {"html": html, "toc": toc, "heading": heading}


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
            return f'href="{up}docs/{slug}/{("#" + frag) if frag else ""}"'
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
        # Every source file of this doc, so its own language line can be
        # recognised precisely and removed.
        siblings = {entry.path.replace(os.sep, "/")}
        siblings |= {r.replace(os.sep, "/") for r in (entry.translations or {}).values()}

        base_dir = os.path.dirname(entry.path)
        rendered = _render(text, base_dir, slug_by_path, depth=2, siblings=siblings)

        langs: Dict[str, Dict[str, Any]] = {}
        for lang, rel in (entry.translations or {}).items():
            lpath = os.path.join(root, rel)
            if not os.path.isfile(lpath):
                warnings.append(f"guide translation missing: {rel}")
                continue
            with open(lpath, "r", encoding="utf-8", errors="replace") as f:
                langs[lang] = _render(f.read(), os.path.dirname(rel), slug_by_path,
                                      depth=3, siblings=siblings)

        out.append({
            "slug": entry.slug,
            "title": entry.title,
            "source": entry.path,
            "html": rendered["html"],
            "toc": rendered["toc"],
            "translations": langs,
        })
    return out, warnings
