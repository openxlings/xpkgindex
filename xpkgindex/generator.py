"""Site generator: parse packages → render templates → output static site."""

import json
import os
import shutil
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader

from .config import load_config
from .lua_parser import parse_packages_dir
from .models import Package, SiteConfig


def _read_build_info() -> Optional[dict]:
    """Pick up build provenance from the environment if any of the well-known
    XPKGINDEX_BUILD_* variables are set. Returns None when nothing is set so
    the about template can omit the section entirely.
    """
    time = os.environ.get("XPKGINDEX_BUILD_TIME")
    commit = os.environ.get("XPKGINDEX_BUILD_COMMIT")
    commit_url = os.environ.get("XPKGINDEX_BUILD_COMMIT_URL")
    if not (time or commit):
        return None
    return {
        "time": time or "",
        "commit": commit or "",
        "commit_short": (commit or "")[:7],
        "commit_url": commit_url or "",
    }


def _safe_filename(name: str) -> str:
    """Sanitize a package name for use as a filename."""
    return name.replace("/", "_").replace("\\", "_").replace(" ", "-").lower()


def _get_template_dir() -> str:
    """Get the path to the templates directory shipped with the package."""
    return os.path.join(os.path.dirname(__file__), "templates")


def _get_static_dir() -> str:
    """Get the path to the static directory shipped with the package."""
    return os.path.join(os.path.dirname(__file__), "static")


def _collect_categories(packages: List[Package]) -> List[str]:
    """Collect and sort all unique categories across packages."""
    cats = set()
    for pkg in packages:
        cats.update(pkg.categories)
    return sorted(cats)


def _package_to_json_dict(pkg: Package, config: SiteConfig) -> dict:
    """Convert a Package to a JSON-serializable dict for packages.json."""
    platforms = {}
    all_versions = set()
    latest = ""
    all_deps = []

    for pname, pinfo in pkg.platforms.items():
        platforms[pname] = {
            "versions": pinfo.versions,
            "latest_version": pinfo.latest_version,
            "deps": pinfo.deps,
        }
        all_versions.update(pinfo.versions)
        if pinfo.latest_version and not latest:
            latest = pinfo.latest_version
        all_deps.extend(pinfo.deps)

    return {
        "name": pkg.name,
        "description": pkg.description,
        "homepage": pkg.homepage,
        "repo": pkg.repo,
        "docs": pkg.docs,
        "licenses": pkg.licenses,
        "type": pkg.type,
        "status": pkg.status,
        "categories": pkg.categories,
        "keywords": pkg.keywords,
        "authors": pkg.authors,
        "maintainers": pkg.maintainers,
        "programs": pkg.programs,
        "archs": pkg.archs,
        "xvm_enable": pkg.xvm_enable,
        "platforms": list(platforms.keys()),
        "latest_version": latest,
        "all_versions": sorted(all_versions),
        "deps": sorted(set(all_deps)),
        "install_command": config.install_command_template.format(
            name=pkg.name, version=latest or "latest"
        ),
    }


def _make_install_command(pkg: Package, config: SiteConfig) -> str:
    """Generate the install command for a package."""
    latest = ""
    for pinfo in pkg.platforms.values():
        if pinfo.latest_version:
            latest = pinfo.latest_version
            break
    return config.install_command_template.format(
        name=pkg.name, version=latest or "latest"
    )


def generate(pkgindex_dir: str, output_dir: str, config_path: str = None):
    """Generate the static site.

    Args:
        pkgindex_dir: Path to the package index repo (containing pkgs/ dir)
        output_dir: Path to write the generated site
        config_path: Optional path to config file (default: pkgindex_dir/.xpkgindex.json)
    """
    # Load config
    config_dir = os.path.dirname(config_path) if config_path else pkgindex_dir
    config = load_config(config_dir if not config_path else os.path.dirname(config_path))
    if config_path and os.path.exists(config_path):
        import json as _json
        with open(config_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
        # Re-load using the explicit config path's directory
        config = load_config(os.path.dirname(os.path.abspath(config_path)))
    else:
        config = load_config(pkgindex_dir)

    # Parse packages
    pkgs_dir = os.path.join(pkgindex_dir, config.pkgs_dir)
    if not os.path.isdir(pkgs_dir):
        print(f"Error: packages directory not found: {pkgs_dir}")
        return

    print(f"Parsing packages from {pkgs_dir}...")
    packages = parse_packages_dir(pkgs_dir)
    packages.sort(key=lambda p: p.name.lower())
    print(f"Found {len(packages)} packages")

    # Setup output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "packages"), exist_ok=True)

    # Setup Jinja2
    template_dir = _get_template_dir()
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["safe_filename"] = _safe_filename

    categories = _collect_categories(packages)

    # Render index.html
    print("Rendering index.html...")
    index_tmpl = env.get_template("index.html")
    index_html = index_tmpl.render(
        config=config,
        packages=packages,
        total_packages=len(packages),
        total_categories=len(categories),
        categories=categories,
        current_page="home",
    )
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Render package detail pages
    print("Rendering package pages...")
    pkg_tmpl = env.get_template("package.html")
    for pkg in packages:
        install_cmd = _make_install_command(pkg, config)
        pkg_html = pkg_tmpl.render(
            config=config,
            package=pkg,
            install_command=install_cmd,
            current_page="package",
        )
        safe_name = _safe_filename(pkg.name)
        with open(os.path.join(output_dir, "packages", f"{safe_name}.html"), "w", encoding="utf-8") as f:
            f.write(pkg_html)

    # Render about.html
    print("Rendering about.html...")
    about_tmpl = env.get_template("about.html")
    about_html = about_tmpl.render(
        config=config,
        current_page="about",
        build_info=_read_build_info(),
    )
    with open(os.path.join(output_dir, "about.html"), "w", encoding="utf-8") as f:
        f.write(about_html)

    # Generate packages.json
    print("Generating packages.json...")
    packages_json = [_package_to_json_dict(pkg, config) for pkg in packages]
    with open(os.path.join(output_dir, "packages.json"), "w", encoding="utf-8") as f:
        json.dump(packages_json, f, ensure_ascii=False, indent=2)

    # Copy static assets
    print("Copying static assets...")
    static_src = _get_static_dir()
    static_dst = os.path.join(output_dir, "static")
    if os.path.exists(static_dst):
        shutil.rmtree(static_dst)
    shutil.copytree(static_src, static_dst)

    print(f"Site generated: {output_dir}")
    print(f"  {len(packages)} packages, {len(categories)} categories")
