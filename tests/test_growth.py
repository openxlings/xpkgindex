"""The growth curve must reconcile with the tree.

Counting only additions gives 86 on mcpp-index where the tree holds 81; the
five-package gap is deletes and renames. The replay handles them, and the
build asserts the result rather than trusting it.
"""

import os

import pytest

from conftest import commit, init_repo, write_config, write_descriptor, git
from xpkgindex.build import BuildError, build
from xpkgindex.data import git_history


@pytest.fixture
def evolving(tmp_path):
    root = str(tmp_path / "index")
    os.makedirs(root)
    init_repo(root)
    write_config(root)
    write_descriptor(root, "alpha", "one")
    write_descriptor(root, "alpha", "two")
    commit(root, "add two", date="2026-01-01")

    write_descriptor(root, "alpha", "three")
    commit(root, "add one more", date="2026-02-01")

    os.remove(os.path.join(root, "pkgs", "t", "alpha.two.lua"))
    commit(root, "drop two", date="2026-03-01")

    git(root, "mv", "pkgs/t/alpha.three.lua", "pkgs/t/alpha.third.lua")
    commit(root, "rename three", date="2026-04-01")
    return root


def test_replay_tracks_deletes_and_renames(evolving):
    hist = git_history.collect(evolving, "pkgs")
    assert hist.available
    counts = [p.count for p in hist.growth]
    assert counts == [2, 3, 2, 2]
    assert hist.final_paths == {"pkgs/o/alpha.one.lua", "pkgs/t/alpha.third.lua"}


def test_naive_add_count_would_be_wrong(evolving):
    """Guards the reason the replay exists at all."""
    hist = git_history.collect(evolving, "pkgs")
    additions = sum(p.added for p in hist.growth)
    assert additions == 3                      # three files were ever added
    assert hist.growth[-1].count == 2          # but only two survive


def test_build_reconciles_curve_with_tree(evolving):
    site, _ = build(evolving, offline=True)
    assert site.growth[-1].count == site.total_packages


def test_untracked_descriptor_is_reported_not_ignored(evolving):
    write_descriptor(evolving, "alpha", "four")     # left uncommitted
    # A dirty tree downgrades to a warning; --strict makes it fatal so CI
    # cannot ship a curve that disagrees with the packages it renders.
    site, _ = build(evolving, offline=True)
    assert any("does not reconcile" in w for w in site.warnings)
    with pytest.raises(BuildError):
        build(evolving, offline=True, strict=True)


def test_shallow_clone_degrades_without_failing(tmp_path):
    root = str(tmp_path / "plain")
    os.makedirs(root)
    write_config(root)
    write_descriptor(root, "alpha", "one")      # no git repo at all
    site, _ = build(root, offline=True)
    assert site.growth == []
    assert any("not a git repository" in w for w in site.warnings)
    assert site.total_packages == 1             # the site still builds
