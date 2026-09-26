"""Real-browser checks for public/index.html + app.js (event grouping, All dates, sorting, reports).

Serves public/ read-only on a local port and drives headless Chromium with Playwright. Scenarios
that need other data (missing/stale event index, unmapped cards, failed days, assessed priorities)
replace responses with request interception; nothing is written to public/data. The assessed
priority data below is SYNTHETIC test data, not real news. Skipped when Playwright or its Chromium
build is not installed.
"""
import functools
import http.server
import json
import threading
from datetime import datetime
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

PUBLIC = Path(__file__).resolve().parents[1] / "public"
DATA = PUBLIC / "data"
REPORT = "reports/junson-private-credit-report-2026q3-en-v2.pdf"
REPORT_ZH = "reports/junson-private-credit-report-2026q3-zh-v2.pdf"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


INDEX = load("index.json")
EVENTS = load("events.json")["events"]
DAYS = {day: load(f"{day}.json")["items"] for day in INDEX["dates"]}
CARDS = {item["id"]: item for items in DAYS.values() for item in items}
REVIEWED = [event for event in EVENTS if event["merge_rule"] == "reviewed"]
UPDATES = load("events.json").get("card_updates", {})  # evidence backfill shown instead of card text


def ts(value):
    return datetime.fromisoformat(value).timestamp()


@pytest.fixture(scope="module")
def site():
    handler = functools.partial(QuietHandler, directory=str(PUBLIC))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except sync_api.Error as error:  # Chromium build missing on this machine.
            pytest.skip(f"Chromium unavailable: {error}")
        yield browser, f"http://127.0.0.1:{server.server_address[1]}/"
        browser.close()
    server.shutdown()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def page(site):
    browser, base = site
    context = browser.new_context(locale="en-GB")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.base = base
    yield page
    context.close()
    assert errors == []


def open_site(page, hash_=""):
    page.goto(page.base + hash_)
    page.wait_for_function("document.querySelector('#main .count, #main .state') !== null || location.hash === '#reports'")


def show_all(page):
    page.click("#allDates")
    page.wait_for_function("state.mode === 'all' && !state.allLoading")


def card_ids(page):
    return page.eval_on_selector_all("#main .card", "cards => cards.map(card => card.dataset.card)")


def reply(**response):
    return lambda route: route.fulfill(**response)


def pick(page, day):
    page.select_option("#dateSelect", day)
    page.wait_for_function("day => state.date === day && state.days.has(day)", arg=day)


# ---- Real archive: grouping, counts, source preservation --------------------------------------

def test_date_views_use_each_days_representative_and_keep_every_source(page):
    open_site(page)
    for day, items in DAYS.items():
        pick(page, day)
        views = [event["date_views"][day] for event in EVENTS if day in event["date_views"]]
        expected = [view["representative_card_id"] for view in sorted(views, key=lambda view: view["priority_rank"])]
        assert card_ids(page) == expected, day
        count = page.text_content("#main .count")
        assert count == f"{len(views)} events · {len(items)} articles", day
        # Every raw article of the day is reachable: as a card or inside its Sources list.
        links = set(page.eval_on_selector_all("#main .source a", "links => links.map(link => link.href)"))
        for item in items:
            assert item["source"]["url"] in links, (day, item["id"])


def test_cross_date_pairs_show_further_coverage_and_link_back(page):
    open_site(page)
    for event_id, first, later in [("evt-reviewed-004", "2026-09-16", "2026-09-18"),   # Apollo Executive Centre
                                   ("evt-reviewed-008", "2026-09-11", "2026-09-13")]:  # BlackRock
        event = next(event for event in EVENTS if event["event_id"] == event_id)
        pick(page, later)
        card = page.locator(f"#main .card[data-card='{event['date_views'][later]['representative_card_id']}']")
        button = card.locator("button.linkish")
        assert "first reported" in button.text_content()
        button.click()
        page.wait_for_function("day => state.date === day", arg=first)
        assert event["date_views"][first]["representative_card_id"] in card_ids(page)


