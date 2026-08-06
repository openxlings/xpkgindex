"""`.xpkgindex.json` loading.

The schema grew (plugins / install disclosure / guides / ecosystem / theme
tokens) but old configs keep working: every new key has a fallback to the
pre-existing one, so an index repo that has not been updated still renders.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CONFIG_NAME = ".xpkgindex.json"


@dataclass
class InstallCommand:
    os: str                      # human label, e.g. "Windows · PowerShell"
    command: str
    id: str = ""                 # machine key: unix | linux | macos | windows

    def __post_init__(self) -> None:
        if not self.id:
            self.id = _infer_os_id(self.os)


def _infer_os_id(label: str) -> str:
    """Derive the match key from the human label so existing configs that only
    write `os` still get OS detection."""
    low = (label or "").lower()
    if "win" in low:
        return "windows"
    if "mac" in low or "osx" in low or "darwin" in low:
        return "macos" if "linux" not in low else "unix"
    if "linux" in low or "unix" in low:
        return "unix" if "mac" in low or "unix" in low else "linux"
    return "any"


@dataclass
class InstallSection:
    label: str = ""
    command: str = ""            # OS-independent primary, optional
    summary: str = ""
    fallback: List[InstallCommand] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.command or self.fallback)


@dataclass
class GuideEntry:
    slug: str
    title: str
    path: str
    translations: Dict[str, str] = field(default_factory=dict)


@dataclass
class SiteConfig:
    # -- identity ---------------------------------------------------------
    title: str = "Package Index"
    description: str = ""
    logo: str = "Package Index"

    # -- links ------------------------------------------------------------
    github: str = ""
    forum: str = ""
    website: str = ""          # the project's own site, not this index
    docs_url: str = ""
    custom_links: List[Dict[str, str]] = field(default_factory=list)

    # -- about ------------------------------------------------------------
    project_name: str = ""
    project_url: str = ""
    about_description: str = ""
    maintainers: List[str] = field(default_factory=list)
    license: str = ""

    # -- theme ------------------------------------------------------------
    accent: str = ""
    style: str = "auto"                       # auto | light | dark
    tones: Dict[str, str] = field(default_factory=dict)
    dark_accent: str = ""
    dark_tones: Dict[str, str] = field(default_factory=dict)
    # How long the day/night swap takes, and on what curve. Long by default:
    # an instant repaint of a whole page reads as a glitch, a slow cross-fade
    # reads as a deliberate change of light. An index that wants it snappy
    # sets `theme.transition.duration` to something short — or "0s" to switch
    # instantly, which is also what a visitor with reduced-motion always gets.
    theme_fade: str = "2s"
    theme_ease: str = "cubic-bezier(.45, .05, .25, 1)"
    density: str = "comfortable"

    # -- build ------------------------------------------------------------
    pkgs_dir: str = "pkgs"
    list_variant: str = "code"     # code | card — plugins may override per package
    # Extra growth-chart lines, each a facet filter. The total is always drawn
    # first; these are added on top.
    growth_series: List[Dict[str, str]] = field(default_factory=list)
    growth_total_label: str = ""
    install_command_template: str = "{ref}@{version}"
    install: InstallSection = field(default_factory=InstallSection)
    plugins: List[str] = field(default_factory=list)
    # A string, or a per-locale map. Consumer-supplied text is never
    # machine-translated, but an index that wants its section named in each
    # language can say so; leaving it out uses the framework's own label.
    guides_nav_label: Any = ""
    guides: List[GuideEntry] = field(default_factory=list)
    # The doc a newcomer should read first. Rendered like any other page, but
    # it also becomes the homepage call to action and the Docs nav target.
    docs_landing: str = ""
    docs_cta_label: str = ""
    # Free-form card contents: eyebrow / title / description / lines / action.
    # All optional; the card falls back to a single "Quick start" label.
    docs_cta: Dict[str, Any] = field(default_factory=dict)
    ecosystem_owners: List[str] = field(default_factory=list)
    ecosystem_repos: List[str] = field(default_factory=list)
    identities_path: str = ".xpkgindex/identities.json"
    cache_path: str = ".xpkgindex/cache/github.json"
    base_url: str = ""
    # Framework chrome locales. The first is the default and lives at the site
    # root; the others are generated under /<tag>/. An index that configures
    # nothing stays single-language, exactly as before.
    languages: List[str] = field(default_factory=lambda: ["en"])

    # -- source -----------------------------------------------------------
    root: str = "."

    @property
    def repo_slug(self) -> str:
        """`owner/name` parsed off the configured GitHub link, if any."""
        if not self.github:
            return ""
        parts = [p for p in self.github.replace("https://", "").split("/") if p]
        if len(parts) >= 3 and parts[0].endswith("github.com"):
            return f"{parts[1]}/{parts[2]}"
        return ""


def _load_install(data: Dict[str, Any]) -> InstallSection:
    """New `install` block, falling back to the legacy `install_commands` map."""
    raw = data.get("install")
    if isinstance(raw, dict):
        primary = raw.get("primary") or {}
        fb = raw.get("fallback") or {}
        # `install.os` is the per-platform list; `install.fallback.commands` is
        # the older spelling and means the same thing.
        entries = raw.get("os") or fb.get("commands") or []
        return InstallSection(
            label=primary.get("label", "") or raw.get("label", ""),
            command=primary.get("command", ""),
            summary=fb.get("summary", "") or raw.get("summary", ""),
            fallback=[
                InstallCommand(os=c.get("os", ""), command=c.get("command", ""),
                               id=c.get("id", ""))
                for c in entries
                if c.get("command")
            ],
        )

    legacy = data.get("install_commands") or {}
    if not legacy:
        return InstallSection()
    label_map = {"unix": "Linux / macOS", "windows": "Windows"}
    cmds = [InstallCommand(os=label_map.get(k, k), command=v) for k, v in legacy.items() if v]
    # No primary/fallback split in the legacy shape: show them all as fallback
    # entries under a neutral summary so nothing silently disappears.
    return InstallSection(summary="Install commands", fallback=cmds)


def _load_guides(data: Dict[str, Any]) -> (str, List[GuideEntry]):
    # `docs` is the current spelling; `guides` is the older one and means the
    # same thing, so existing configs keep working.
    guides = data.get("docs") or data.get("guides")
    if not isinstance(guides, dict):
        return "", []
    entries = []
    for e in guides.get("entries", []):
        if not (e.get("slug") and e.get("path")):
            continue
        entries.append(GuideEntry(
            slug=e["slug"],
            title=e.get("title", e["slug"]),
            path=e["path"],
            translations=e.get("translations", {}) or {},
        ))
    return guides.get("nav_label", ""), entries


def load_config(directory: str, config_path: Optional[str] = None) -> SiteConfig:
    """Load `.xpkgindex.json` from `directory` (or an explicit file path)."""
    path = config_path or os.path.join(directory, CONFIG_NAME)
    cfg = SiteConfig(root=os.path.abspath(directory))
    if not os.path.exists(path):
        return cfg

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    site = data.get("site", {})
    cfg.title = site.get("title", cfg.title)
    cfg.description = site.get("description", cfg.description)
    cfg.logo = site.get("logo", cfg.title)

    links = data.get("links", {})
    cfg.github = links.get("github", "")
    cfg.forum = links.get("forum", "")
    cfg.website = links.get("website", "")
    cfg.docs_url = links.get("docs", "")
    cfg.custom_links = links.get("custom", []) or []

    about = data.get("about", {})
    cfg.project_name = about.get("project_name", "")
    cfg.project_url = about.get("project_url", "")
    cfg.about_description = about.get("description", "")
    cfg.maintainers = about.get("maintainers", []) or []
    cfg.license = about.get("license", "")

    theme = data.get("theme", {})
    cfg.accent = theme.get("accent", theme.get("primary_color", cfg.accent))
    cfg.style = theme.get("style", cfg.style)
    cfg.tones = theme.get("tones", {}) or {}
    dark = theme.get("dark", {}) or {}
    cfg.dark_accent = dark.get("accent", "")
    cfg.dark_tones = dark.get("tones", {}) or {}
    fade = theme.get("transition", {}) or {}
    cfg.theme_fade = str(fade.get("duration", cfg.theme_fade))
    cfg.theme_ease = str(fade.get("easing", cfg.theme_ease))
    cfg.density = theme.get("density", cfg.density)

    cfg.pkgs_dir = data.get("pkgs_dir", cfg.pkgs_dir)
    cfg.list_variant = (data.get("list") or {}).get("variant", cfg.list_variant)

    growth = data.get("growth") or {}
    cfg.growth_total_label = growth.get("total_label", "")
    cfg.growth_series = [s for s in (growth.get("series") or []) if s.get("facet")]
    cfg.install_command_template = data.get(
        "install_command_template", cfg.install_command_template)
    cfg.install = _load_install(data)
    cfg.plugins = data.get("plugins", []) or []
    cfg.guides_nav_label, cfg.guides = _load_guides(data)
    docs_cfg = data.get("docs") or data.get("guides") or {}
    cfg.docs_landing = docs_cfg.get("landing", "")
    cfg.docs_cta_label = docs_cfg.get("cta_label", "")
    cfg.docs_cta = docs_cfg.get("cta") or {}

    eco = data.get("ecosystem", {}) or {}
    cfg.ecosystem_owners = eco.get("owners", []) or []
    cfg.ecosystem_repos = eco.get("repos", []) or []

    from .i18n import available
    cfg.languages = available(data.get("languages") or cfg.languages)

    cfg.identities_path = data.get("identities_path", cfg.identities_path)
    cfg.cache_path = data.get("cache_path", cfg.cache_path)
    cfg.base_url = data.get("base_url", "")

    return cfg
