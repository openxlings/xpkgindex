"""Exercise generated navigation with real mouse, touch and keyboard input.

Install .[dev,browser] and run playwright install chromium webkit locally.
The dedicated CI job installs both engines; ordinary Python-only runs skip it.
"""

import pytest
from pathlib import Path

playwright = pytest.importorskip("playwright.sync_api")

from xpkgindex.build import build
from xpkgindex.render import render
from conftest import commit, write_config


@pytest.fixture
def site(repo, tmp_path):
    Path(repo, 'pkgs/w/beta.widget.lua').unlink()
    Path(repo, 'guide.md').write_text('# Guide\n', encoding='utf-8')
    write_config(repo, languages=["en", "zh"], theme={"transition": {"duration": "0s"}},
                 docs={"entries": [{"slug": slug, "title": slug, "path": "guide.md"}
                                   for slug in ['start', 'reference']]})
    commit(repo, "configure languages")
    site, config = build(repo, offline=True)
    out = tmp_path / "site"
    render(site, config, str(out))
    return (out / "index.html").as_uri()


@pytest.fixture(params=["chromium", "webkit"])
def browser(request):
    with playwright.sync_playwright() as pw:
        engine = getattr(pw, request.param).launch()
        yield engine
        engine.close()


def assert_closed(page):
    playwright.expect(page.locator('.nav-panel')).to_be_hidden()
    playwright.expect(page.locator('.nav-menu a').first).to_be_hidden()
    playwright.expect(page.locator('.nav-trigger')).to_have_attribute('aria-expanded', 'false')


def assert_open(page):
    playwright.expect(page.locator('.nav-trigger')).to_have_attribute('aria-expanded', 'true')
    playwright.expect(page.locator('.nav-panel')).to_be_visible()


def test_narrow_mouse_and_keyboard(browser, site):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(site)
    trigger = page.locator('.nav-trigger')
    trigger.hover()
    assert_closed(page)
    trigger.focus()
    assert_closed(page)
    trigger.press('Enter')
    assert_open(page)
    trigger.click()
    assert_closed(page)
    trigger.press('Space')
    assert_open(page)
    page.locator('#q').focus()
    page.locator('#q').press('Escape')
    assert_closed(page)
    playwright.expect(trigger).to_be_focused()
    trigger.press('Tab')
    # Closed links and controls must be absent from keyboard navigation.
    assert not page.evaluate("document.activeElement.closest('.nav-panel') !== null")
    trigger.click()
    assert_open(page)
    page.locator('.footer strong').click()
    assert_closed(page)
    trigger.click()
    page.locator('#q').focus()
    page.locator('.skip').focus()
    assert_closed(page)
    page.close()


def test_touch_controls_and_resize(browser, site):
    context = browser.new_context(viewport={"width": 390, "height": 844},
                                  is_mobile=True, has_touch=True)
    page = context.new_page()
    page.goto(site)
    trigger = page.locator('.nav-trigger')
    trigger.tap()
    assert_open(page)
    trigger.tap()
    assert_closed(page)
    trigger.tap()
    page.locator('#q').tap()
    page.locator('#q').fill('widget')
    assert_open(page)
    theme = page.locator('html').get_attribute('data-theme')
    page.locator('.theme-toggle').tap()
    assert_open(page)
    assert page.locator('html').get_attribute('data-theme') != theme
    page.locator('.lang-trigger').tap()
    playwright.expect(page.locator('.lang-menu')).to_be_visible()
    assert_open(page)
    page.locator('.footer strong').tap()
    assert_closed(page)
    trigger.tap()
    page.set_viewport_size({"width": 1000, "height": 844})
    playwright.expect(trigger).to_be_hidden()
    playwright.expect(page.locator('.nav a').first).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    assert_closed(page)
    context.close()


@pytest.mark.parametrize('width', [390, 1000])
def test_navigation_without_javascript(browser, site, width):
    context = browser.new_context(java_script_enabled=False,
                                  viewport={"width": width, "height": 844})
    page = context.new_page()
    page.goto(site)
    playwright.expect(page.locator('.nav-trigger')).to_be_hidden()
    playwright.expect(page.locator('.nav a').first).to_be_visible()
    playwright.expect(page.locator('#q')).to_be_visible()
    context.close()