def test_same_day_pairs_expand_to_both_sources(page):
    from tools.summarize import strip_absence_claims
    open_site(page)
    for event in REVIEWED:
        for day, view in event["date_views"].items():
            if len(view["member_card_ids"]) < 2:
                continue
            pick(page, day)
            card = page.locator(f"#main .card[data-card='{view['representative_card_id']}']")
            summary = card.locator("details.sources summary")
            assert summary.text_content() == f"Sources ({len(view['member_card_ids'])})"
            summary.click()
            items = card.locator(".source-list li")
            assert items.count() == len(view["member_card_ids"])
            for index, member in enumerate(view["member_card_ids"]):
                text = items.nth(index).text_content()
                current = UPDATES.get(member) or CARDS[member]
                shown = strip_absence_claims(current["summary"]["en"])  # display hides unread-article claims
                assert current["headline"]["en"] in text and shown in text


def test_all_dates_lists_each_event_once_and_every_article(page):
    open_site(page)
    show_all(page)
    ids = card_ids(page)
    assert len(ids) == len(EVENTS) and len(set(ids)) == len(EVENTS)
    assert ids == [event["representative_card_id"] for event in sorted(EVENTS, key=lambda event: event["priority_rank"])]
    assert page.text_content("#main .count") == f"{len(EVENTS)} events · {len(CARDS)} articles · {len(DAYS)} dates"
    links = page.eval_on_selector_all("#main .source a", "links => links.map(link => link.href)")
    assert {item["source"]["url"] for item in CARDS.values()} <= set(links)
    for size in {len(event["member_card_ids"]) for event in EVENTS} - {1}:
        expected = sum(len(event["member_card_ids"]) == size for event in EVENTS)
        assert page.locator("details.sources summary", has_text=f"Sources ({size})").count() == expected
    # Earlier/Later are disabled here but still visible, and come back on a date.
    assert page.is_disabled("#prev") and page.is_disabled("#next") and page.is_visible("#prev")
    pick(page, INDEX["dates"][5])
    assert not page.is_disabled("#prev") and not page.is_disabled("#next")


def test_all_dates_filters_intersect_and_persist(page):
    open_site(page)
    show_all(page)
    for gp in [""] + list(INDEX["labels"]["gps"]):
        page.select_option("#gpSelect", gp)
        for sector in [""] + list(INDEX["labels"]["sectors"]):
            page.select_option("#sectorSelect", sector)
            expected = [event for event in EVENTS
                        if (not gp or gp in event["display_gps"]) and (not sector or sector in event["display_sectors"])]
            assert len(card_ids(page)) == len(expected), (gp, sector)
            if gp or sector:
                articles = sum(len(event["member_card_ids"]) for event in expected)
                assert page.text_content("#main .count").startswith(
                    f"{len(expected)} of {len(EVENTS)} events · {articles} of {len(CARDS)} articles")
    page.select_option("#gpSelect", "apollo")
    page.select_option("#sectorSelect", "private_credit")
    page.click("#today")
    page.wait_for_function("state.mode === 'date'")
    assert page.input_value("#gpSelect") == "apollo" and page.input_value("#sectorSelect") == "private_credit"
    show_all(page)
    assert page.input_value("#gpSelect") == "apollo"


def test_newest_sort_and_language_do_not_change_order_unexpectedly(page):
    open_site(page)
    show_all(page)
    page.select_option("#sortSelect", "newest")
    order = sorted(range(len(EVENTS)), key=lambda i: (-ts(EVENTS[i]["last_material_update_at"]), i))
    assert card_ids(page) == [EVENTS[i]["representative_card_id"] for i in order]
    before = card_ids(page)
    page.click("[data-lang='zh']")
    assert card_ids(page) == before
    assert page.input_value("#sortSelect") == "newest"
    page.reload()
    page.wait_for_function("state.index !== null")
    assert page.get_attribute("html", "lang") == "zh-CN"
    assert page.get_attribute("[data-lang='zh']", "aria-pressed") == "true"


def test_today_from_all_dates_and_legacy_priority_notice(page):
    open_site(page)
    show_all(page)
    assert "Needs review" in page.text_content("#main")
    # The notice is shown only while nothing in the archive has an assessed priority.
    assessed = any(event["priority"]["priority"] != "needs_review" for event in EVENTS)
    assert ("No article here has an assessed priority yet" in page.text_content("#main")) is not assessed
    page.click("#today")
    page.wait_for_function("state.mode === 'date' && state.date !== null")
    assert page.input_value("#dateSelect") == page.evaluate("state.date")


