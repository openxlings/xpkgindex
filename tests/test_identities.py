"""Identity merging and bot filtering.

mcpp-index has ten git identities for about eight humans; xim-pkgindex has a
version-bump workflow whose commits are authored by `github-actions[bot]`,
which is not a contributor and should not sit in the contributor wall.
"""

from xpkgindex.data.git_history import AuthorStat
from xpkgindex.data.identities import login_from_email, merge


def stat(name, email, paths=("pkgs/a.lua",), shas=("s1",)):
    s = AuthorStat(name=name, email=email)
    s.paths = set(paths)
    s.shas = set(shas)
    s.first_seen = s.last_seen = "2026-01-01"
    return s


def test_shared_email_and_shared_name_collapse_to_one_person():
    people = merge({
        "SPeak|a@x.com": stat("SPeak", "a@x.com", shas=("s1",)),
        "sunrisepeak|a@x.com": stat("sunrisepeak", "a@x.com", shas=("s2",)),
        "sunrisepeak|b@y.com": stat("sunrisepeak", "b@y.com", shas=("s3",)),
    })
    assert len(people) == 1
    assert people[0].commits == 3
    assert set(people[0].names) == {"SPeak", "sunrisepeak"}


def test_distinct_people_stay_distinct():
    people = merge({
        "A|a@x.com": stat("A", "a@x.com"),
        "B|b@y.com": stat("B", "b@y.com"),
    })
    assert len(people) == 2


def test_noreply_email_yields_the_login():
    assert login_from_email("96378453+wellwei@users.noreply.github.com") == "wellwei"
    assert login_from_email("plain@example.com") == ""


def test_manual_map_wins_over_heuristics():
    people = merge(
        {"Someone|a@x.com": stat("Someone", "a@x.com"),
         "Other|b@y.com": stat("Other", "b@y.com")},
        manual={"Someone|a@x.com": "real", "Other|b@y.com": "real"},
    )
    assert len(people) == 1
    assert people[0].login == "real"


def test_bots_are_not_contributors():
    people = merge({
        "github-actions[bot]|bot@github.com": stat("github-actions[bot]", "bot@github.com"),
        "Human|h@x.com": stat("Human", "h@x.com"),
    })
    assert [p.label for p in people] == ["Human"]
