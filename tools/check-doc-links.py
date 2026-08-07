#!/usr/bin/env python3
"""Check every relative link and anchor in the repository's markdown.

The documentation is bilingual and cross-links heavily — English to Chinese,
each document to its siblings, and several into named sections. A moved file
or a retitled heading breaks those silently, and nothing else in CI reads
markdown. Code — fenced or inline — is skipped: it contains example links on
purpose, including the hand-written language line the site strips.
"""

from __future__ import annotations

import pathlib
import re
import sys

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.M)
NOT_IN_ANCHOR = re.compile(r"[^\w一-鿿 \-]")


def body(text: str) -> str:
    """What counts as prose: no code, fenced or inline."""
    return INLINE_CODE.sub("", FENCE.sub("", text))


def anchors(text: str) -> set[str]:
    """Headings keep their inline code — `## `site`` anchors as `site`, the
    way GitHub slugs it — so only fenced blocks are dropped here."""
    out = set()
    for title in HEADING.findall(FENCE.sub("", text)):
        slug = NOT_IN_ANCHOR.sub("", title.strip().lower()).strip().replace(" ", "-")
        if slug:
            out.add(slug)
    return out


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    files = sorted(root.glob("*.md")) + sorted(root.glob("docs/**/*.md"))
    problems: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(body(text)):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            rel, _, fragment = target.partition("#")
            dest = (path.parent / rel).resolve() if rel else path.resolve()
            here = path.relative_to(root)
            if not dest.exists():
                problems.append(f"{here}: no such file -> {target}")
            elif fragment and dest.suffix == ".md" \
                    and fragment not in anchors(dest.read_text(encoding="utf-8")):
                problems.append(f"{here}: no such heading -> {target}")

    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    print(f"checked {len(files)} markdown files, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