def test_keyboard_and_mobile(page):
    page.set_viewport_size({"width": 375, "height": 812})
    open_site(page)
    page.focus("#today")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.id") == "allDates"
    page.keyboard.press("Enter")
    page.wait_for_function("state.mode === 'all' && !state.allLoading")
    page.focus("details.sources summary")
    page.keyboard.press("Enter")
    assert page.evaluate("document.querySelector('details.sources').open")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


# ---- Mocked failure modes -------------------------------------------------------------------

def test_missing_or_invalid_event_index_shows_every_raw_article(page):
    for body, status in [("not found", 404), ("{\"schema_version\": 1, \"events\": \"bad\"}", 200)]:
        page.unroute("**/data/events.json")
        page.route("**/data/events.json", reply(status=status, body=body))
        open_site(page)
        day = page.evaluate("state.date")
        assert len(card_ids(page)) == len(DAYS[day])
        assert "grouping is unavailable" in page.text_content("#main")
        show_all(page)
        assert len(card_ids(page)) == len(CARDS)


def test_stale_index_and_unmapped_new_card(page):
    day = "2026-09-23"
    synthetic = dict(DAYS[day][0], id="synthetic0001", source={"publisher": "Synthetic", "url": "https://example.com/synthetic"})
    page.route(f"**/data/{day}.json", lambda route: route.fulfill(json={"date": day, "items": [synthetic] + DAYS[day]}))
    open_site(page)
    pick(page, day)
    assert "synthetic0001" in card_ids(page)
    event_count = sum(day in event["date_views"] for event in EVENTS) + 1
    assert page.text_content("#main .count") == f"{event_count} events · {len(DAYS[day]) + 1} articles"
    # Dropping a grouped member makes the index stale for that day: raw fallback, nothing hidden.
    member = "8d1b134a37a1"
    remaining = [item for item in DAYS[day] if item["id"] != member]
    page.unroute(f"**/data/{day}.json")
    page.route(f"**/data/{day}.json", lambda route: route.fulfill(json={"date": day, "items": remaining}))
    open_site(page)
    pick(page, day)
    assert sorted(card_ids(page)) == sorted(item["id"] for item in remaining)
    assert "does not match these articles" in page.text_content("#main")


def test_stale_date_view_cannot_omit_a_loaded_group_member(page):
    data = load("events.json")
    day = "2026-09-23"
    event = next(event for event in data["events"]
                 if len(event["date_views"].get(day, {}).get("member_card_ids", [])) >= 2)
    view = event["date_views"][day]
    first = next(item["id"] for item in DAYS[day] if item["id"] in view["member_card_ids"])
    view["member_card_ids"] = [first]
    view["representative_card_id"] = first
    page.route("**/data/events.json", lambda route: route.fulfill(json=data))
    open_site(page)
    pick(page, day)
    assert sorted(card_ids(page)) == sorted(item["id"] for item in DAYS[day])
    assert "does not match these articles" in page.text_content("#main")


def test_partial_all_dates_load_names_failures_and_retries(page):
    failing = INDEX["dates"][3]
    page.route(f"**/data/{failing}.json", lambda route: route.fulfill(status=500, body="error"))
    open_site(page)
    show_all(page)
    notice = page.text_content("#main .notice-warn")
    assert f"1 of {len(DAYS)} dates could not be loaded" in notice and "not the full archive" in notice
    assert page.text_content("#main .count").endswith(f"· {len(DAYS) - 1} dates")
    assert len(card_ids(page)) < len(EVENTS)
    page.unroute(f"**/data/{failing}.json")
    page.click("#main .retry")
    page.wait_for_function("state.mode === 'all' && !state.allLoading")
    assert page.locator("#main .notice-warn").count() == 0
    assert len(card_ids(page)) == len(EVENTS)


