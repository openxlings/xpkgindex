"""Render `SiteData` into a static site.

URLs are directory-shaped (`/packages/<slug>/`) rather than `<slug>.html`:
that is the form a server can take over later without breaking a single link,
and it leaves room for sub-pages without another migration.

When several UI locales are configured, the whole site is generated once per
locale — the default at the root, the rest under `/<tag>/`. Each locale is
complete static HTML, so a translated page is indexable and shareable rather
than a client-side re-render.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import charts, i18n, serialize
from .config import SiteConfig
from .models import Package, SiteData


def _here(*parts: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


PLATFORM_LABELS = {"linux": "Linux", "windows": "Windows", "macosx": "macOS"}


def _env(lang: str = i18n.DEFAULT, default: str = i18n.DEFAULT) -> Environment:
    env = Environment(
        loader=FileSystemLoader(_here("templates")),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["platform_label"] = lambda p: PLATFORM_LABELS.get(p, p)
    # `loc` unwraps any consumer- or plugin-supplied value that was written
    # per locale. Applied wherever such text reaches a template.
    env.filters["loc"] = lambda v: i18n.localize(v, lang, default)
    return env


class Renderer:
    """One locale's worth of pages."""

    def __init__(self, site: SiteData, config: SiteConfig, out: str,
                 lang: str, langs: List[str], write_data: bool) -> None:
        self.site = site
        self.config = config
        self.out = out
        self.lang = lang
        self.langs = langs
        self.default = langs[0]
        self.prefix = "" if lang == self.default else f"{lang}/"
        self.write_data = write_data
        self.env = _env(lang, langs[0])
        # The JSON documents are written once, in the site's default language.
        serialize.set_locale(self.default)
        self.t = i18n.Translator(lang)
        self.asset_v = self.asset_version()

    # -- helpers ----------------------------------------------------------
    def _lang_links(self, page_path: str) -> List[Dict[str, str]]:
        """Same page, other locales. Depth is measured inside the locale, so a
        link out of `/zh/packages/x/` has to climb one extra level."""
        up = "../" * (page_path.count("/") + (1 if self.prefix else 0))
        links = []
        for code in self.langs:
            url = up + ("" if code == self.default else f"{code}/") + page_path
            links.append({
                "code": code,
                "name": i18n.LANGUAGE_NAMES.get(code, code),
                "current": code == self.lang,
                # "./" rather than "": the default locale's own homepage
                # resolves to an empty string, which is not a valid href and
                # gave the language redirect an empty target to jump to.
                "url": url or "./",
            })
        return links

    def _docs_nav_label(self) -> str:
        """The Docs section's name in this locale.

        A plain string in the config is used as-is (the index chose that
        wording); a per-locale map is looked up; nothing at all falls back to
        the framework's translated label, which is what most indexes want.
        """
        label = self.config.guides_nav_label
        if isinstance(label, dict):
            for key in (self.lang, self.lang.split("-")[0]):
                if label.get(key):
                    return label[key]
            return self.t("nav.docs_section")
        return label or self.t("nav.docs_section")

    def _docs_home(self) -> str:
        """The doc the Docs nav and the homepage call to action point at.

        The configured landing page when it exists, otherwise simply the first
        one — a site should never link to a Docs section that 404s.
        """
        slugs = [g["slug"] for g in self.site.guides]
        if self.config.docs_landing in slugs:
            return self.config.docs_landing
        return slugs[0] if slugs else ""

    def _ctx(self, page_path: str, page: str, **extra: Any) -> Dict[str, Any]:
        depth = page_path.count("/")
        root = "../" * depth
        ctx = {
            "site": self.site,
            "config": self.config,
            "root": root,                       # links inside this locale
            "site_root": root + ("../" if self.prefix else ""),   # shared assets/data
            "page": page,
            "asset_v": self.asset_v,
            "docs_home": self._docs_home(),
            "docs_nav_label": self._docs_nav_label(),
            "docs_titles": {g["slug"]: self._guide_title(g) for g in self.site.guides},
            "t": self.t,
            "lang": self.lang,
            "html_lang": self.t.html_lang,
            "languages": self._lang_links(page_path),
            "stats": {
                "packages": self.site.total_packages,
                "namespaces": self.site.total_namespaces,
                "versions": self.site.total_versions,
            },
        }
        ctx.update(extra)
        return ctx

    def _render(self, template: str, page_path: str, page: str, **extra: Any) -> None:
        """`page_path` is locale-relative and ends in `/` for directory pages."""
        html = self.env.get_template(template).render(**self._ctx(page_path, page, **extra))
        rel = page_path + "index.html" if page_path.endswith("/") or not page_path else page_path
        _write(os.path.join(self.out, self.prefix + rel), html)

    # -- pages ------------------------------------------------------------
    def _latest_per_package(self, limit: int) -> List[Any]:
        """One entry per package, newest first.

        A version bump touches several descriptors in one commit, so the raw
        stream repeats the same package and the homepage ends up showing one
        afternoon's work eight times over. The full stream stays on /stats/
        and on each package page.
        """
        seen, out = set(), []
        for ev in self.site.history:
            key = ev.slug or ev.display
            if key in seen:
                continue
            seen.add(key)
            out.append(ev)
            if len(out) >= limit:
                break
        return out

    def home(self) -> None:
        self._render("index.html", "", "home",
                     growth=charts.growth_chart(self.site.growth_series, width=560, height=170,
                                                gradient_id="g-home"),
                     recent=self._latest_per_package(8))

    def packages(self) -> None:
        for pkg in self.site.packages:
            self._render("package.html", f"packages/{pkg.slug}/", "packages", pkg=pkg)
            if self.write_data:
                _write_json(os.path.join(self.out, "packages", pkg.slug, "index.json"),
                            serialize.package_dict(pkg))

    def stats(self) -> None:
        by_ns: Dict[str, int] = {}
        for pkg in self.site.packages:
            ns = pkg.effective_namespace or "(none)"
            by_ns[ns] = by_ns.get(ns, 0) + 1
        self._render("stats.html", "stats/", "stats",
                     growth=charts.growth_chart(self.site.growth_series, width=1000, height=280,
                                                gradient_id="g-stats"),
                     by_namespace=sorted(by_ns.items(), key=lambda kv: -kv[1]),
                     history=self.site.history[:80])

    def contributors(self) -> None:
        self._render("contributors.html", "contributors/", "contributors",
                     upstreams=[u for u in self.site.upstreams if not u.is_own],
                     own=[u for u in self.site.upstreams if u.is_own])

    def guides(self) -> None:
        # Titles follow the locale: a doc that ships a translation names
        # itself in that language, in the sidebar as well as on the page.
        for guide in self.site.guides:
            self._render("guide.html", f"docs/{guide['slug']}/", "docs",
                         guide=guide, body=self._guide_body(guide))

    def _guide_title(self, guide: Dict[str, Any]) -> str:
        """What this doc is called in this locale.

        A configured title that names this locale explicitly wins: it is the
        short label an index writes *for the navigation*, and it is the only
        thing that can be right when the doc itself is not translated — a
        Traditional Chinese reader gets a Traditional label above a Simplified
        document rather than nothing.

        Otherwise the doc's own H1, which is at least in the language the doc
        is actually written in. The configured title is the last resort, and
        deliberately so: a single English string used to caption every
        translation of a page.
        """
        title = guide["title"]
        if isinstance(title, dict):
            for key in (self.lang, self.lang.split("-")[0]):
                if title.get(key):
                    return title[key]
        body = self._guide_body(guide)
        return body.get("heading") or i18n.localize(title, self.lang, self.default)

    def _guide_body(self, guide: Dict[str, Any]) -> Dict[str, Any]:
        """Use the consumer's translation for this locale when it exists.

        The framework never translates guide prose itself: an index that ships
        only English docs shows English docs in every locale, which is honest
        about what the maintainers actually wrote.
        """
        translations = guide.get("translations") or {}
        for key in (self.lang, self.lang.split("-")[0]):
            if key in translations:
                return translations[key]
        return guide

    def about(self) -> None:
        self._render("about.html", "about/", "about")

    def aliases(self) -> None:
        """Old `packages/<short>.html` URLs are already linked to from outside.

        A unique short name redirects; an ambiguous one gets a disambiguation
        page instead of silently picking a winner — which is exactly the bug
        this redesign removes.
        """
        groups: Dict[str, List[Package]] = {}
        for pkg in self.site.packages:
            groups.setdefault(pkg.name.lower(), []).append(pkg)
        for short, group in groups.items():
            if len(group) == 1 and group[0].slug.lower() == short:
                continue                       # same URL, nothing to alias
            self._render("alias.html", f"packages/{short}.html", "packages",
                         short=short, group=group,
                         target=group[0] if len(group) == 1 else None)

    # -- data products ----------------------------------------------------
    def data(self) -> None:
        _write_json(os.path.join(self.out, "index.json"),
                    serialize.index_dict(self.site, self.config, self.default))
        _write_json(os.path.join(self.out, "search-index.json"),
                    serialize.search_index(self.site))
        _write_json(os.path.join(self.out, "packages.json"),
                    serialize.legacy_packages_json(self.site))

    def feeds(self) -> None:
        base = self.config.base_url.rstrip("/")
        paths = ["", "stats/", "contributors/", "about/"]
        paths += [f"packages/{p.slug}/" for p in self.site.packages]
        paths += [f"docs/{g['slug']}/" for g in self.site.guides]
        urls = list(paths)
        for lang in self.langs[1:]:
            urls += [f"{lang}/{p}" for p in paths]
        _write(os.path.join(self.out, "sitemap.xml"),
               self.env.get_template("sitemap.xml").render(base=base, urls=urls))
        _write(os.path.join(self.out, "feed.xml"),
               self.env.get_template("feed.xml").render(
                   base=base, config=self.config, events=self.site.history[:40]))

    def asset_version(self) -> str:
        """Short content hash for `?v=` on the CSS and JS links.

        Without it a browser keeps serving the previous stylesheet from cache
        after a redeploy — which is not a theoretical worry: a stale
        `site.css` made the package filter look broken while it was working
        perfectly, twice.
        """
        h = hashlib.sha256()
        for name in ("css/site.css", "js/site.js"):
            path = _here("static", *name.split("/"))
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    h.update(f.read())
        h.update(self._theme_css().encode("utf-8"))
        return h.hexdigest()[:10]

    def assets(self) -> None:
        dst = os.path.join(self.out, "static")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(_here("static"), dst)
        _write(os.path.join(dst, "css", "theme.css"), self._theme_css())

    def _theme_css(self) -> str:
        """Config-driven token overrides — layer 1 of theme customisation.

        Only what the site actually configures is emitted, so an index that
        sets nothing keeps every built-in token (including the dark-mode
        adjustments) intact.
        """
        cfg = self.config
        light = {**({"accent": cfg.accent} if cfg.accent else {}), **cfg.tones}
        dark = {**({"accent": cfg.dark_accent} if cfg.dark_accent else {}), **cfg.dark_tones}
        out = ["/* generated from .xpkgindex.json — theme tokens */",
               ":root {",
               f"  --theme-fade: {cfg.theme_fade};",
               f"  --theme-fade-ease: {cfg.theme_ease};",
               "}"]
        if light:
            out.append(":root {")
            out += [f"  --tone-{k}: {v};" for k, v in light.items()]
            out.append("}")
        if dark:
            out.append(':root[data-theme="dark"] {')
            out += [f"  --tone-{k}: {v};" for k, v in dark.items()]
            out.append("}")
        return "\n".join(out) + "\n"

    def run(self) -> None:
        os.makedirs(self.out, exist_ok=True)
        self.home()
        self.packages()
        self.stats()
        self.contributors()
        self.guides()
        self.about()
        self.aliases()
        if self.write_data:
            self.assets()
            self.data()
            self.feeds()


def render(site: SiteData, config: SiteConfig, out: str) -> None:
    langs = i18n.available(config.languages)
    for lang in langs:
        Renderer(site, config, out, lang, langs,
                 write_data=(lang == langs[0])).run()
