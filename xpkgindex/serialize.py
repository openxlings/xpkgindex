"""The `index.json` contract.

This is the formal boundary between the data layer and the render layer, and
it is deliberately shaped like an API response: a server that later replaces
the static build serves the same documents, so the front end and any third
party tooling keep working unchanged.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from .models import Package, SiteData

SCHEMA = 1


def package_dict(pkg: Package) -> Dict[str, Any]:
    return {
        "id": pkg.identity.slug,
        "namespace": pkg.identity.namespace,
        "namespace_effective": pkg.effective_namespace,
        "namespace_implicit": pkg.namespace_implicit,
        "name": pkg.identity.name,
        "display": pkg.identity.display,
        "slug": pkg.identity.slug,
        "install_ref": pkg.identity.install_ref,
        "description": pkg.description,
        "homepage": pkg.homepage,
        "repo": pkg.repo,
        "docs": pkg.docs,
        "licenses": pkg.licenses,
        "type": pkg.type,
        "status": pkg.status,
        "latest": pkg.latest,
        "platforms": {
            name: {"versions": info.versions, "latest": info.latest, "deps": info.deps}
            for name, info in pkg.platforms.items()
        },
        "versions": [
            {"version": v.version, "platforms": v.platforms,
             "urls": v.urls, "sha256": v.sha256}
            for v in pkg.versions
        ],
        "deps": pkg.deps,
        "required_by": pkg.required_by,
        "facets": pkg.facets,
        "people": pkg.people,
        "history": pkg.history,
        "extensions": pkg.extensions,
        "blocks": [asdict(b) for b in pkg.sorted_blocks()],
        "source_file": pkg.source_file,
    }


def index_dict(site: SiteData, config: Any) -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "site": {
            "title": config.title,
            "description": config.description,
            "github": config.github,
            **site.build,
        },
        "index": site.index_meta.fields,
        "stats": {
            "packages": site.total_packages,
            "namespaces": site.total_namespaces,
            "versions": site.total_versions,
        },
        "facets": [
            {
                "key": f.key,
                "label": f.label,
                "values": [
                    {"key": v.key, "label": v.label, "count": v.count, "tone": v.tone}
                    for v in f.values
                ],
            }
            for f in site.facets
        ],
        "growth": [asdict(p) for p in site.growth],
        "history": [asdict(e) for e in site.history[:200]],
        "guides": [{"slug": g["slug"], "title": g["title"], "source": g["source"]}
                   for g in site.guides],
        "packages": [package_dict(p) for p in site.packages],
    }


def search_index(site: SiteData) -> List[Dict[str, Any]]:
    """Small payload for client-side search: matching fields only."""
    out = []
    for pkg in site.packages:
        out.append({
            "s": pkg.identity.slug,
            "d": pkg.identity.display,
            "n": pkg.identity.name,
            "ns": pkg.identity.namespace,
            "t": pkg.description[:160],
            "f": pkg.facets,
            "v": pkg.latest,
        })
    return out


def legacy_packages_json(site: SiteData) -> List[Dict[str, Any]]:
    """Schema 0 shape, kept one release cycle so existing consumers of
    `/packages.json` do not break the day the new site ships."""
    out = []
    for pkg in site.packages:
        out.append({
            "name": pkg.identity.display,
            "description": pkg.description,
            "homepage": pkg.homepage,
            "repo": pkg.repo,
            "docs": pkg.docs,
            "licenses": pkg.licenses,
            "type": pkg.type,
            "status": pkg.status,
            "platforms": list(pkg.platforms.keys()),
            "latest_version": pkg.latest,
            "all_versions": sorted(v.version for v in pkg.versions),
            "deps": pkg.deps,
            "install_command": pkg.extensions.get("_core", {}).get("install_command", ""),
        })
    return out
