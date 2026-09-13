// Fund Coverage News demo dashboard. Reads static JSON from the directory this page is served from:
// either a Phase 8 published site (publication.json names the served edition; see
// tools/publication.py) or an older bundle with a ./data feed (tools/export_demo.py). No network
// calls beyond same-origin fetch of local JSON; nothing here collects news or runs a model.
//
// Safety notes:
// - Every render path below builds DOM nodes and sets .textContent; nothing from the feed (a
//   headline, a source title, a publisher name) is ever assigned to innerHTML. Source article
//   text is untrusted -- a hostile title like "<img onerror=...>" must render as inert text.
// - Source links are allowlisted to http/https before becoming a real <a href>; anything else
//   renders as plain text so a "javascript:" or "data:" URL in captured evidence cannot execute.
// - Fetches carry a monotonic request token so a slow response for a date the user already
//   navigated away from can never overwrite what is on screen (out-of-order fetch guard).
// - Freshness shows recorded source-check and publication times only. The browser clock is used
//   to judge staleness, never displayed as the age of the news.
const LEGACY_DATA_ROOT = "./data";
const HK_OFFSET_MS = 8 * 60 * 60 * 1000;
const NO_STORE = {cache: "no-store"};
const HK_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Hong_Kong", year: "numeric", month: "short", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hour12: false,
});

const state = {
  dates: [], index: -1, indexMeta: null, lang: "en", requestToken: 0, mode: "calendar",
  dataRoot: LEGACY_DATA_ROOT, publication: null, status: null, reloadNote: "", reloadFailed: false,
};

function todayHongKong() {
  const utcMillis = Date.now();
  const hk = new Date(utcMillis + HK_OFFSET_MS);
  return hk.toISOString().slice(0, 10);
}

async function fetchJson(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

async function loadPublication() {
  // A bundle without publication.json (the baseline demo) keeps reading ./data exactly as before.
  const response = await fetch("./publication.json", NO_STORE);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`publication.json: HTTP ${response.status}`);
  return response.json();
}

async function loadStatus() {
  try {
    return await fetchJson("./status.json", NO_STORE);
  } catch {
    return null; // Reported as "status unavailable", never as a healthy check.
  }
}

function formatInstant(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : `${HK_TIME.format(parsed)} HKT`;
}