def test_rapid_date_switching_keeps_last_choice(page):
    slow, fast = INDEX["dates"][10], INDEX["dates"][11]

    # Hold the first day's response in the page so the second choice lands first.
    page.add_init_script("""const realFetch = window.fetch;
      window.fetch = (url, options) => String(url).includes(SLOW_DAY)
        ? new Promise((resolve) => setTimeout(resolve, 800)).then(() => realFetch(url, options))
        : realFetch(url, options);""".replace("SLOW_DAY", json.dumps(slow)))
    open_site(page)
    page.select_option("#dateSelect", slow)
    page.select_option("#dateSelect", fast)
    page.wait_for_function("day => state.days.has(day)", arg=slow)
    page.wait_for_timeout(100)
    assert page.evaluate("state.date") == fast
    assert set(card_ids(page)) <= {item["id"] for item in DAYS[fast]}


# ---- SYNTHETIC assessed priorities (never written to public/data) ----------------------------

def synthetic_archive():
    def card(card_id, day, hour):
        return {"id": card_id, "date": day, "published_at": f"{day}T{hour:02d}:00:00+08:00",
                "headline": {"en": f"SYNTHETIC {card_id}", "zh": f"合成 {card_id}"},
                "summary": {"en": "Synthetic fixture.", "zh": "合成测试数据。"}, "gps": ["apollo"], "sectors": ["private_credit"],
                "region": "US", "source": {"publisher": "Fixture", "url": f"https://example.com/{card_id}"},
                "review_status": "unreviewed", "origin": "auto_fetch"}

    def priority(level, potential=False):
        return {"priority": level, "potential_urgent": potential,
                "reason": {"en": f"Synthetic {level} reason", "zh": f"合成{level}理由"}}

    days = {"2026-09-22": [card("a", "2026-09-22", 9), card("b", "2026-09-22", 10)],
            "2026-09-23": [card("c", "2026-09-23", 8), card("d", "2026-09-23", 9), card("e", "2026-09-23", 10),
                           card("f", "2026-09-23", 11)]}
    # Global ranks: c urgent, a important, e important (same-class tie), b useful, d/f needs_review.
    spec = [("c", "urgent", 1, 2, True), ("a", "important", 2, 1, False), ("e", "important", 3, 1, False),
            ("b", "useful", 4, 2, False), ("d", "needs_review", 5, 3, True), ("f", "needs_review", 6, 4, False)]
    events = []
    for card_id, level, rank, day_rank, potential in spec:
        day = next(day for day, items in days.items() if any(item["id"] == card_id for item in items))
        events.append({"event_id": f"evt-{card_id}", "member_card_ids": [card_id], "representative_card_id": card_id,
                       "display_gps": ["apollo"], "display_sectors": ["private_credit"],
                       "last_material_update_at": f"{day}T00:00:00+08:00", "updated": card_id == "e",
                       "priority": priority(level, potential), "priority_rank": rank, "sources": [],
                       "date_views": {day: {"representative_card_id": card_id, "member_card_ids": [card_id],
                                            "display_gps": ["apollo"], "display_sectors": ["private_credit"],
                                            "further_coverage": False, "priority": priority(level, potential),
                                            "priority_rank": day_rank}}})
    index = dict(INDEX, dates=list(days), counts={day: len(items) for day, items in days.items()})
    return index, days, {"schema_version": 1, "events": events}


def test_synthetic_priority_order_labels_and_potential_urgent(page):
    index, days, events = synthetic_archive()
    page.route("**/data/index.json", lambda route: route.fulfill(json=index))
    page.route("**/data/events.json", lambda route: route.fulfill(json=events))
    for day, items in days.items():
        page.route(f"**/data/{day}.json", reply(json={"date": day, "items": items}))
    open_site(page)
    show_all(page)
    assert card_ids(page) == ["c", "a", "e", "b", "d", "f"]
    labels = page.eval_on_selector_all("#main .card .prio", "nodes => nodes.map(node => node.textContent)")
    assert labels == ["Urgent", "Important", "Important", "Useful", "Needs review", "Needs review"]
    alerts = page.eval_on_selector_all("#main .card", "cards => cards.map(card => card.querySelector('.alert')?.textContent || '')")
    assert alerts[0] == alerts[4] == "Potential urgent item — needs verification" and alerts.count("") == 4
    assert "Source updated" in page.text_content("#main .card[data-card='e']")
    assert "No article here has an assessed priority yet" not in page.text_content("#main")
    # Single date uses that day's own ranks, not the global ones.
    pick(page, "2026-09-23")
    assert card_ids(page) == ["e", "c", "d", "f"]
    page.select_option("#sortSelect", "newest")
    assert card_ids(page) == ["f", "e", "d", "c"]
    page.click("[data-lang='zh']")
    assert card_ids(page) == ["f", "e", "d", "c"]
    assert "潜在紧急事项" in page.text_content("#main")


