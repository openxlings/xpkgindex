"""Build-time enrichment from GitHub, with a committable cache.

Descriptors carry a `repo` URL for every package but almost no other metadata,
so upstream description / stars / avatars are fetched here. Everything is
optional: no token, rate limiting, offline builds and non-GitHub hosts all
degrade to "render what we already have" — never to a failed build.

Not every upstream is on GitHub (mcpp-index has 15 packages on
gitlab.freedesktop.org and one on sourceware.org). Those are recorded with
their owner and link, and simply carry no fetched metadata.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

API = "https://api.github.com"
USER_AGENT = "xpkgindex-site-generator"


def parse_repo_url(url: str) -> Tuple[str, str, str]:
    """-> (host, owner, name); empty strings when unparsable."""
    if not url:
        return "", "", ""
    try:
        parsed = urllib.parse.urlparse(url if "//" in url else "https://" + url)
    except ValueError:
        return "", "", ""
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return parsed.netloc, parts[0] if parts else "", ""
    name = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    return parsed.netloc, parts[0], name


class GitHubCache:
    """URL-keyed JSON cache. Reads always work; writes only when online."""

    def __init__(self, root: str, relative: str, token: str = "",
                 offline: bool = False, force: bool = False,
                 ttl_days: int = 14) -> None:
        self.path = os.path.join(root, relative)
        self.token = token
        self.offline = offline
        # `force` is the manual refresh: re-fetch even entries that are still
        # fresh, so a maintainer can pull in upstream changes on demand
        # instead of waiting for a TTL.
        self.force = force
        self.ttl = ttl_days * 86400
        self.dirty = False
        self.warnings: List[str] = []
        self.entries: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.entries = data.get("entries", {}) if isinstance(data, dict) else {}
        except Exception as exc:                 # noqa: BLE001
            self.warnings.append(f"github cache unreadable ({exc}); starting empty")

    def save(self) -> None:
        if not self.dirty:
            return
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        payload = {"schema": 1, "fetched_at": int(time.time()), "entries": self.entries}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)

    def get(self, url: str, project: Optional[Callable[[Any], Any]] = None) -> Optional[Any]:
        """Fetch `url`, storing only what `project` keeps.

        Projecting before caching matters: the raw commits endpoint alone is
        megabytes per repo, and this file is meant to be committed and read by
        humans reviewing a PR.
        """
        entry = self.entries.get(url)
        fresh = (entry is not None and not self.force
                 and (time.time() - entry.get("at", 0)) < self.ttl)
        if fresh or self.offline:
            return entry.get("body") if entry else None

        body = self._fetch(url)
        if body is None:
            # Stale cache beats nothing.
            return entry.get("body") if entry else None
        stored = project(body) if project else body
        self.entries[url] = {"at": int(time.time()), "body": stored}
        self.dirty = True
        return stored

    def get_text(self, url: str, project: Optional[Callable[[str], Any]] = None) -> Optional[Any]:
        """Same cache, for plain-text resources (an upstream `mcpp.toml`).

        Keyed by URL, and an upstream manifest URL contains its release tag —
        so a cached entry is only refetched when the package version actually
        changes, which is exactly the "only on update" behaviour wanted here.
        """
        entry = self.entries.get(url)
        if (entry is not None and not self.force) or self.offline:
            return entry.get("body") if entry else None
        text = self._fetch(url, as_json=False)
        if text is None:
            return None
        stored = project(text) if project else text
        self.entries[url] = {"at": int(time.time()), "body": stored}
        self.dirty = True
        return stored

    def _fetch(self, url: str, as_json: bool = True) -> Optional[Any]:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw) if as_json else raw
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                self.offline = True              # rate limited: stop hammering
                self.warnings.append("github rate limited — using cached data only")
            elif exc.code == 404:
                self.entries[url] = {"at": int(time.time()), "body": None}
                self.dirty = True
            else:
                self.warnings.append(f"github {exc.code} for {url}")
            return None
        except Exception as exc:                 # noqa: BLE001 - offline, DNS, TLS...
            self.offline = True
            self.warnings.append(f"github unreachable ({exc}) — using cached data only")
            return None


def _project_repo(body: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(body, dict):
        return None
    owner = body.get("owner") or {}
    return {
        "slug": body.get("full_name", ""),
        "description": body.get("description") or "",
        "stars": body.get("stargazers_count"),
        "language": body.get("language") or "",
        "topics": body.get("topics") or [],
        "license": ((body.get("license") or {}).get("spdx_id") or ""),
        "homepage": body.get("homepage") or "",
        "owner": owner.get("login", ""),
        "owner_avatar": owner.get("avatar_url", ""),
        "owner_url": owner.get("html_url", ""),
    }


def _project_contributors(body: Any) -> List[Dict[str, Any]]:
    if not isinstance(body, list):
        return []
    return [
        {
            "login": c.get("login", ""),
            "avatar": c.get("avatar_url", ""),
            "url": c.get("html_url", ""),
            "contributions": c.get("contributions", 0),
        }
        for c in body if isinstance(c, dict) and c.get("login")
    ]


def _project_commit_logins(body: Any) -> Dict[str, str]:
    """Keep only `"name|email" -> login`; the rest of a commit page is noise."""
    mapping: Dict[str, str] = {}
    if not isinstance(body, list):
        return mapping
    for item in body:
        if not isinstance(item, dict):
            continue
        login = (item.get("author") or {}).get("login")
        commit = (item.get("commit") or {}).get("author") or {}
        name, email = commit.get("name", ""), commit.get("email", "")
        if login and (name or email):
            mapping[f"{name}|{email}"] = login
    return mapping


def repo_info(cache: GitHubCache, slug: str) -> Optional[Dict[str, Any]]:
    info = cache.get(f"{API}/repos/{slug}", _project_repo)
    if isinstance(info, dict):
        info.setdefault("slug", slug)
        return info
    return None


def contributors(cache: GitHubCache, slug: str, limit: int = 30) -> List[Dict[str, Any]]:
    body = cache.get(f"{API}/repos/{slug}/contributors?per_page={limit}",
                     _project_contributors)
    return body if isinstance(body, list) else []


def commit_login_map(cache: GitHubCache, slug: str, pages: int = 5) -> Dict[str, str]:
    """Map `"name|email"` to the GitHub login that authored those commits.

    This is the authoritative signal for identity merging — GitHub resolves
    verified emails to accounts, which no local heuristic can do.
    """
    mapping: Dict[str, str] = {}
    for page in range(1, pages + 1):
        body = cache.get(f"{API}/repos/{slug}/commits?per_page=100&page={page}",
                         _project_commit_logins)
        if not isinstance(body, dict) or not body:
            break
        mapping.update(body)
    return mapping
