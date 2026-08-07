"""Derive the index's evolution from git history.

One `git log` pass replays add/delete/rename over the descriptor directory and
produces three things at once: the growth curve, the activity history line and
the per-descriptor author set.

Counting only additions is wrong: on mcpp-index it yields 86 where the tree
holds 81, because deletes and renames are ignored. `build.py` asserts the final
count equals the number of parsed packages, so that class of drift fails the
build instead of quietly shipping.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..models import GrowthPoint, HistoryEvent

# %aI is the full ISO author timestamp: the date drives the growth curve, the
# clock time disambiguates the several same-day commits a bump day produces.
_FORMAT = "C\t%H\t%aI\t%an\t%ae\t%s"


@dataclass
class AuthorStat:
    name: str
    email: str
    paths: Set[str] = field(default_factory=set)
    added_paths: Set[str] = field(default_factory=set)
    shas: Set[str] = field(default_factory=set)
    first_seen: str = ""
    last_seen: str = ""

    @property
    def key(self) -> str:
        return f"{self.name}|{self.email}"

    @property
    def commits(self) -> int:
        return len(self.shas)


@dataclass
class GitHistory:
    available: bool = False
    growth: List[GrowthPoint] = field(default_factory=list)
    # End-of-day snapshot of which descriptors existed. Keeping the set, not
    # just the count, is what lets the site draw a curve per facet ("how many
    # importable packages did we have in June?") without a second git pass.
    daily_active: List[Tuple[str, Set[str]]] = field(default_factory=list)
    events: List[HistoryEvent] = field(default_factory=list)
    per_path: Dict[str, List[HistoryEvent]] = field(default_factory=dict)
    authors: Dict[str, AuthorStat] = field(default_factory=dict)
    final_paths: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)


def _run(root: str, args: List[str]) -> Optional[str]:
    try:
        out = subprocess.run(["git", "-C", root] + args, capture_output=True,
                             text=True, check=False)
    except FileNotFoundError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _is_usable(root: str) -> Tuple[bool, str]:
    if _run(root, ["rev-parse", "--git-dir"]) is None:
        return False, "not a git repository — growth curve, history and contributors skipped"
    shallow = (_run(root, ["rev-parse", "--is-shallow-repository"]) or "").strip()
    if shallow == "true":
        return False, ("shallow clone detected — growth curve, history and contributors "
                       "skipped (set fetch-depth: 0)")
    return True, ""


def collect(root: str, pkgs_dir: str) -> GitHistory:
    """Replay descriptor add/delete/rename over the whole history."""
    hist = GitHistory()
    ok, why = _is_usable(root)
    if not ok:
        hist.warnings.append(why)
        return hist

    log = _run(root, [
        "log", "--reverse", "--date=short", "--find-renames",
        "--name-status", "--pretty=format:" + _FORMAT, "--", pkgs_dir,
    ])
    if log is None:
        hist.warnings.append("git log failed — history data skipped")
        return hist

    active: Set[str] = set()
    per_day: Dict[str, GrowthPoint] = {}
    snapshots: Dict[str, Set[str]] = {}
    order: List[str] = []
    date = author = email = subject = sha = stamp = ""

    def note_author(path: str, added: bool) -> None:
        key = f"{author}|{email}"
        stat = hist.authors.get(key)
        if stat is None:
            stat = AuthorStat(name=author, email=email, first_seen=date)
            hist.authors[key] = stat
        stat.paths.add(path)
        if added:
            stat.added_paths.add(path)
        stat.shas.add(sha)
        stat.last_seen = date
        if not stat.first_seen:
            stat.first_seen = date

    def record(kind: str, path: str) -> None:
        ev = HistoryEvent(date=date, kind=kind, slug="", display=path,
                          by=author, subject=subject, at=stamp)
        hist.events.append(ev)
        hist.per_path.setdefault(path, []).append(ev)

    for line in log.splitlines():
        if not line.strip():
            continue
        if line.startswith("C\t"):
            _, sha, stamp, author, email, subject = (line.split("\t", 5) + [""] * 5)[:6]
            date = stamp[:10]
            continue

        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            old, new = parts[1], parts[2]
            active.discard(old)
            active.add(new)
            hist.per_path[new] = hist.per_path.pop(old, [])
            note_author(new, added=False)
            record("updated", new)
        elif status.startswith("A") and len(parts) >= 2:
            path = parts[1]
            active.add(path)
            note_author(path, added=True)
            record("added", path)
        elif status.startswith("D") and len(parts) >= 2:
            path = parts[1]
            active.discard(path)
            note_author(path, added=False)
            record("removed", path)
        elif status.startswith("M") and len(parts) >= 2:
            path = parts[1]
            note_author(path, added=False)
            record("updated", path)
        else:
            continue

        point = per_day.get(date)
        if point is None:
            point = GrowthPoint(date=date, count=len(active))
            per_day[date] = point
            order.append(date)
        point.count = len(active)
        snapshots[date] = set(active)
        if status.startswith("A"):
            point.added += 1
        elif status.startswith("D"):
            point.removed += 1

    dates = sorted(order)
    hist.growth = [per_day[d] for d in dates]
    hist.daily_active = [(d, snapshots[d]) for d in dates]
    hist.events.reverse()                     # newest first
    hist.final_paths = active
    hist.available = True
    return hist


def commit_counts_by_author(hist: GitHistory) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for stat in hist.authors.values():
        counts[stat.key] = stat.commits
    return dict(counts)
