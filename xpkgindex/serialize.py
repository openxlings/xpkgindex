"""The `index.json` contract.

This is the formal boundary between the data layer and the render layer, and
it is deliberately shaped like an API response: a server that later replaces
the static build serves the same documents, so the front end and any third
party tooling keep working unchanged.

Text an index writes per locale is flattened to the site's default language
here. `index.json` is one document at one URL, and schema 1 promises strings:
a consumer that suddenly received `{"en": …, "zh": …}` where it expected a
label would break. Translations live in the rendered pages.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from . import i18n
from .models import Package, SiteData

SCHEMA = 1

# The locale index.json speaks. Set per build from the site's language list.
_LANG = i18n.DEFAULT

# Keys that mark a dict as "the same text in several languages" rather than
# data. Deliberately the known tags only: a descriptor's `{GLOBAL, CN}` url map
# or a `{linux, windows}` platform map must never be mistaken for one.
_LANG_KEYS = (set(i18n.LANGUAGE_NAMES) | set(i18n.ALIASES)
              | {tag.split("-")[0] for tag in i18n.LANGUAGE_NAMES})


def set_locale(lang: str) -> None:
    """Choose the language the JSON documents speak (the site default)."""
    global _LANG
    _LANG = lang


def _s(value: Any) -> Any:
    """Flatten a possibly per-locale value to the default language."""
    return i18n.localize(value, _LANG, _LANG)


def _flat(value: Any) -> Any:
    """Resolve every per-locale map anywhere in a document.

    Plugins put their own text in places the schema does not name — a block's
    `data`, an extension payload — so flattening only the fields listed here
    left maps in the JSON. Walking the finished document catches all of them
    without the serializer having to know what a plugin invented.
    """
    if isinstance(value, dict):
        if value and all(k in _LANG_KEYS for k in value):
            return _s(value)
        return {k: _flat(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_flat(v) for v in value]
    return value


def _block_dict(block: Any) -> Dict[str, Any]:
    data = dict(asdict(block))
    data["title"] = _s(data.get("title"))
    payload = data.get("data")
    if isinstance(payload, dict):
        payload = dict(payload)
        for field in ("caption", "source", "text"):
            if field in payload:
                payload[field] = _s(payload[field])
        data["data"] = payload
    return data


def package_dict(pkg: Package) -> Dict[str, Any]:
    return _flat(_package_dict(pkg))


def _package_dict(pkg: Package) -> Dict[str, Any]:
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
        "blocks": [_block_dict(b) for b in pkg.sorted_blocks()],
        "source_file": pkg.source_file,
    }


def index_dict(site: SiteData, config: Any, lang: str = i18n.DEFAULT) -> Dict[str, Any]:
    set_locale(lang)
    return _flat({
        "schema": SCHEMA,
        "site": {
            "title": _s(config.title),
            "description": _s(config.description),
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
                "label": _s(f.label),
                "values": [
                    {"key": v.key, "label": _s(v.label), "count": v.count, "tone": v.tone}
                    for v in f.values
                ],
            }
            for f in site.facets
        ],
        "growth": [asdict(p) for p in site.growth],
        "history": [asdict(e) for e in site.history[:200]],
        "guides": [{"slug": g["slug"], "title": _s(g["title"]), "source": g["source"]}
                   for g in site.guides],
        "packages": [_package_dict(p) for p in site.packages],
    })


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
