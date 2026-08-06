"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict

from . import __version__
from .build import BuildError, build
from .render import render


def _build_info() -> Dict[str, str]:
    """Provenance handed in by CI; absent locally, and that is fine."""
    info = {}
    time = os.environ.get("XPKGINDEX_BUILD_TIME", "")
    commit = os.environ.get("XPKGINDEX_BUILD_COMMIT", "")
    if time:
        info["time"] = time
    if commit:
        info["commit"] = commit
        info["commit_url"] = os.environ.get("XPKGINDEX_BUILD_COMMIT_URL", "")
    info["generator"] = f"xpkgindex {__version__}"
    return info


def _generate(args: argparse.Namespace) -> int:
    try:
        site, config = build(args.directory, args.config, offline=args.offline,
                             strict=args.strict, refresh=getattr(args, "refresh", False),
                             build_info=_build_info())
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.base_url:
        config.base_url = args.base_url
    render(site, config, args.output)

    print(f"generated {site.total_packages} packages -> {args.output}")
    print(f"  {site.total_namespaces} namespaces, {site.total_versions} versions, "
          f"{len(site.facets)} facet axes, {len(site.contributors)} contributors")
    for warning in site.warnings:
        print(f"  warning: {warning}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    code = _generate(args)
    if code:
        return code
    import functools
    import http.server
    import socketserver

    class Handler(http.server.SimpleHTTPRequestHandler):
        """Preview server. Nothing it serves may be cached.

        A page's filename never changes, so a browser that holds on to
        `index.html` keeps requesting the stylesheet hash that page was built
        with — and a rebuilt site looks like it did not rebuild at all. That
        is a preview-only concern, and a preview that lies is worse than a
        slow one.
        """

        def end_headers(self):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def log_message(self, fmt, *fmt_args):      # quieter than the default
            pass

    handler = functools.partial(Handler, directory=os.path.abspath(args.output))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"serving {args.output} at http://127.0.0.1:{args.port}/  (ctrl-c to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="xpkgindex",
        description="Static site generator for xpkg package indexes")
    parser.add_argument("--version", action="version", version=f"xpkgindex {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("directory", nargs="?", default=".",
                       help="index repository root (contains pkgs/)")
        p.add_argument("--output", "-o", default="site", help="output directory")
        p.add_argument("--config", "-c", default=None, help="explicit .xpkgindex.json path")
        p.add_argument("--offline", action="store_true",
                       help="never touch the network; use the committed cache only")
        p.add_argument("--strict", action="store_true",
                       help="treat reconciliation warnings as errors (CI)")
        p.add_argument("--refresh", action="store_true",
                       help="re-fetch every cached upstream lookup, ignoring freshness; "
                            "run this on demand and commit the updated cache")
        p.add_argument("--base-url", default="", help="absolute base URL for sitemap/feed")

    gen = sub.add_parser("generate", help="generate the static site")
    common(gen)
    gen.set_defaults(func=_generate)

    srv = sub.add_parser("serve", help="generate, then serve locally for review")
    common(srv)
    srv.add_argument("--port", "-p", type=int, default=8000)
    srv.set_defaults(func=_serve)

    args = parser.parse_args(argv)
    return args.func(args)
