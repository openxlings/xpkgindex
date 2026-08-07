"""Fixtures that build throwaway index repositories.

The tests exercise the whole pipeline against real descriptors and real git
history rather than mocking it — the bugs this framework exists to prevent
(a silently overwritten page, a curve that disagrees with the tree) only show
up end to end.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap

import pytest

DESCRIPTOR = """\
package = {{
    spec        = "1",
    namespace   = "{ns}",
    name        = "{name}",
    description = "{desc}",
    licenses    = {{"MIT"}},
    repo        = "https://github.com/{ns}/{name}",
    type        = "package",
    xpm = {{
        linux = {{
            ["{version}"] = {{
                url    = {{ GLOBAL = "https://example.invalid/{name}.tar.gz" }},
                sha256 = "0000000000000000000000000000000000000000000000000000000000000000",
            }},
        }},
    }},
}}
"""


def write_descriptor(root, ns, name, version="1.0.0", desc="test package"):
    path = os.path.join(root, "pkgs", name[0].lower(), f"{ns}.{name}.lua")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(DESCRIPTOR.format(ns=ns, name=name, version=version, desc=desc))
    return path


def git(root, *args):
    subprocess.run(["git", "-C", root] + list(args), check=True,
                   capture_output=True, text=True)


def init_repo(root):
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test Person")


def commit(root, message, date="2026-01-01"):
    env = dict(os.environ, GIT_AUTHOR_DATE=f"{date}T00:00:00", GIT_COMMITTER_DATE=f"{date}T00:00:00")
    subprocess.run(["git", "-C", root, "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", root, "commit", "-q", "-m", message],
                   check=True, capture_output=True, env=env)


def write_config(root, **overrides):
    config = {
        "site": {"title": "Test Index"},
        "pkgs_dir": "pkgs",
        "install_command_template": "tool add {ref}@{version}",
    }
    config.update(overrides)
    with open(os.path.join(root, ".xpkgindex.json"), "w", encoding="utf-8") as f:
        json.dump(config, f)


def write_plugin(root, body, name="p.py"):
    path = os.path.join(root, ".xpkgindex", "plugins")
    os.makedirs(path, exist_ok=True)
    full = os.path.join(path, name)
    with open(full, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(body))
    return f".xpkgindex/plugins/{name}"


@pytest.fixture
def repo(tmp_path):
    """An index repo with two packages sharing a short name."""
    root = str(tmp_path / "index")
    os.makedirs(root)
    init_repo(root)
    write_config(root)
    write_descriptor(root, "alpha", "widget")
    write_descriptor(root, "beta", "widget")
    commit(root, "add widgets", date="2026-01-01")
    return root
