# Deployment

**English** | [简体中文](zh/deployment.md)

The output is a plain directory. Anything that serves files serves it.

## GitHub Pages

```yaml
name: deploy-site

on:
  push:
    branches: [main]
    paths: ['pkgs/**', '.xpkgindex.json', '.xpkgindex/**', 'docs/**']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # the growth curve replays the whole log
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install git+https://github.com/openxlings/xpkgindex.git
      - name: Generate
        env:
          GITHUB_TOKEN:               ${{ secrets.GITHUB_TOKEN }}
          XPKGINDEX_BUILD_TIME:       ${{ github.event.head_commit.timestamp }}
          XPKGINDEX_BUILD_COMMIT:     ${{ github.sha }}
          XPKGINDEX_BUILD_COMMIT_URL: ${{ github.server_url }}/${{ github.repository }}/commit/${{ github.sha }}
        run: xpkgindex generate . --output site
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

**`fetch-depth: 0` is not optional.** The growth curve, the history line and
the contributor list are all replayed from the git log; a shallow clone
produces a curve that starts at the shallow boundary, and the build's own
reconciliation check will tell you so.

### Build provenance

Three environment variables, all optional, all surfaced on the About page and
in `index.json` under `site`:

| Variable | Becomes |
|---|---|
| `XPKGINDEX_BUILD_TIME` | when this site was built |
| `XPKGINDEX_BUILD_COMMIT` | which commit it was built from |
| `XPKGINDEX_BUILD_COMMIT_URL` | a link to that commit |

`workflow_dispatch` leaves `head_commit.timestamp` empty, so fill it in:

```bash
if [ -z "$XPKGINDEX_BUILD_TIME" ]; then
  XPKGINDEX_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ); export XPKGINDEX_BUILD_TIME
fi
```

## The network cache

`GITHUB_TOKEN` raises the API rate limit and enables the author→login mapping
that merges contributor identities. Without it the build still succeeds, with
fewer avatars and less merging.

The cache at `.xpkgindex/cache/github.json` is meant to be committed. It holds
projected fields only — logins, avatars, descriptions, star counts — so builds
are reproducible and survive an unauthenticated rate limit.

Refresh it deliberately rather than on every build:

```yaml
name: refresh-site-cache
on: { workflow_dispatch: }

jobs:
  refresh:
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install git+https://github.com/openxlings/xpkgindex.git
      - env: { GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}' }
        run: xpkgindex generate . --output /tmp/site --refresh
      - run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add .xpkgindex/cache
          git diff --staged --quiet || git commit -m "chore(site): refresh upstream cache"
          git push
```

Both live indexes ship exactly this, and both run it by hand when an upstream
manifest or a repository description has moved on.

## Validating in CI

Run the build on pull requests without publishing:

```yaml
- run: xpkgindex generate . --output /tmp/site --offline --strict
```

`--offline` keeps a PR from spending rate limit and makes the result depend
only on what is in the repository. `--strict` turns the growth reconciliation
warning into an error — if the replayed history disagrees with the tree, the
curve on the site would be wrong, and that is worth failing a build over.

Warnings that are not errors are printed by `generate`; a PR check that greps
its output for `warning:` is a reasonable extra guard.

## Anywhere else

```bash
xpkgindex generate . --output site --base-url https://packages.example.org
```

`--base-url` is only used by `sitemap.xml` and `feed.xml` — every link inside
the site is relative, so the same output works at a domain root, in a
subdirectory, or opened from disk. Serve `site/` with any static file server;
directory-shaped URLs need `index.html` resolution, which every one of them
does by default.

### A host that does not resolve directories

Some static hosts serve files and nothing else: `/stats/` is a 404 there and
only `/stats/index.html` exists. Every internal link this framework writes is
directory-shaped, so on such a host the homepage renders and the first click
404s.

```bash
xpkgindex generate . --output site --url-style file
```

Every internal link then ends in `index.html` — including the ones inside your
own documents, which are rewritten while the site is built. The files written
to disk are identical either way, so this is a re-render, not a different
site, and the same repository can publish both forms:

```bash
xpkgindex generate . --output site                     # GitHub Pages
xpkgindex generate . --output site-flat --url-style file   # the other host
```

`urls.style` in the config sets a default for every build; the flag overrides
it for one.

For a local look before publishing:

```bash
xpkgindex serve . --port 8000
```

That builds and serves, sending `Cache-Control: no-store` — a preview that
still shows the previous build is worse than no preview.