# ---- Reports ----------------------------------------------------------------------------------

REPORT_SHA256 = {REPORT: "84e9a89bb7f27dc6f1cb316b810dcecb46d6ab89f7799e71bc9b725e15a0ab0c",
                 REPORT_ZH: "4f8e456ab7dd821a0cc7283bd38aceb3b334dfacd1936d3f6edae96cccf5d106"}
# A page counts as shown only when its canvas has real ink: many distinct colours, not a blank pane.
PAINTED = """canvas => {
  const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
  const colours = new Set();
  for (let i = 0; i < data.length; i += 4 * 97) colours.add(data[i] << 16 | data[i + 1] << 8 | data[i + 2]);
  return canvas.width > 100 && colours.size > 20;
}"""


def viewer_ready(page, src):
    page.wait_for_selector(f"#reports .pdf-viewer[data-src='{src}'][data-state='ready']", timeout=30000)
    assert page.eval_on_selector("#reports .pdf-page canvas", PAINTED)
    assert page.locator("#reports .pdf-viewer [role='status']").count() == 0


def test_summaries_hide_claims_about_unread_articles_exactly_like_the_pipeline(page):
    from tools.summarize import strip_absence_claims
    open_site(page)
    samples = [(item["summary"]["en"], "en") for item in CARDS.values()] + [(item["summary"]["zh"], "zh") for item in CARDS.values()]
    got = page.evaluate("pairs => pairs.map(([text, lang]) => stripAbsence(text, lang))", samples)
    assert got == [strip_absence_claims(text, lang) for text, lang in samples]
    assert sum(g != t for g, (t, _) in zip(got, samples)) > 20  # the archive really carries this filler
    card = next(c for c in CARDS.values() if "No further details" in c["summary"]["en"])
    show_all(page)
    shown = page.text_content(f"#main .card[data-card='{card['id']}'] p.summary") if page.locator(
        f"#main .card[data-card='{card['id']}'] p.summary").count() else page.text_content("#main")
    assert "No further details" not in shown


def test_evidence_updates_replace_headline_only_text_and_are_labelled(page):
    data = load("events.json")
    event = next(e for e in data["events"] if len(e["member_card_ids"]) == 1)
    cid = event["representative_card_id"]
    data["card_updates"] = {cid: {"headline": {"en": "Updated headline from source", "zh": "按原文更新的标题"},
                                  "summary": {"en": "Updated summary from the source page.", "zh": "按原文页面更新的摘要。"},
                                  "evidence_level": "excerpt", "updated_at": "2026-09-26T08:00:00+00:00"}}
    page.route("**/data/events.json", lambda route: route.fulfill(json=data))
    open_site(page)
    show_all(page)
    card = page.locator(f"#main .card[data-card='{cid}']")
    assert card.locator("h3.headline").text_content() == "Updated headline from source"
    assert card.locator("p.summary").text_content() == "Updated summary from the source page."
    assert "Updated from source" in card.text_content()
    page.click("[data-lang='zh']")
    assert card.locator("p.summary").text_content() == "按原文页面更新的摘要。"
    # Without the event index the original card text is shown: updates never outlive their index.
    page.unroute("**/data/events.json")
    page.route("**/data/events.json", lambda route: route.fulfill(status=404, body="missing"))
    open_site(page)
    show_all(page)
    assert "Updated headline from source" not in page.text_content("#main")


def test_reports_render_both_approved_pdfs_inline(page):
    open_site(page, "#reports")
    assert page.is_hidden("#toolbar") and page.is_hidden("#main")
    viewer_ready(page, REPORT)
    assert page.locator("#reports .pdf-page").count() == 21
    assert "21" in page.text_content("#reports .pdf-count")
    hrefs = page.eval_on_selector_all("#reports .report-actions a", "links => links.map(link => link.getAttribute('href'))")
    assert hrefs == [REPORT, REPORT]
    # Explicit Chinese choice renders the approved Chinese PDF inside the page.
    page.click("#reports .report-lang button:nth-child(2)")
    viewer_ready(page, REPORT_ZH)
    assert page.text_content("#reports .report-lang button:nth-child(2)") == "中文"
    assert "pending" not in page.text_content("#reports").lower()
    page.click("#reports .report-lang button:nth-child(1)")
    viewer_ready(page, REPORT)
    page.click("[data-view='news']")
    page.wait_for_function("!document.getElementById('main').hidden")


