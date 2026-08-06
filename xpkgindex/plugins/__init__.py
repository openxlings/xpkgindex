"""Plugin system.

An index repo carries its own ecosystem semantics as a plugin — the core knows
nothing about mcpp or xlings. Plugins return structured data (Block/Facet/
Identity), never HTML, so every consumer site keeps one visual system and the
plugin output travels verbatim into `index.json`.

Trust model: the build already executes the repo's own `.lua` descriptors in
its own workflow, so executing the repo's own Python adds no new risk.

Failure model: any hook may raise; the core logs a warning, drops that
plugin's contribution for that call and keeps building. The one exception is a
duplicate slug, which is a data-correctness failure and aborts the build
(see `build.py`).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any, Dict, List, Optional

from ..models import Block, Facet, Identity, IndexMeta, Package, RowSpec

API_VERSION = 1


class Plugin:
    """Base class. Every hook is optional; the defaults are no-ops."""

    api_version: int = API_VERSION
    name: str = "plugin"

    # -- repo level -------------------------------------------------------
    def on_index(self, ctx: "IndexContext") -> None:
        """Read repo-level configuration (index.toml, mcpp.toml, ...)."""

    # -- per package ------------------------------------------------------
    def identity(self, raw: Dict[str, Any], path: str) -> Optional[Identity]:
        """Return the canonical identity, or None to keep the core default.

        The core default never joins the namespace: doing so silently would
        produce install commands the client rejects.
        """
        return None

    def on_package(self, pkg: Package, raw: Dict[str, Any]) -> None:
        """Populate `pkg.extensions[self.name]`, `pkg.facets`, `pkg.deps`."""

    def facets(self) -> List[Facet]:
        """Declare facet axes. Counts are filled in by the core."""
        return []

    def detail_blocks(self, pkg: Package) -> List[Block]:
        """Structured detail-page content for one package."""
        return []

    def row(self, pkg: Package) -> Optional["RowSpec"]:
        """Describe this package's listing row, or None for the core default.

        Lets an ecosystem decide what the densest surface on the site leads
        with, without forking the template.
        """
        return None

    # -- network ----------------------------------------------------------
    def enrich_remote(self, packages: List[Package], http: Any) -> None:
        """Optional build-time enrichment. Must be skippable and cacheable."""


class IndexContext:
    """What a plugin sees at repo level."""

    def __init__(self, root: str, meta: IndexMeta, config: Any) -> None:
        self.root = root
        self.meta = meta
        self.config = config

    def path(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    def read_text(self, relative: str) -> Optional[str]:
        p = self.path(relative)
        if not os.path.isfile(p):
            return None
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def _load_from_file(path: str) -> List[Plugin]:
    """Import a repo-local .py file and instantiate every Plugin subclass."""
    module_name = "xpkgindex_plugin_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load plugin module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return _instantiate(module)


def _load_from_entrypoint(name: str) -> List[Plugin]:
    from importlib.metadata import entry_points

    eps = entry_points()
    group = eps.select(group="xpkgindex.plugins") if hasattr(eps, "select") \
        else eps.get("xpkgindex.plugins", [])       # pragma: no cover - py<3.10
    for ep in group:
        if ep.name == name:
            obj = ep.load()
            return [obj()] if isinstance(obj, type) else _instantiate(obj)
    raise ImportError(f"no entry point named {name!r} in group 'xpkgindex.plugins'")


def _instantiate(module: Any) -> List[Plugin]:
    found: List[Plugin] = []
    for attr in vars(module).values():
        if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
            found.append(attr())
    return found


def load_plugins(specs: List[str], root: str) -> "PluginHost":
    plugins: List[Plugin] = []
    warnings: List[str] = []
    for spec in specs:
        try:
            if spec.endswith(".py"):
                path = spec if os.path.isabs(spec) else os.path.join(root, spec)
                loaded = _load_from_file(path)
            else:
                loaded = _load_from_entrypoint(spec)
            if not loaded:
                warnings.append(f"plugin {spec!r} defines no Plugin subclass")
            for p in loaded:
                if getattr(p, "api_version", None) != API_VERSION:
                    warnings.append(
                        f"plugin {p.name!r} targets api_version "
                        f"{getattr(p, 'api_version', '?')}, core is {API_VERSION} — not loaded")
                    continue
                plugins.append(p)
        except Exception as exc:                  # noqa: BLE001
            warnings.append(f"plugin {spec!r} failed to load: {exc}")
    return PluginHost(plugins, warnings)


class PluginHost:
    """Dispatches hooks, swallowing per-plugin failures."""

    def __init__(self, plugins: List[Plugin], warnings: List[str]) -> None:
        self.plugins = plugins
        self.warnings = list(warnings)

    def __bool__(self) -> bool:
        return bool(self.plugins)

    @property
    def names(self) -> List[str]:
        return [p.name for p in self.plugins]

    def _guard(self, plugin: Plugin, hook: str, fn, *args):
        try:
            return fn(*args)
        except Exception as exc:                  # noqa: BLE001
            self.warnings.append(f"plugin {plugin.name!r} {hook}() failed: {exc}")
            return None

    # -- hooks ------------------------------------------------------------
    def on_index(self, ctx: IndexContext) -> None:
        for p in self.plugins:
            self._guard(p, "on_index", p.on_index, ctx)

    def identity(self, raw: Dict[str, Any], path: str) -> Optional[Identity]:
        for p in self.plugins:
            ident = self._guard(p, "identity", p.identity, raw, path)
            if isinstance(ident, Identity):
                return ident
        return None

    def on_package(self, pkg: Package, raw: Dict[str, Any]) -> None:
        for p in self.plugins:
            self._guard(p, "on_package", p.on_package, pkg, raw)

    def facets(self) -> List[Facet]:
        out: List[Facet] = []
        for p in self.plugins:
            res = self._guard(p, "facets", p.facets)
            if res:
                out.extend(res)
        return out

    def detail_blocks(self, pkg: Package) -> List[Block]:
        out: List[Block] = []
        for p in self.plugins:
            res = self._guard(p, "detail_blocks", p.detail_blocks, pkg)
            for block in res or []:
                if not block.plugin:
                    block.plugin = p.name
                out.append(block)
        return out

    def row(self, pkg: Package) -> Optional[RowSpec]:
        for p in self.plugins:
            spec = self._guard(p, "row", p.row, pkg)
            if isinstance(spec, RowSpec):
                return spec
        return None

    def enrich_remote(self, packages: List[Package], http: Any) -> None:
        for p in self.plugins:
            self._guard(p, "enrich_remote", p.enrich_remote, packages, http)
