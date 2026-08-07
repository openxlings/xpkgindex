"""Core data model.

Everything here is ecosystem-agnostic. No field in this module may encode the
semantics of a specific package manager — those live in plugins, reachable
through ``Package.extensions`` / ``Package.blocks`` / ``Package.facets``.

See .agents/docs/2026-08-06-xpkgindex-framework-and-site-redesign-design.md §4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Identity:
    """How a package is named — three separate concerns that must not be
    derived from one another (design §4.1).

    ``display``      what humans read on the page
    ``slug``         the URL segment; unique across the whole site
    ``install_ref``  what the client CLI actually accepts

    The core NEVER joins ``namespace`` into any of them: mcpp treats the
    namespace as part of the package identity (``nlohmann.json``) while xlings
    treats it as a classification label and resolves ``ns:name`` against the
    *index repo* name. A plugin opts in explicitly via ``Plugin.identity()``.
    """

    namespace: str = ""
    name: str = ""
    display: str = ""
    slug: str = ""
    install_ref: str = ""

    @classmethod
    def plain(cls, namespace: str, name: str) -> "Identity":
        """Core default: the namespace is metadata only."""
        return cls(namespace=namespace, name=name,
                   display=name, slug=name, install_ref=name)

    @classmethod
    def joined(cls, namespace: str, name: str, sep: str = ".") -> "Identity":
        """Namespace participates in the identity (mcpp-style)."""
        full = f"{namespace}{sep}{name}" if namespace else name
        return cls(namespace=namespace, name=name,
                   display=full, slug=full, install_ref=full)

    def with_slug(self, slug: str) -> "Identity":
        """Disambiguate the URL without touching the install command."""
        return Identity(self.namespace, self.name, self.display, slug, self.install_ref)

    @property
    def display_parts(self) -> Tuple[str, str]:
        """Split for rendering — ("nlohmann.", "json"), prefix may be empty."""
        if self.display.endswith(self.name) and len(self.display) > len(self.name):
            return self.display[: -len(self.name)], self.name
        return "", self.display


# --------------------------------------------------------------------------
# Versions / platforms
# --------------------------------------------------------------------------

@dataclass
class Version:
    version: str
    platforms: List[str] = field(default_factory=list)
    urls: Dict[str, str] = field(default_factory=dict)   # mirror key -> url
    sha256: str = ""

    @property
    def mirrors(self) -> List[str]:
        return sorted(k for k in self.urls if k != "DEFAULT")


@dataclass
class PlatformInfo:
    versions: List[str] = field(default_factory=list)
    latest: str = ""
    deps: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------

@dataclass
class Person:
    key: str                       # canonical identity key
    login: str = ""                # GitHub login when known
    name: str = ""
    email: str = ""
    avatar: str = ""
    url: str = ""
    commits: int = 0
    packages: List[str] = field(default_factory=list)
    repos: List[str] = field(default_factory=list)      # ecosystem membership
    names: List[str] = field(default_factory=list)      # every git author name merged in
    first_seen: str = ""
    last_seen: str = ""

    @property
    def label(self) -> str:
        return self.login or self.name or self.key


@dataclass
class UpstreamProject:
    owner: str
    url: str = ""
    host: str = "github.com"
    avatar: str = ""
    description: str = ""
    stars: Optional[int] = None
    packages: List[str] = field(default_factory=list)
    is_own: bool = False           # belongs to this ecosystem, not a third party


# --------------------------------------------------------------------------
# Plugin output
# --------------------------------------------------------------------------

@dataclass
class Block:
    """Structured detail-page content produced by a plugin.

    Plugins do not write HTML: the core renders ``kind`` with its own design
    system, and the block travels verbatim into index.json so a future server
    API carries it too. ``template``/``styles`` are the explicit escape hatch.
    """

    kind: str                      # kv | code | table | list | callout
    title: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    plugin: str = ""
    collapsed: bool = False
    template: Optional[str] = None
    styles: Optional[str] = None
    weight: int = 100


@dataclass
class RowSpec:
    """How one package appears in the listing.

    The listing row is the densest, most-read surface on the site, and what
    belongs on it is ecosystem-specific: mcpp leads with the line you write
    (`import nlohmann.json;`), xlings with the binary you get (`$ gcc`),
    and a future index might lead with something else entirely. So the row is
    a plugin-owned spec rather than a fixed template — same contract as
    `Block`, including the explicit template escape hatch.
    """

    # Empty means "use the site default"; a plugin sets it only when the
    # layout is part of what it is expressing.
    variant: str = ""              # code | card — the two shipped layouts
    tone: str = "neutral"
    lead: str = ""                 # short labelled badge, e.g. "import"

    # The two lines have fixed meanings, and every row fills both the same
    # way — a row where line 2 sometimes held the install command and
    # sometimes the usage line made the layout unreadable.
    code: str = ""                 # how you consume it: `import x;` / `#include <x>`
    install: str = ""              # how you add it: `mcpp add x@1.0`
    code_muted: bool = False       # the consumption line is a placeholder, not a fact

    note: str = ""
    badges: List[str] = field(default_factory=list)
    template: Optional[str] = None
    styles: Optional[str] = None


@dataclass
class FacetValue:
    key: str
    label: str = ""
    count: int = 0
    tone: str = ""                 # semantic color token name


@dataclass
class Facet:
    key: str
    label: str = ""
    # Core axes carry a translation key instead of a literal; plugin axes keep
    # whatever wording the ecosystem chose, untranslated by design.
    label_key: str = ""
    values: List[FacetValue] = field(default_factory=list)
    weight: int = 100


# --------------------------------------------------------------------------
# Package
# --------------------------------------------------------------------------

@dataclass
class Package:
    identity: Identity = field(default_factory=Identity)
    description: str = ""
    homepage: str = ""
    repo: str = ""
    docs: str = ""
    licenses: List[str] = field(default_factory=list)
    type: str = "package"
    status: str = ""
    platforms: Dict[str, PlatformInfo] = field(default_factory=dict)
    versions: List[Version] = field(default_factory=list)
    latest: str = ""
    deps: List[str] = field(default_factory=list)
    required_by: List[str] = field(default_factory=list)

    facets: Dict[str, str] = field(default_factory=dict)
    extensions: Dict[str, Any] = field(default_factory=dict)
    blocks: List[Block] = field(default_factory=list)
    row: Optional["RowSpec"] = None

    people: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)

    source_file: str = ""          # repo-relative path of the descriptor
    raw: Dict[str, Any] = field(default_factory=dict)

    # A descriptor without a `namespace` is not un-namespaced: it falls into
    # the index's default namespace (`xim` for xim-pkgindex, `mcpplibs` for
    # mcpp-index). That is display and grouping only — it must never reach
    # `identity.slug` or `identity.install_ref`.
    effective_namespace: str = ""
    namespace_implicit: bool = False

    # -- convenience ------------------------------------------------------
    @property
    def slug(self) -> str:
        return self.identity.slug

    @property
    def display(self) -> str:
        return self.identity.display

    @property
    def name(self) -> str:
        return self.identity.name

    @property
    def namespace(self) -> str:
        return self.identity.namespace

    @property
    def url(self) -> str:
        return f"packages/{self.identity.slug}/"

    def sorted_blocks(self) -> List[Block]:
        return sorted(self.blocks, key=lambda b: b.weight)

    @property
    def install_command(self) -> str:
        return self.extensions.get("_core", {}).get("install_command", "")

    @property
    def interface(self) -> Optional[Block]:
        """The one line a user actually writes to consume this package.

        A plugin marks it by emitting a code block with `data.role ==
        "interface"`; the core shows it as the headline of the list row and at
        the top of the detail page. Without a plugin there is simply no such
        line and the row falls back to the install command.
        """
        for block in self.blocks:
            if block.kind == "code" and block.data.get("role") == "interface":
                return block
        return None

    @property
    def tone(self) -> str:
        block = self.interface
        if block and block.data.get("tone"):
            return str(block.data["tone"])
        return "neutral"

    def detail_blocks(self) -> List[Block]:
        """Blocks for the detail page body — the interface line is rendered
        separately in the header, so it is excluded here."""
        iface = self.interface
        return [b for b in self.sorted_blocks() if b is not iface]


# --------------------------------------------------------------------------
# Index-level metadata (plugins fill this in via on_index)
# --------------------------------------------------------------------------

@dataclass
class IndexMeta:
    fields: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.fields[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)


# --------------------------------------------------------------------------
# Site derived data
# --------------------------------------------------------------------------

@dataclass
class GrowthPoint:
    date: str
    count: int
    added: int = 0
    removed: int = 0


@dataclass
class GrowthSeries:
    """One line on the growth chart.

    A single total says the index grew; several say *what* grew — on
    mcpp-index the interesting question is whether the importable-module count
    is moving or only the compat layer.
    """

    key: str
    label: str
    points: List[GrowthPoint] = field(default_factory=list)
    tone: str = ""                 # design-system token, e.g. "module"
    color: str = ""                # explicit override

    @property
    def last(self) -> int:
        return self.points[-1].count if self.points else 0


@dataclass
class HistoryEvent:
    date: str                      # YYYY-MM-DD, the key the growth curve groups by
    kind: str                      # added | updated | removed
    slug: str = ""
    display: str = ""
    by: str = ""
    subject: str = ""
    at: str = ""                   # full author timestamp, ISO 8601

    @property
    def clock(self) -> str:
        """HH:MM from the full timestamp; empty when only a date is known."""
        return self.at[11:16] if len(self.at) >= 16 else ""


@dataclass
class SiteData:
    """Everything the templates need, assembled once."""

    packages: List[Package] = field(default_factory=list)
    facets: List[Facet] = field(default_factory=list)
    index_meta: IndexMeta = field(default_factory=IndexMeta)
    growth: List[GrowthPoint] = field(default_factory=list)
    growth_series: List[GrowthSeries] = field(default_factory=list)
    history: List[HistoryEvent] = field(default_factory=list)
    contributors: List[Person] = field(default_factory=list)
    upstreams: List[UpstreamProject] = field(default_factory=list)
    ecosystem: List[Person] = field(default_factory=list)
    ecosystem_repos: List[Dict[str, Any]] = field(default_factory=list)
    guides: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    build: Dict[str, str] = field(default_factory=dict)

    # -- stats ------------------------------------------------------------
    @property
    def total_packages(self) -> int:
        return len(self.packages)

    @property
    def total_namespaces(self) -> int:
        return len({p.effective_namespace for p in self.packages if p.effective_namespace})

    @property
    def total_versions(self) -> int:
        """Distinct (package, version) pairs — NOT version x platform rows."""
        return sum(len(p.versions) for p in self.packages)
