"""Build orchestration: read → model → plugins → derive → serialize.

Rendering lives in `render.py`; this module produces the `SiteData` that both
the templates and `index.json` are built from, so the two can never disagree.
"""

from __future__ import annotations

import glob
import os
import subprocess
from typing import Any, Dict, List, Optional, Set

from . import guides as guides_mod
from .config import SiteConfig, load_config
from .data import git_history, github, identities
from .models import (Facet, FacetValue, GrowthPoint, GrowthSeries, IndexMeta,
                     Package, Person, RowSpec,
                     SiteData, UpstreamProject)
from .plugins import IndexContext, load_plugins
from .readers import xpkg_lua


class BuildError(Exception):
    """A data-correctness problem. Never raised for external-dependency issues."""


# --------------------------------------------------------------------------

def _tracked_clean(root: str, pkgs_dir: str) -> bool:
    try:
        out = subprocess.run(["git", "-C", root, "status", "--porcelain", "--", pkgs_dir],
                             capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return False
    return out.returncode == 0 and not out.stdout.strip()


def _assign_identities(packages: List[Package], host, config: SiteConfig) -> None:
    for pkg in packages:
        ident = host.identity(pkg.raw, pkg.source_file)
        if ident is not None:
            pkg.identity = ident


def _check_slugs(packages: List[Package]) -> None:
    """Duplicate slugs silently overwrote pages before; now they stop the build."""
    seen: Dict[str, Package] = {}
    clashes: Dict[str, List[Package]] = {}
    for pkg in packages:
        first = seen.get(pkg.identity.slug)
        if first is None:
            seen[pkg.identity.slug] = pkg
            continue
        clashes.setdefault(pkg.identity.slug, [first]).append(pkg)
    if clashes:
        lines = ["duplicate package slugs — pages would overwrite each other:"]
        for slug, group in sorted(clashes.items()):
            lines.append(f"  {slug}")
            for p in group:
                lines.append(f"    - {p.source_file} (namespace={p.namespace or '-'})")
        lines.append("  fix: give the ecosystem plugin an identity() that disambiguates")
        raise BuildError("\n".join(lines))


def _install_commands(packages: List[Package], config: SiteConfig) -> None:
    tmpl = config.install_command_template
    for pkg in packages:
        version = pkg.latest or "latest"
        try:
            cmd = tmpl.format(ref=pkg.identity.install_ref,
                              name=pkg.identity.name,
                              namespace=pkg.identity.namespace,
                              display=pkg.identity.display,
                              version=version)
        except (KeyError, IndexError):
            cmd = f"{pkg.identity.install_ref}@{version}"
        pkg.extensions.setdefault("_core", {})["install_command"] = cmd


def _reverse_deps(packages: List[Package]) -> None:
    """Map dependency strings back onto packages, by any of their names."""
    by_key: Dict[str, Package] = {}
    for pkg in packages:
        for key in {pkg.identity.slug, pkg.identity.display,
                    pkg.identity.install_ref, pkg.identity.name}:
            by_key.setdefault(key, pkg)
    for pkg in packages:
        for dep in pkg.deps:
            target = by_key.get(dep.split("@")[0].strip())
            if target is not None and target is not pkg:
                if pkg.identity.slug not in target.required_by:
                    target.required_by.append(pkg.identity.slug)


def _apply_default_namespace(packages: List[Package], meta: IndexMeta) -> None:
    """Resolve each package's effective namespace.

    A descriptor that omits `namespace` still belongs to one — the index's
    default (`xim` for xim-pkgindex, `mcpplibs` for mcpp-index). Rendering
    those as "—" invented a bucket of 146 packages that does not exist. The
    plugin supplies the default via `on_index`; only display and grouping use
    it, never the slug or the install command.
    """
    default = str(meta.get("default_namespace") or "")
    for pkg in packages:
        if pkg.namespace:
            pkg.effective_namespace = pkg.namespace
            pkg.namespace_implicit = False
        else:
            pkg.effective_namespace = default
            pkg.namespace_implicit = bool(default)


def _assign_rows(packages: List[Package], host, config: SiteConfig) -> None:
    """Ask the plugin how each row should read; fall back to a sane default.

    The default leads with the interface line when the ecosystem declared one
    and with the install command otherwise — never with nothing.
    """
    for pkg in packages:
        spec = host.row(pkg)
        if spec is None:
            iface = pkg.interface
            spec = RowSpec(
                variant=config.list_variant,
                tone=pkg.tone,
                lead=(iface.data.get("label", "") if iface else ""),
                code=(iface.data.get("code", "") if iface else ""),
                badges=list(pkg.extensions.get("_badges", [])),
            )
        elif not spec.variant:
            spec.variant = config.list_variant
        if not spec.install:
            spec.install = pkg.install_command
        pkg.row = spec


def _core_facets(packages: List[Package]) -> List[Facet]:
    """Namespace is the one axis every index has."""
    counts: Dict[str, int] = {}
    for pkg in packages:
        ns = pkg.effective_namespace
        if not ns:
            continue
        counts[ns] = counts.get(ns, 0) + 1
        pkg.facets.setdefault("namespace", ns)
    values = [FacetValue(key=k, label=k, count=v)
              for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return [Facet(key="namespace", label="namespace", label_key="facet.namespace",
                  values=values, weight=200)]


def _count_facets(facets: List[Facet], packages: List[Package]) -> List[Facet]:
    """Facet values are space-separated, so one package can sit in several.

    Some packages genuinely belong to more than one bucket — `nlohmann.json`
    ships a C++23 module *and* exposes its headers, so forcing a single value
    would make either the `import` or the `#include` filter lie.
    """
    out: List[Facet] = []
    for facet in facets:
        counts: Dict[str, int] = {}
        for pkg in packages:
            for val in str(pkg.facets.get(facet.key) or "").split():
                counts[val] = counts.get(val, 0) + 1
        values = [v for v in facet.values if counts.get(v.key)]
        for v in values:
            v.count = counts.get(v.key, 0)
        if not values:                      # plugin declared the axis but no values
            values = [FacetValue(key=k, label=k, count=c)
                      for k, c in sorted(counts.items(), key=lambda kv: -kv[1])]
        facet.values = values
        if values:
            out.append(facet)
    return sorted(out, key=lambda f: f.weight)


# --------------------------------------------------------------------------

def _growth_series(hist: git_history.GitHistory, packages: List[Package],
                   config: SiteConfig) -> List[GrowthSeries]:
    """The total, plus one line per configured facet filter.

    Caveat worth knowing: the facet of a package is its facet *today*, applied
    backwards over the historical set. Descriptors do not record when a
    package became importable, so a line answers "how many of the packages
    that existed then are, by today's classification, X" — which is the
    question people actually ask, but it is not archaeology.
    """
    total = GrowthSeries(key="all", label=config.growth_total_label or "all",
                         points=list(hist.growth))
    out = [total]
    if not config.growth_series:
        return out

    by_path = {p.source_file: p for p in packages}
    for spec in config.growth_series:
        facet, value = spec.get("facet", ""), spec.get("value", "")
        matching = {
            path for path, pkg in by_path.items()
            if value in str(pkg.facets.get(facet, "")).split()
        }
        if not matching:
            continue
        points = [GrowthPoint(date=date, count=len(active & matching))
                  for date, active in hist.daily_active]
        # A semantic tone that happens to resolve to the site accent would
        # draw this line in the total's colour — two indistinguishable curves.
        # Fall back to the chart palette in that case.
        tone = spec.get("tone", "")
        if tone and config.tones.get(tone, "") == config.accent:
            tone = ""
        out.append(GrowthSeries(key=f"{facet}:{value}",
                                label=spec.get("label") or value,
                                points=points, tone=tone))
    return out


def _attach_history(site: SiteData, hist: git_history.GitHistory,
                    packages: List[Package]) -> None:
    by_path = {p.source_file: p for p in packages}
    for ev in hist.events:
        pkg = by_path.get(ev.display)
        if pkg is not None:
            ev.slug = pkg.identity.slug
            ev.display = pkg.identity.display
    site.history = [e for e in hist.events if e.slug or e.kind == "removed"]

    for path, events in hist.per_path.items():
        pkg = by_path.get(path)
        if pkg is None:
            continue
        pkg.history = [{"date": e.date, "at": e.at, "clock": e.clock, "kind": e.kind,
                        "by": e.by, "subject": e.subject}
                       for e in reversed(events)][:12]


def _contributors(hist: git_history.GitHistory, config: SiteConfig,
                  packages: List[Package], logins: Dict[str, str]) -> List[Person]:
    manual = identities.load_manual_map(config.root, config.identities_path)
    people = identities.merge(hist.authors, manual=manual, logins=logins)
    by_path = {p.source_file: p for p in packages}
    for person in people:
        slugs = []
        for path in person.packages:
            pkg = by_path.get(path)
            if pkg is not None and pkg.identity.slug not in slugs:
                slugs.append(pkg.identity.slug)
        person.packages = sorted(slugs)
    return people


def _attach_people(packages: List[Package], hist: git_history.GitHistory,
                   people: List[Person],
                   upstream_by_owner: Dict[str, UpstreamProject]) -> None:
    """Per package: who wrote the library upstream vs who wrote the descriptor."""
    for pkg in packages:
        host, owner, _ = github.parse_repo_url(pkg.repo)
        up = upstream_by_owner.get(owner.lower()) if owner else None
        maintainers = []
        added_by = ""
        for ev in hist.per_path.get(pkg.source_file, []):
            if ev.kind == "added" and not added_by:
                added_by = ev.by
        for person in people:
            if pkg.identity.slug in person.packages:
                maintainers.append({
                    "login": person.login, "name": person.name,
                    "avatar": person.avatar, "url": person.url,
                    # `added_by` is a raw git author name; a person may have
                    # committed under several, so match against all of them.
                    "added": added_by in person.names,
                })
        pkg.people = {
            "upstream": ({
                "owner": up.owner, "url": up.url, "avatar": up.avatar,
                "description": up.description, "stars": up.stars, "host": up.host,
            } if up else ({"owner": owner, "url": pkg.repo, "host": host} if owner else {})),
            "descriptor": maintainers,
        }


# --------------------------------------------------------------------------

def build(root: str, config_path: Optional[str] = None, *,
          offline: bool = False, strict: bool = False, refresh: bool = False,
          build_info: Optional[Dict[str, str]] = None) -> (SiteData, SiteConfig):
    root = os.path.abspath(root)
    config = load_config(root, config_path)
    site = SiteData()
    site.build = dict(build_info or {})

    # -- descriptors ------------------------------------------------------
    pkgs_dir = os.path.join(root, config.pkgs_dir)
    if not os.path.isdir(pkgs_dir):
        raise BuildError(f"packages directory not found: {pkgs_dir}")
    packages, warns = xpkg_lua.read_dir(pkgs_dir, root)
    site.warnings.extend(warns)
    if not packages:
        raise BuildError(f"no packages parsed from {pkgs_dir}")

    # -- plugins ----------------------------------------------------------
    # `host.warnings` keeps accumulating as hooks run, so it is drained once
    # at the end of the build — draining it here would silently discard every
    # runtime plugin failure.
    host = load_plugins(config.plugins, root)
    meta = IndexMeta()
    host.on_index(IndexContext(root, meta, config))
    site.index_meta = meta

    _assign_identities(packages, host, config)
    for pkg in packages:
        host.on_package(pkg, pkg.raw)
    _check_slugs(packages)

    packages.sort(key=lambda p: p.identity.display.lower())
    _install_commands(packages, config)

    # Remote enrichment runs BEFORE facets, blocks and rows: a plugin that
    # resolves data it could not read from the descriptor alone (an upstream
    # manifest, say) must be able to change how the package is classified and
    # rendered, which is impossible once those are already computed.
    token = os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", "")
    cache = github.GitHubCache(root, config.cache_path, token=token,
                               offline=offline, force=refresh)
    host.enrich_remote(packages, cache)

    _reverse_deps(packages)
    _apply_default_namespace(packages, meta)
    site.packages = packages

    facets = _core_facets(packages) + host.facets()
    site.facets = _count_facets(facets, packages)

    for pkg in packages:
        pkg.blocks = host.detail_blocks(pkg)
    _assign_rows(packages, host, config)

    # -- git derived ------------------------------------------------------
    hist = git_history.collect(root, config.pkgs_dir)
    site.warnings.extend(hist.warnings)
    if hist.available:
        site.growth = hist.growth
        site.growth_series = _growth_series(hist, packages, config)
        _attach_history(site, hist, packages)
        _verify_growth(site, hist, pkgs_dir, root, config, strict)

    # -- github enrichment ------------------------------------------------
    logins: Dict[str, str] = {}
    upstream_by_owner = _upstreams(packages, cache, config)
    site.upstreams = sorted(upstream_by_owner.values(),
                            key=lambda u: (u.is_own, -(u.stars or 0), u.owner.lower()))
    if config.repo_slug:
        logins = github.commit_login_map(cache, config.repo_slug)
    site.ecosystem_repos, site.ecosystem = _ecosystem(cache, config)
    site.warnings.extend(cache.warnings)
    cache.save()

    if hist.available:
        site.contributors = _contributors(hist, config, packages, logins)
    _attach_people(packages, hist, site.contributors, upstream_by_owner)

    # -- guides -----------------------------------------------------------
    site.guides, gwarn = guides_mod.load(root, config.guides)
    site.warnings.extend(gwarn)

    site.warnings.extend(host.warnings)
    return site, config


def _verify_growth(site: SiteData, hist: git_history.GitHistory, pkgs_dir: str,
                   root: str, config: SiteConfig, strict: bool) -> None:
    """The replayed set must equal what is on disk — otherwise the curve lies."""
    on_disk = {
        os.path.relpath(p, root).replace(os.sep, "/")
        for p in glob.glob(os.path.join(pkgs_dir, "**", "*.lua"), recursive=True)
    }
    missing = on_disk - hist.final_paths
    extra = hist.final_paths - on_disk
    if not missing and not extra:
        return
    detail = []
    if missing:
        detail.append(f"{len(missing)} on disk but not in history ({sorted(missing)[:3]}…)")
    if extra:
        detail.append(f"{len(extra)} in history but not on disk ({sorted(extra)[:3]}…)")
    msg = "growth curve does not reconcile with the tree: " + "; ".join(detail)
    if _tracked_clean(root, config.pkgs_dir) or strict:
        raise BuildError(msg)
    site.warnings.append(msg + " (working tree is dirty — treated as a warning)")


def _upstreams(packages: List[Package], cache: github.GitHubCache,
               config: SiteConfig) -> Dict[str, UpstreamProject]:
    own = {o.lower() for o in config.ecosystem_owners}
    out: Dict[str, UpstreamProject] = {}
    for pkg in packages:
        host, owner, name = github.parse_repo_url(pkg.repo)
        if not owner:
            continue
        key = owner.lower()
        up = out.get(key)
        if up is None:
            up = UpstreamProject(owner=owner, host=host,
                                 url=f"https://{host}/{owner}" if host else pkg.repo,
                                 is_own=key in own)
            out[key] = up
        up.packages.append(pkg.identity.slug)

        if host == "github.com" and up.stars is None and name:
            info = github.repo_info(cache, f"{owner}/{name}")
            if info:
                up.avatar = info["owner_avatar"]
                up.url = info["owner_url"] or up.url
                up.description = info["description"]
                up.stars = info["stars"]
    return out


def _ecosystem(cache: github.GitHubCache, config: SiteConfig):
    repos: List[Dict[str, Any]] = []
    people: Dict[str, Person] = {}
    for slug in config.ecosystem_repos:
        info = github.repo_info(cache, slug)
        entry = {"slug": slug, "stars": (info or {}).get("stars"),
                 "description": (info or {}).get("description", ""),
                 "url": f"https://github.com/{slug}"}
        repos.append(entry)
        for c in github.contributors(cache, slug):
            person = people.get(c["login"])
            if person is None:
                person = Person(key=c["login"], login=c["login"],
                                avatar=c["avatar"], url=c["url"])
                people[c["login"]] = person
            person.commits += c["contributions"]
            if slug not in person.repos:
                person.repos.append(slug)
    ordered = sorted(people.values(), key=lambda p: (-len(p.repos), -p.commits))
    return repos, ordered