function clearChildren(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function el(tag, options, children) {
  const node = document.createElement(tag);
  if (options) {
    if (options.className) node.className = options.className;
    if (options.text !== undefined) node.textContent = options.text;
    if (options.attrs) for (const [key, value] of Object.entries(options.attrs)) node.setAttribute(key, value);
  }
  for (const child of children || []) node.appendChild(child);
  return node;
}

function isSafeHttpUrl(value) {
  try {
    const url = new URL(value, window.location.href);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function renderDisclosure(meta) {
  const target = document.getElementById("disclosure");
  clearChildren(target);
  target.appendChild(document.createTextNode(meta.disclosure));
}

function sourceCheckText(check) {
  if (!check) return "None recorded";
  const when = formatInstant(check.checked_at);
  if (check.status === "succeeded") {
    const items = check.new_items === 0 ? "no new items"
      : check.new_items == null ? "new item count not recorded"
      : `${check.new_items} new item${check.new_items === 1 ? "" : "s"}`;
    return `${when} — succeeded, ${items}`;
  }
  const outcome = check.status === "budget_stopped" ? "stopped at the paid-call cap" : "failed";
  return `${when} — ${outcome}${check.detail ? ` (${check.detail})` : ""}`;
}

function freshnessNotices() {
  const publication = state.publication;
  const status = state.status || {};
  const notices = [];
  if (publication.edition_kind === "historical_sample") {
    notices.push(["historical", "Historical sample — not today's news"]);
  }
  const check = status.last_source_check;
  const success = status.last_successful_source_check;
  if (check && check.status === "succeeded" && check.new_items === 0) {
    notices.push(["nonews", "Latest source check: no new items"]);
  }
  if (check && check.status === "failed") notices.push(["failed", "Latest source check failed"]);
  if (check && check.status === "budget_stopped") {
    notices.push(["failed", "Latest source check stopped at the paid-call cap"]);
  }
  const hours = status.stale_after_hours ?? 24;
  const successAt = success ? new Date(success.checked_at).getTime() : NaN;
  if (Number.isNaN(successAt) || Date.now() - successAt > hours * 60 * 60 * 1000) {
    notices.push(["stale", `Stale: no successful source check in the last ${hours} h`]);
  }
  const attempt = status.last_publish_attempt;
  if (attempt && attempt.status === "failed") {
    notices.push(["failed", `Publish attempt ${attempt.publication_id} failed; still serving ${publication.publication_id}`]);
  }
  if (!state.status) notices.push(["failed", "Status file unavailable"]);
  if (state.reloadFailed) notices.push(["failed", "Reload failed; showing the previously loaded edition"]);
  return notices;
}

function renderFreshness() {
  const panel = document.getElementById("freshness");
  panel.hidden = !state.publication;
  if (!state.publication) return;
  const publication = state.publication;
  const status = state.status || {};
  const entries = [
    ["Update mode", `${publication.update_mode === "manual" ? "Manual (operator-run)" : publication.update_mode}` +
      ` · ${status.scheduler === "not_installed" ? "no scheduler installed" : `scheduler: ${status.scheduler ?? "unknown"}`}`],
    ["Last source check", sourceCheckText(status.last_source_check)],
  ];
  const check = status.last_source_check;
  if (check && check.status !== "succeeded") {
    entries.push(["Last successful source check", sourceCheckText(status.last_successful_source_check)]);
  }
  entries.push(["Last successful publication",
                `${formatInstant(publication.published_at)} · edition ${publication.publication_id}`]);
  const attempt = status.last_publish_attempt;
  if (attempt && attempt.status === "failed") {
    entries.push(["Last publish attempt", `${formatInstant(attempt.attempted_at)} — failed: ${attempt.detail}`]);
  }
  entries.push(["Article dates in this edition", (publication.article_dates || []).join(", ") || "none"]);

  const rows = document.getElementById("freshnessRows");
  clearChildren(rows);
  for (const [label, value] of entries) {
    rows.appendChild(el("dt", {text: label}));
    rows.appendChild(el("dd", {text: value}));
  }
  const notices = document.getElementById("freshnessNotices");
  clearChildren(notices);
  // "is-" prefix: a bare "stale" class would inherit the page's .stale error-state layout.
  for (const [kind, text] of freshnessNotices()) notices.appendChild(el("span", {className: `notice is-${kind}`, text}));
  document.getElementById("reloadNote").textContent = state.reloadNote;
}

function applyPageText(publication) {
  if (!publication || !publication.page_text) return;
  document.getElementById("subtitle").textContent = publication.page_text.subtitle;
  document.getElementById("footer").textContent = publication.page_text.footer;
}

function applyEdition(meta) {
  state.indexMeta = meta;
  state.dates = meta.dates;
  renderDisclosure(meta);
}

function renderNav() {
  const select = document.getElementById("dateSelect");
  clearChildren(select);
  state.dates.forEach((date, i) => {
    const marked = state.indexMeta && state.indexMeta.dates_with_cards.includes(date);
    select.appendChild(el("option", {text: marked ? `${date} •` : date,
                                     attrs: {value: String(i)}}));
  });
  if (state.index >= 0) select.value = String(state.index);
  document.getElementById("prevDay").disabled = state.index <= 0;
  document.getElementById("nextDay").disabled = state.index < 0 || state.index >= state.dates.length - 1;
  document.getElementById("langEn").classList.toggle("active", state.lang === "en");
  document.getElementById("langZh").classList.toggle("active", state.lang === "zh");
}

function pill(text, cls) {
  return el("span", {className: `pill ${cls || ""}`, text});
}

function tagList(labels) {
  return el("div", {className: "tags"}, labels.filter(Boolean).map((label) => pill(label, "tag")));
}

function renderSource(source) {
  const label = `${source.publisher || "Unknown publisher"}: ${source.title || "Untitled"}`;
  if (source.url && isSafeHttpUrl(source.url)) {
    return el("a", {text: label, attrs: {href: source.url, target: "_blank", rel: "noopener noreferrer"}});
  }
  // No safe scheme (or no URL at all): show the citation as inert text rather than a dead or
  // dangerous link, and say so plainly instead of silently dropping the source.
  return el("span", {text: `${label} (no verifiable link)`});
}

function cardBody(card) {
  const lang = state.lang;
  const en = card.en || {};
  const zh = card.zh;
  const usingZh = lang === "zh" && zh && zh.headline;
  const headline = usingZh ? zh.headline : en.headline;
  const summary = usingZh ? zh.summary : en.summary;
  const whyItMatters = usingZh ? zh.why_it_matters : en.why_it_matters;
  const notice = lang === "zh" && !usingZh
    ? el("div", {className: "zh-block", text: `中文 (Chinese rendering): ${card.zh_status}`})
    : null;
  return {headline, summary, whyItMatters, notice};
}

function renderCard(card) {
  const relevance = card.relevance_level ? pill(card.relevance_level, card.relevance_level) : null;
  const score = pill(`score ${card.total_score ?? "n/a"}`, "score");
  const body = cardBody(card);

  const top = el("div", {className: "card-top"}, [
    el("h3", {className: "headline", text: body.headline || "(no headline)"}),
    el("div", {}, [relevance, score].filter(Boolean)),
  ]);
  const summary = el("p", {className: "summary", text: body.summary || "(no summary)"});
  const children = [top, summary];
  if (body.whyItMatters) {
    children.push(el("p", {className: "why-it-matters"},
      [el("strong", {text: "Why it matters: "}), document.createTextNode(body.whyItMatters)]));
  } else {
    children.push(el("p", {className: "why-it-matters muted",
                          text: "Why it matters: not available (this mechanics demo did not run a drafting model)."}));
  }
  if (body.notice) children.push(body.notice);

  const tags = card.tags || {};
  children.push(tagList([...(tags.entities || []), ...(tags.sectors || []),
                         tags.primary_region, ...(tags.geography || []), tags.event_type]));

  const sources = el("div", {className: "sources"},
    (card.sources || []).map((source, i) => {
      const wrapper = el("div", {}, [renderSource(source)]);
      return wrapper;
    }));
  if (!card.sources || card.sources.length === 0) {
    sources.appendChild(el("span", {text: "No source captured"}));
  }
  children.push(sources);

  children.push(el("div", {className: "meta",
    text: `${card.date ? `article date: ${card.date} · ` : ""}${card.primary_event_type} / ${card.subtype ?? "—"} · partition: ${card.partition} · status: ${card.status}`}));

  return el("div", {className: "card"}, children);
}

function emptyState(title, body) {
  return el("div", {className: "empty"}, [el("h3", {text: title}), el("p", {text: body})]);
}

function errorState(title, body) {
  return el("div", {className: "stale"}, [el("h3", {text: title}), el("p", {text: body})]);
}

async function renderDay() {
  const main = document.getElementById("main");
  const dayStats = document.getElementById("dayStats");
  clearChildren(main);
  if (state.index < 0) {
    main.appendChild(emptyState("No edition open",
      "Pick a date, or use \"Jump to latest historical edition\" below."));
    dayStats.textContent = "";
    return;
  }
  const date = state.dates[state.index];
  const token = ++state.requestToken;
  let cards = [];
  try {
    cards = await fetchJson(`${state.dataRoot}/${date}.json`);
  } catch (error) {
    if (token !== state.requestToken) return; // a newer navigation has already superseded this
    clearChildren(main);
    main.appendChild(errorState(`Could not load ${date}`, error.message));
    dayStats.textContent = "";
    return;
  }
  if (token !== state.requestToken) return; // response arrived after the user moved on
  clearChildren(main);
  dayStats.textContent = `${cards.length} candidate${cards.length === 1 ? "" : "s"} on ${date}`;
  if (cards.length === 0) {
    main.appendChild(emptyState(`No shortlisted candidates for ${date}`,
      "A thin or empty day is an honest editorial outcome, not a display bug."));
    return;
  }
  for (const card of cards) main.appendChild(renderCard(card));
}

function goTo(delta) {
  const next = state.index + delta;
  if (next < 0 || next >= state.dates.length) return;
  state.index = next;
  renderNav();
  renderDay();
}

function goToDate(isoDate) {
  const found = state.dates.indexOf(isoDate);
  if (found < 0) return false;
  state.index = found;
  renderNav();
  renderDay();
  return true;
}

function setLang(lang) {
  state.lang = lang;
  renderNav();
  renderDay();
}

function renderTodayState(today) {
  const main = document.getElementById("main");
  clearChildren(main);
  const hasLatest = state.indexMeta.dates_with_cards.length > 0;
  const message = state.dates.includes(today)
    ? `No edition has been produced yet for today (${today}, Asia/Hong_Kong). This is an honest ` +
      "empty state, not a stale cache."
    : `Today (${today}, Asia/Hong_Kong) is outside this edition's dates ` +
      `(${state.dates[0]} to ${state.dates[state.dates.length - 1]}).`;
  const box = emptyState("No edition open for today", message);
  if (hasLatest) {
    const reviewed = state.publication && state.publication.edition_kind === "reviewed_update";
    const jump = el("button", {text: reviewed ? "Jump to latest approved card date"
                                              : "Jump to latest historical edition"});
    jump.addEventListener("click", () => {
      const latest = state.indexMeta.dates_with_cards[state.indexMeta.dates_with_cards.length - 1];
      goToDate(latest);
    });
    box.appendChild(jump);
  }
  main.appendChild(box);
  document.getElementById("dayStats").textContent = "";
}

function openToday(today) {
  if (state.dates.includes(today) && state.indexMeta.dates_with_cards.includes(today)) {
    state.index = state.dates.indexOf(today);
  } else {
    state.index = -1; // Honest empty state; never silently substitute an older day as "today".
  }
  renderNav();
  if (state.index === -1) {
    renderTodayState(today);
  } else {
    renderDay();
  }
}

async function reloadPublished(today) {
  // Re-reads the published pointer, status and edition index. It never checks sources, collects
  // news or calls a model; a failure keeps whatever edition is already on screen.
  const button = document.getElementById("reloadBtn");
  button.disabled = true;
  const previous = state.publication ? state.publication.publication_id : null;
  const openDate = state.index >= 0 ? state.dates[state.index] : null;
  try {
    const publication = await loadPublication();
    if (!publication) throw new Error("publication.json not found");
    const [status, meta] = await Promise.all([
      loadStatus(), fetchJson(`./${publication.edition_path}/index.json`, NO_STORE)]);
    state.publication = publication;
    state.status = status;
    state.dataRoot = `./${publication.edition_path}`;
    state.reloadFailed = false;
    state.reloadNote = publication.publication_id === previous
      ? `Reloaded: still edition ${previous}.`
      : `Reloaded: now edition ${publication.publication_id} (was ${previous ?? "none"}).`;
    applyPageText(publication);
    applyEdition(meta);
    if (!(openDate && goToDate(openDate))) openToday(today);
  } catch (error) {
    state.reloadFailed = true;
    state.reloadNote = `Reload failed: ${error.message}`;
  } finally {
    button.disabled = false;
    renderFreshness();
  }
}

async function init() {
  const today = todayHongKong();
  let meta;
  try {
    state.publication = await loadPublication();
    if (state.publication) {
      state.dataRoot = `./${state.publication.edition_path}`;
      state.status = await loadStatus();
    }
    meta = await fetchJson(`${state.dataRoot}/index.json`, NO_STORE);
  } catch (error) {
    document.getElementById("disclosure").textContent =
      `Could not load the feed index (${error.message}). Serve the exported or published site ` +
      `directory over HTTP on 127.0.0.1 (see docs/manager-demo-guide.md) rather than opening ` +
      `index.html directly.`;
    clearChildren(document.getElementById("main"));
    return;
  }
  applyPageText(state.publication);
  applyEdition(meta);
  renderFreshness();
  openToday(today);

  document.getElementById("prevDay").addEventListener("click", () => goTo(-1));
  document.getElementById("nextDay").addEventListener("click", () => goTo(1));
  document.getElementById("dateSelect").addEventListener("change", (event) => {
    state.index = Number(event.target.value);
    renderNav();
    renderDay();
  });
  document.getElementById("todayBtn").addEventListener("click", () => {
    if (!goToDate(today)) renderTodayState(today);
  });
  document.getElementById("langEn").addEventListener("click", () => setLang("en"));
  document.getElementById("langZh").addEventListener("click", () => setLang("zh"));
  document.getElementById("reloadBtn").addEventListener("click", () => reloadPublished(today));
}

init();