def test_report_bytes_are_the_approved_versions(page):
    import hashlib
    for path, digest in REPORT_SHA256.items():
        body = page.request.get(page.base + path).body()
        assert body[:5] == b"%PDF-" and hashlib.sha256(body).hexdigest() == digest


def test_report_zoom_and_scrolling_render_later_pages(page):
    open_site(page, "#reports")
    viewer_ready(page, REPORT)
    first = "#reports .pdf-page:first-child"
    width = page.eval_on_selector(first, "node => node.getBoundingClientRect().width")
    assert page.text_content("#reports .pdf-zoom") == "100%"
    page.click("#reports button.pdf-zoom-in")
    page.wait_for_function("w => document.querySelector('#reports .pdf-page').getBoundingClientRect().width > w * 1.2", arg=width)
    assert page.text_content("#reports .pdf-zoom") == "125%"
    page.wait_for_function("() => document.querySelector('#reports .pdf-page canvas') && document.querySelector('#reports .pdf-page').dataset.rendered === '125'")
    page.click("#reports button.pdf-fit")
    assert page.text_content("#reports .pdf-zoom") == "100%"
    # The last page is drawn only once it is scrolled into view.
    last = "#reports .pdf-page:last-child"
    assert page.eval_on_selector(last, "node => !node.querySelector('canvas')")
    page.eval_on_selector("#reports .pdf-scroll", "node => { node.scrollTop = node.scrollHeight; }")
    page.wait_for_selector(last + " canvas")
    page.wait_for_function("() => document.querySelector('#reports .pdf-page:last-child').dataset.rendered")
    assert page.eval_on_selector(last + " canvas", PAINTED)


def test_report_failure_is_an_explicit_error_with_retry(page):
    page.route("**/" + REPORT, lambda route: route.fulfill(status=404, body="missing"))
    open_site(page, "#reports")
    page.wait_for_selector("#reports .pdf-viewer[data-state='error']", timeout=30000)
    text = page.text_content("#reports .pdf-viewer")
    assert "could not be displayed" in text and page.locator("#reports .pdf-page").count() == 0
    assert page.is_visible("#reports .report-actions a")  # Open/Download remain the way out.
    page.unroute("**/" + REPORT)
    page.click("#reports .pdf-viewer .retry")
    viewer_ready(page, REPORT)


def test_report_viewer_fits_a_phone_and_is_keyboard_reachable(page):
    page.set_viewport_size({"width": 375, "height": 812})
    open_site(page, "#reports")
    viewer_ready(page, REPORT)
    box = page.eval_on_selector("#reports .pdf-scroll", "node => node.getBoundingClientRect().width")
    assert page.eval_on_selector("#reports .pdf-page", "node => node.getBoundingClientRect().width") <= box
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    for selector in ("button.pdf-zoom-out", "button.pdf-zoom-in", "button.pdf-fit"):
        assert page.get_attribute("#reports " + selector, "aria-label")
    assert page.get_attribute("#reports .pdf-scroll", "tabindex") == "0"
    assert page.get_attribute("#reports .pdf-page canvas", "aria-label") == "Page 1 of 21"


def test_reports_default_to_page_language_and_english_fallback(page):
    open_site(page, "#reports")
    page.click("[data-lang='zh']")
    viewer_ready(page, REPORT_ZH)
    assert page.get_attribute("#reports .pdf-zoom-in", "aria-label") == "放大"
    # Without an approved Chinese file only English is offered, with no pending wording.
    page.evaluate("REPORTS[0].files.zh = null; renderReports()")
    buttons = page.eval_on_selector_all("#reports .report-lang button", "nodes => nodes.map(node => node.textContent)")
    assert buttons == ["English"] and "待审核" not in page.text_content("#reports")
    viewer_ready(page, REPORT)
