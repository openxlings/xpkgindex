"""Collapse git author identities into people.

`mcpp-index` has ten git identities for roughly eight humans — the same person
appears as `SPeak <speakshen@163.com>`, `sunrisepeak <speakshen@163.com>` and
`sunrisepeak <x.d2learn.org@gmail.com>`. Rendering those as three contributors
is wrong, so identities are unioned on three signals, strongest first:

1. an explicit map in `.xpkgindex/identities.json`
2. a GitHub noreply address, which encodes the login
3. a shared email, or a shared author name

An explicit map always wins; it exists precisely for the cases the heuristics
get wrong.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from ..models import Person
from .git_history import AuthorStat

_NOREPLY = re.compile(r"^(?:\d+\+)?([A-Za-z0-9-]+)@users\.noreply\.github\.com$")


class _Union:
    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def login_from_email(email: str) -> str:
    m = _NOREPLY.match(email or "")
    return m.group(1) if m else ""


def load_manual_map(root: str, relative: str) -> Dict[str, str]:
    """`{"name|email": "canonical-login"}` — optional, wins over heuristics."""
    path = os.path.join(root, relative)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:                            # noqa: BLE001
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def merge(stats: Dict[str, AuthorStat], manual: Optional[Dict[str, str]] = None,
          logins: Optional[Dict[str, str]] = None) -> List[Person]:
    """Union author stats into people, strongest signal first."""
    manual = manual or {}
    logins = dict(logins or {})
    uf = _Union()

    by_email: Dict[str, List[str]] = {}
    by_name: Dict[str, List[str]] = {}
    by_login: Dict[str, List[str]] = {}

    for key, stat in stats.items():
        uf.find(key)
        login = manual.get(key) or logins.get(key) or login_from_email(stat.email)
        if login:
            logins[key] = login
            by_login.setdefault(login.lower(), []).append(key)
        if stat.email:
            by_email.setdefault(stat.email.lower(), []).append(key)
        if stat.name:
            by_name.setdefault(stat.name.strip().lower(), []).append(key)

    for group in list(by_login.values()) + list(by_email.values()) + list(by_name.values()):
        for other in group[1:]:
            uf.union(group[0], other)

    people: Dict[str, Person] = {}
    for key, stat in stats.items():
        root_key = uf.find(key)
        person = people.get(root_key)
        if person is None:
            person = Person(key=root_key)
            people[root_key] = person
        login = logins.get(key, "")
        if login and not person.login:
            person.login = login
        if stat.name and (not person.name or len(stat.name) > len(person.name)):
            person.name = stat.name
        if stat.name and stat.name not in person.names:
            person.names.append(stat.name)
        if stat.email and not person.email:
            person.email = stat.email
        person.commits += stat.commits
        for p in stat.paths:
            if p not in person.packages:
                person.packages.append(p)
        if stat.first_seen and (not person.first_seen or stat.first_seen < person.first_seen):
            person.first_seen = stat.first_seen
        if stat.last_seen and stat.last_seen > person.last_seen:
            person.last_seen = stat.last_seen

    for person in people.values():
        if person.login:
            person.avatar = f"https://github.com/{person.login}.png?size=96"
            person.url = f"https://github.com/{person.login}"

    # Automation is not a contributor. `github-actions[bot]` lands high in the
    # list on repos with version-bump workflows and reads as a person.
    humans = [p for p in people.values() if not _is_bot(p)]
    return sorted(humans, key=lambda p: (-p.commits, p.label.lower()))


def _is_bot(person) -> bool:
    label = (person.login or person.name or "").lower()
    return label.endswith("[bot]") or label.endswith("-bot") or label == "dependabot"
