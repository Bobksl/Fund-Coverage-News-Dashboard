// Junson Capital — Fund Coverage News. A static page that reads ./data/index.json,
// ./data/status.json, ./data/YYYY-MM-DD.json (shapes in docs/site-data-contract.md) and the optional
// event index ./data/events.json (docs/news-events-contract.md).
//
// Safety: values from the data files are rendered with textContent, never as HTML, and a source
// link is only created for an absolute http(s) URL. Day fetches carry a request token so a slow
// response for a date the reader has already left cannot overwrite the current view.
//
// Grouping and priority are consumed from events.json exactly as generated; this page never groups
// or scores articles itself. If the event index is missing, invalid or does not match the loaded
// articles, every raw article is shown individually, and an article absent from the index is always
// shown on its own.
"use strict";

const I18N = {
  en: {
    pageTitle: "Junson Capital — Fund Coverage News",
    title: "Fund Coverage News",
    prev: "‹ Earlier",
    next: "Later ›",
    today: "Today",
    allDates: "All dates",
    dateLabel: "Date",
    gpLabel: "Manager",
    sectorLabel: "Sub-sector",
    sortLabel: "Sort",
    sortPriority: "Sort: Priority",
    sortNewest: "Sort: Newest",
    allGps: "All managers",
    allSectors: "All sub-sectors",
    dateOption: "{date} ({n})",
    itemCount: "{n} items",
    itemCountOne: "1 item",
    filteredCount: "{shown} of {n} items",
    eventCount: "{e} events · {a} articles",
    eventCountFiltered: "{e} of {E} events · {a} of {A} articles",
    allScope: "{n} dates",
    readOriginal: "Read original →",
    unknownPublisher: "Unknown source",
    unreviewed: "Auto-selected · not yet reviewed",
    noToday: "No new items yet today ({today}). Showing the latest day, {date}.",
    noMatch: "No items match these filters.",
    noItems: "No news has been published yet.",
    loading: "Loading…",
    allLoading: "Loading all dates… {done} of {n}",
    allFailed: "{k} of {n} dates could not be loaded: {list}. This list is incomplete — it is not the full archive.",
    retry: "Retry",
    indexError: "The news index could not be loaded. Please reload the page or try again later.",
    dayError: "News for {date} could not be loaded. Try another date or reload the page.",
    groupingMissing: "Duplicate-coverage grouping is unavailable, so every source article is shown individually.",
    groupingStale: "Duplicate-coverage grouping does not match these articles, so every source article is shown individually.",
    sources: "Sources ({n})",
    sourceMissing: "Article details unavailable — that date did not load.",
    furtherCoverage: "Further coverage · first reported {date}",
    sourceUpdated: "Source updated · not verified as a material change",
    prio_urgent: "Urgent",
    prio_important: "Important",
    prio_useful: "Useful",
    prio_needs_review: "Needs review",
    potentialUrgent: "Potential urgent item — needs verification",
    legacyPriority: "No article here has an assessed priority yet. Earlier articles were collected without the source evidence the priority rules need, so they are marked Needs review and Priority order falls back to recency. Newly collected, adequately evidenced items can be marked Urgent, Important or Useful.",
    lastRefreshed: "Last refreshed {time} HKT",
    refreshFailed: "Latest refresh failed; showing the last successful update.",
    statusUnavailable: "Refresh status unavailable",
    footer: "Summaries are AI-drafted from the linked sources; follow the link for full details.",
    navNews: "News",
    navReports: "Reports",
    reportsTitle: "Reports",
    reportLangLabel: "Report language",
    reportMeta: "Published {date} · {lang} · PDF",
    reportOpen: "Open PDF",
    reportDownload: "Download PDF",
    reportLoading: "Loading report… {pct}",
    reportError: "The report could not be displayed here. Use Open PDF or Download PDF, or try again.",
    reportRetry: "Try again",
    reportPages: "{n} pages",
    reportPage: "Page {n} of {total}",
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    zoomFit: "Fit width",
    locale: "en-GB",
  },
  zh: {
    pageTitle: "Junson Capital — 基金覆盖新闻",
    title: "基金覆盖新闻",
    prev: "‹ 前一天",
    next: "后一天 ›",
    today: "今天",
    allDates: "全部日期",
    dateLabel: "日期",
    gpLabel: "管理人",
    sectorLabel: "子行业",
    sortLabel: "排序",
    sortPriority: "排序：优先级",
    sortNewest: "排序：最新",
    allGps: "全部管理人",
    allSectors: "全部子行业",
    dateOption: "{date}（{n}）",
    itemCount: "{n} 条新闻",
    itemCountOne: "1 条新闻",
    filteredCount: "{n} 条中的 {shown} 条",
    eventCount: "{e} 个事件 · {a} 篇文章",
    eventCountFiltered: "{E} 个事件中的 {e} 个 · {A} 篇文章中的 {a} 篇",
    allScope: "{n} 个日期",
    readOriginal: "阅读原文 →",
    unknownPublisher: "来源未知",
    unreviewed: "自动筛选 · 未经审核",
    noToday: "今天（{today}）暂无新内容，以下为最近一天：{date}。",
    noMatch: "没有符合筛选条件的新闻。",
    noItems: "暂未发布任何新闻。",
    loading: "加载中…",
    allLoading: "正在加载全部日期…{done}/{n}",
    allFailed: "{n} 个日期中有 {k} 个未能加载：{list}。以下列表不完整，并非全部存档。",
    retry: "重试",
    indexError: "无法加载新闻索引，请刷新页面或稍后再试。",
    dayError: "无法加载 {date} 的新闻，请选择其他日期或刷新页面。",
    groupingMissing: "重复报道归并暂不可用，所有来源文章均单独显示。",
    groupingStale: "重复报道归并与当前文章不一致，所有来源文章均单独显示。",
    sources: "来源（{n}）",
    sourceMissing: "文章详情不可用：该日期未能加载。",
    furtherCoverage: "后续报道 · 首次报道于 {date}",
    sourceUpdated: "来源已更新 · 未核实为实质性变化",
    prio_urgent: "紧急",
    prio_important: "重要",
    prio_useful: "参考",
    prio_needs_review: "待复核",
    potentialUrgent: "潜在紧急事项 — 有待核实",
    legacyPriority: "此处文章尚无经评估的优先级。早期文章收录时未保存优先级规则所需的来源证据，因此标为“待复核”，按优先级排序时实际按时间先后排列。新收录且证据充分的文章可标为紧急、重要或参考。",
    lastRefreshed: "最近更新：{time}（香港时间）",
    refreshFailed: "最近一次更新失败，当前显示上次成功更新的内容。",
    statusUnavailable: "更新状态不可用",
    footer: "摘要由 AI 根据所链接的来源撰写，详情请点击原文链接。",
    navNews: "新闻",
    navReports: "研究报告",
    reportsTitle: "研究报告",
    reportLangLabel: "报告语言",
    reportMeta: "发布日期 {date} · {lang} · PDF",
    reportOpen: "打开 PDF",
    reportDownload: "下载 PDF",
    reportLoading: "正在加载报告… {pct}",
    reportError: "报告无法在此显示。请使用“打开 PDF”或“下载 PDF”，或重试。",
    reportRetry: "重试",
    reportPages: "共 {n} 页",
    reportPage: "第 {n} 页，共 {total} 页",
    zoomIn: "放大",
    zoomOut: "缩小",
    zoomFit: "适应宽度",
    locale: "zh-CN",
  },
};

// Published reports. Only languages with an approved file are offered; otherwise English is shown.
const REPORTS = [{
  title: {en: "Private Credit Quarterly Report (2026Q3)", zh: "私募信贷季度报告（2026年第三季度）"},
  date: "2026-08-13",
  files: {en: "reports/junson-private-credit-report-2026q3-en-v2.pdf", zh: "reports/junson-private-credit-report-2026q3-zh-v2.pdf"},
}];

const REPORT_LANGS = {en: "English", zh: "中文"};
const LANG_KEY = "fund-coverage-news-lang";
const DAY_CONCURRENCY = 4;
const state = {
  lang: "en", index: null, status: null, fatal: false,
  date: null, notice: null, gp: "", sector: "",
  days: new Map(), dayErrors: new Set(), inflight: new Map(), token: 0,
  mode: "date", sort: "priority", allLoading: false,
  events: null, // {byCard: Map(card id -> event)} when events.json is present and well formed
  reportLang: null, // null follows the page language until the reader picks one
};

function t(key, params) {
  let text = I18N[state.lang][key] ?? I18N.en[key] ?? key;
  for (const [name, value] of Object.entries(params || {})) text = text.split(`{${name}}`).join(String(value));
  return text;
}

function readStoredLang() {
  try {
    const value = localStorage.getItem(LANG_KEY);
    return value === "en" || value === "zh" ? value : null;
  } catch {
    return null;
  }
}

function storeLang(lang) {
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    // Storage unavailable (private mode, blocked site data): the choice lasts for this visit.
  }
}

function todayHongKong() {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", {timeZone: "Asia/Hong_Kong", year: "numeric", month: "2-digit", day: "2-digit"})
    .format(new Date());
}

function formatDay(iso, style) {
  const parsed = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return iso;
  const options = style === "short"
    ? {timeZone: "UTC", day: "numeric", month: "short", year: "numeric", weekday: "short"}
    : {timeZone: "UTC", day: "numeric", month: "long", year: "numeric", weekday: "long"};
  return new Intl.DateTimeFormat(t("locale"), options).format(parsed);
}

function formatInstant(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat(t("locale"), {
    timeZone: "Asia/Hong_Kong", day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(parsed);
}

function el(tag, options, children) {
  const node = document.createElement(tag);
  if (options) {
    if (options.className) node.className = options.className;
    if (options.text !== undefined) node.textContent = options.text;
    for (const [name, value] of Object.entries(options.attrs || {})) node.setAttribute(name, value);
  }
  for (const child of children || []) if (child) node.appendChild(child);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function safeHttpUrl(value) {
  try {
    const url = new URL(String(value));
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function bilingual(value) {
  if (!value || typeof value !== "object") return "";
  return value[state.lang] || value.en || "";
}

// Older briefs were written from headlines and often claim the article "provided no further
// details". The pipeline cannot know that, so such sentences are not shown. Mirrors
// tools/summarize.py strip_absence_claims exactly (a browser test compares both on the archive).
const ABSENCE = {
  en: /\b(no (?:further|other|additional|more|specific)\b.{0,60}\b(?:details?|figures?|information|data|terms)\b|no (?:specific )?(?:managers?|funds?|figures)\b.{0,40}\b(?:named|disclosed|provided|given)\b|(?:was|were) not (?:provided|disclosed|given)|(?:did|does|do) not (?:provide|disclose|give|name) (?:any )?(?:further|more|additional|other)?|provides? no (?:further|additional|other) detail|consisted only of the headline|beyond the headline)/i,
  zh: /(未|没有)(?:进一步)?予?(提供|披露|给出|说明|点名|提及)|仅(有|包含)标题/,
};

function stripAbsence(text, lang) {
  const parts = (text || "").split(lang === "zh" ? /(?<=[。！？])|(?<=[。！？][”’）])/ : /(?<=[.!?])\s+|(?<=[.!?]["'”’)])\s+/);
  const kept = parts.filter((part) => part.trim() && !ABSENCE[lang === "zh" ? "zh" : "en"].test(part));
  return kept.join(lang === "zh" ? "" : " ").trim() || (text || "").trim();
}

function summaryText(item) {
  return stripAbsence(bilingual(item.summary), state.lang);
}

function label(kind, id) {
  const entry = state.index && state.index.labels && state.index.labels[kind] && state.index.labels[kind][id];
  return (entry && (entry[state.lang] || entry.en)) || id;
}

async function fetchJson(path) {
  const response = await fetch(path, {cache: "no-store"});
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function dates() {
  return (state.index && Array.isArray(state.index.dates)) ? state.index.dates : [];
}

function isList(value) {
  return Array.isArray(value) && value.every((id) => typeof id === "string");
}

// ---- Event index (consumed, never recomputed) -----------------------------------------------

// Structural check only. Membership against the loaded articles is checked per view (groupingFits).
function validateEvents(data) {
  if (!data || data.schema_version !== 1 || !Array.isArray(data.events)) return null;
  const byCard = new Map();
  for (const event of data.events) {
    if (!event || typeof event.event_id !== "string" || !isList(event.member_card_ids)) return null;
    if (!event.member_card_ids.includes(event.representative_card_id)) return null;
    if (!event.date_views || typeof event.date_views !== "object") return null;
    for (const view of Object.values(event.date_views)) {
      if (!view || !isList(view.member_card_ids) || !view.member_card_ids.includes(view.representative_card_id)) return null;
      if (view.member_card_ids.some((id) => !event.member_card_ids.includes(id))) return null;
    }
    for (const id of event.member_card_ids) {
      if (byCard.has(id)) return null; // Memberships must be disjoint.
      byCard.set(id, event);
    }
  }
  return {byCard};
}

// The index fits a set of loaded days when every day's mapped articles and the index's view of
// that day agree exactly. Articles missing from the index do not break the fit; they are singletons.
function groupingFits(days) {
  if (!state.events) return false;
  for (const day of days) {
    const ids = new Set(state.days.get(day).map((item) => item && item.id));
    const checked = new Set();
    for (const id of ids) {
      const event = state.events.byCard.get(id);
      if (!event) continue;
      const view = event.date_views[day];
      if (!view || !view.member_card_ids.includes(id)) return false;
      if (checked.has(event)) continue;
      checked.add(event);
      if (view.member_card_ids.some((member) => !ids.has(member))) return false;
    }
  }
  return true;
}

function cardTime(item) {
  const time = Date.parse(item.published_at || item.observed_at || `${item.date}T00:00:00+08:00`);
  return Number.isNaN(time) ? 0 : time;
}

function listOf(value) {
  return Array.isArray(value) ? value : [];
}

function singleton(item, order) {
  return {rep: item, members: [{card: item}], gps: listOf(item.gps), sectors: listOf(item.sectors),
    priority: null, rank: null, time: cardTime(item), order, event: null, firstDay: null};
}

// One entry per event for a single day, using that day's view (never the global representative).
function dayEntries(day) {
  const items = state.days.get(day).filter((item) => item && typeof item === "object");
  const grouped = groupingFits([day]);
  const byId = new Map(items.map((item) => [item.id, item]));
  const seen = new Set();
  const entries = [];
  for (const item of items) {
    const event = grouped ? state.events.byCard.get(item.id) : null;
    if (!event) {
      entries.push(singleton(item, entries.length));
      continue;
    }
    if (seen.has(event)) continue;
    seen.add(event);
    const view = event.date_views[day];
    const rep = byId.get(view.representative_card_id);
    const earlier = Object.keys(event.date_views).sort()[0];
    entries.push({rep, members: view.member_card_ids.map((id) => ({card: byId.get(id)})),
      gps: listOf(view.display_gps), sectors: listOf(view.display_sectors),
      priority: view.priority || null, rank: typeof view.priority_rank === "number" ? view.priority_rank : null,
      time: cardTime(rep), order: entries.length, event,
      firstDay: view.further_coverage && earlier < day ? earlier : null});
  }
  return {entries, grouped, problem: grouped ? null : (state.events ? "stale" : "missing")};
}

// One entry per event across every loaded day, using the global representative.
function allEntries() {
  const loaded = dates().filter((day) => state.days.has(day));
  const cards = new Map();
  for (const day of loaded) for (const item of state.days.get(day)) if (item && typeof item === "object") cards.set(item.id, item);
  const grouped = groupingFits(loaded);
  const entries = [];
  const mapped = new Set();
  if (grouped) {
    for (const event of new Set(state.events.byCard.values())) {
      const present = event.member_card_ids.filter((id) => cards.has(id));
      if (present.length === 0) continue; // All of its dates failed to load; reported in the notice.
      for (const id of present) mapped.add(id);
      const sources = new Map(listOf(event.sources).map((source) => [source && source.card_id, source]));
      const time = Date.parse(event.last_material_update_at);
      entries.push({rep: cards.get(event.representative_card_id) || cards.get(present[0]),
        members: event.member_card_ids.map((id) => ({card: cards.get(id), meta: sources.get(id)})),
        gps: listOf(event.display_gps), sectors: listOf(event.display_sectors),
        priority: event.priority || null, rank: typeof event.priority_rank === "number" ? event.priority_rank : null,
        time: Number.isNaN(time) ? cardTime(cards.get(present[0])) : time, order: entries.length, event, firstDay: null});
    }
  }
  for (const item of cards.values()) if (!mapped.has(item.id)) entries.push(singleton(item, entries.length));
  return {entries, grouped, problem: grouped ? null : (state.events ? "stale" : "missing")};
}

// Priority: the pipeline's rank, lower first; articles without a rank follow. Newest: latest first.
// Neither reads any text, so switching language never changes the order.
function sortEntries(entries) {
  const newest = (a, b) => b.time - a.time || a.order - b.order;
  if (state.sort === "newest") return entries.sort(newest);
  return entries.sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity) || newest(a, b));
}

function matches(entry) {
  return (!state.gp || entry.gps.includes(state.gp)) && (!state.sector || entry.sectors.includes(state.sector));
}

function articleCount(entries) {
  return entries.reduce((total, entry) => total + entry.members.filter((member) => member.card).length, 0);
}

// ---- Static text, status and controls -----------------------------------------------------

function applyStaticText() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.title = t("pageTitle");
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
  }
}

function renderStatus() {
  const node = document.getElementById("status");
  clear(node);
  const status = state.status;
  if (!status || !status.last_success_at) {
    node.textContent = t("statusUnavailable");
    return;
  }
  const schedule = status.schedule ? (status.schedule[state.lang] || status.schedule.en) : "";
  node.appendChild(document.createTextNode(
    t("lastRefreshed", {time: formatInstant(status.last_success_at)}) + (schedule ? ` · ${schedule}` : "")));
  if (status.last_refresh_result === "failed") {
    node.appendChild(el("span", {className: "status-warn", text: ` ${t("refreshFailed")}`}));
  }
}

function fillSelect(select, options, value) {
  clear(select);
  for (const [optionValue, text] of options) select.appendChild(el("option", {text, attrs: {value: optionValue}}));
  select.value = value;
}

function renderControls() {
  const list = dates();
  const counts = (state.index && state.index.counts) || {};
  const all = state.mode === "all";
  fillSelect(document.getElementById("dateSelect"),
    [["*", t("allDates")], ...list.map((day) => [day, t("dateOption", {date: formatDay(day, "short"), n: counts[day] ?? "?"})])],
    all ? "*" : (state.date || ""));
  const labels = (state.index && state.index.labels) || {};
  fillSelect(document.getElementById("gpSelect"),
    [["", t("allGps")], ...Object.keys(labels.gps || {}).map((id) => [id, label("gps", id)])], state.gp);
  fillSelect(document.getElementById("sectorSelect"),
    [["", t("allSectors")], ...Object.keys(labels.sectors || {}).map((id) => [id, label("sectors", id)])], state.sector);
  fillSelect(document.getElementById("sortSelect"),
    [["priority", t("sortPriority")], ["newest", t("sortNewest")]], state.sort);

  const position = list.indexOf(state.date);
  const noData = state.fatal || list.length === 0;
  document.getElementById("prev").disabled = noData || all || position < 0 || position >= list.length - 1;
  document.getElementById("next").disabled = noData || all || position <= 0;
  document.getElementById("allDates").setAttribute("aria-pressed", String(all));
  for (const id of ["today", "allDates", "dateSelect", "gpSelect", "sectorSelect", "sortSelect"]) {
    document.getElementById(id).disabled = noData;
  }
}

// ---- Cards ----------------------------------------------------------------------------------

function sourceLine(publisher, url, when) {
  const line = el("p", {className: "source"}, [el("span", {text: publisher || t("unknownPublisher")})]);
  if (when) line.appendChild(document.createTextNode(` · ${when}`));
  const href = safeHttpUrl(url);
  if (href) {
    line.appendChild(document.createTextNode(" · "));
    line.appendChild(el("a", {text: t("readOriginal"), attrs: {href, target: "_blank", rel: "noopener noreferrer"}}));
  }
  return line;
}

function articleWhen(item) {
  return item.published_at ? formatInstant(item.published_at) : formatDay(item.date, "short");
}

function renderSources(entry) {
  const list = el("ul", {className: "source-list"});
  for (const member of entry.members) {
    const item = member.card;
    if (item) {
      const source = item.source || {};
      list.appendChild(el("li", null, [
        el("p", {className: "source-head", text: bilingual(item.headline)}),
        sourceLine(source.publisher, source.url, articleWhen(item)),
        el("p", {className: "source-summary", text: summaryText(item)}),
      ]));
    } else {
      const meta = member.meta || {};
      list.appendChild(el("li", null, [
        sourceLine(meta.publisher, meta.url, meta.published_at ? formatInstant(meta.published_at) : ""),
        el("p", {className: "source-summary", text: t("sourceMissing")}),
      ]));
    }
  }
  return el("details", {className: "sources"}, [el("summary", {text: t("sources", {n: entry.members.length})}), list]);
}

function renderCard(entry) {
  const item = entry.rep;
  const card = el("article", {className: "card", attrs: {"data-card": String(item.id)}});
  const flags = [];
  if (item.review_status === "unreviewed") flags.push(el("span", {className: "badge", text: t("unreviewed")}));
  const level = entry.priority && entry.priority.priority;
  if (level && I18N.en[`prio_${level}`]) flags.push(el("span", {className: `prio prio-${level}`, text: t(`prio_${level}`)}));
  if (state.mode === "all") flags.push(el("span", {className: "when", text: formatDay(item.date, "short")}));
  if (flags.length) card.appendChild(el("div", {className: "flags"}, flags));
  if (entry.priority && entry.priority.potential_urgent === true) {
    card.appendChild(el("p", {className: "alert", text: t("potentialUrgent")}));
  }
  card.appendChild(el("h3", {className: "headline", text: bilingual(item.headline)}));
  card.appendChild(el("p", {className: "summary", text: summaryText(item)}));
  if (level) {
    const reason = bilingual(entry.priority.reason);
    if (reason) card.appendChild(el("p", {className: "reason", text: `${t(`prio_${level}`)}: ${reason}`}));
  }

  const source = item.source || {};
  card.appendChild(sourceLine(source.publisher, source.url));

  const notes = [];
  if (entry.firstDay) {
    const jump = el("button", {className: "linkish", text: t("furtherCoverage", {date: formatDay(entry.firstDay, "short")}),
      attrs: {type: "button"}});
    jump.addEventListener("click", () => showDate(entry.firstDay));
    notes.push(jump);
  }
  if (entry.event && entry.event.updated === true) notes.push(el("span", {text: t("sourceUpdated")}));
  if (notes.length) card.appendChild(el("p", {className: "notes"}, notes));
  if (entry.members.length > 1) card.appendChild(renderSources(entry));

  const tags = [
    ...entry.gps.map((id) => el("span", {className: "tag tag-gp", text: label("gps", id)})),
    ...entry.sectors.map((id) => el("span", {className: "tag", text: label("sectors", id)})),
  ];
  if (item.region) tags.push(el("span", {className: "tag", text: label("regions", item.region)}));
  if (tags.length) card.appendChild(el("p", {className: "tags"}, tags));
  return card;
}

// Heading count, notices and cards shared by the day and all-dates views.
function renderList(main, heading, result, scope) {
  const shown = sortEntries(result.entries.filter(matches));
  const filtered = Boolean(state.gp || state.sector);
  const total = articleCount(result.entries);
  let count;
  if (result.grouped) {
    count = filtered
      ? t("eventCountFiltered", {e: shown.length, E: result.entries.length, a: articleCount(shown), A: total})
      : t("eventCount", {e: result.entries.length, a: total});
  } else {
    count = filtered
      ? t("filteredCount", {shown: shown.length, n: total})
      : (total === 1 ? t("itemCountOne") : t("itemCount", {n: total}));
  }
  heading.appendChild(el("p", {className: "count", text: scope ? `${count} · ${scope}` : count}));
  if (result.problem && total > 0) {
    main.appendChild(el("p", {className: "notice", text: t(result.problem === "stale" ? "groupingStale" : "groupingMissing")}));
  }
  const prioritised = shown.filter((entry) => entry.priority);
  if (state.sort === "priority" && prioritised.length && prioritised.every((entry) => entry.priority.priority === "needs_review")) {
    main.appendChild(el("p", {className: "notice", text: t("legacyPriority")}));
  }
  if (shown.length === 0) {
    main.appendChild(el("p", {className: "state", text: filtered ? t("noMatch") : t("noItems")}));
    return;
  }
  for (const entry of shown) main.appendChild(renderCard(entry));
}

function renderMain() {
  const main = document.getElementById("main");
  clear(main);
  if (state.fatal) {
    main.appendChild(el("p", {className: "state", text: t("indexError")}));
    return;
  }
  if (state.mode === "all") {
    renderAll(main);
    return;
  }
  if (!state.date) {
    main.appendChild(el("p", {className: "state", text: t("noItems")}));
    return;
  }
  if (state.notice) {
    main.appendChild(el("p", {className: "notice", text: t("noToday", {
      today: formatDay(state.notice.today), date: formatDay(state.date)})}));
  }
  const heading = el("div", {className: "day-head"}, [el("h2", {text: formatDay(state.date)})]);
  main.appendChild(heading);

  if (state.dayErrors.has(state.date)) {
    main.appendChild(el("p", {className: "state", text: t("dayError", {date: formatDay(state.date)})}));
    return;
  }
  if (!state.days.has(state.date)) {
    main.appendChild(el("p", {className: "state", text: t("loading")}));
    return;
  }
  renderList(main, heading, dayEntries(state.date));
}

function renderAll(main) {
  const list = dates();
  const heading = el("div", {className: "day-head"}, [el("h2", {text: t("allDates")})]);
  main.appendChild(heading);
  if (list.length === 0) {
    main.appendChild(el("p", {className: "state", text: t("noItems")}));
    return;
  }
  if (state.allLoading) {
    const done = list.filter((day) => state.days.has(day) || state.dayErrors.has(day)).length;
    main.appendChild(el("p", {className: "state", text: t("allLoading", {done, n: list.length})}));
    return;
  }
  const failed = list.filter((day) => !state.days.has(day));
  if (failed.length) {
    const retry = el("button", {className: "retry", text: t("retry"), attrs: {type: "button"}});
    retry.addEventListener("click", showAll);
    main.appendChild(el("div", {className: "notice notice-warn", attrs: {role: "alert"}}, [
      el("span", {text: t("allFailed", {k: failed.length, n: list.length,
        list: failed.map((day) => formatDay(day, "short")).join(", ")})}), document.createTextNode(" "), retry]));
  }
  renderList(main, heading, allEntries(), t("allScope", {n: list.length - failed.length}));
}

// ---- Loading and navigation -----------------------------------------------------------------

// One request per day at a time; a finished day stays cached for both views.
function loadDay(day) {
  if (state.days.has(day)) return Promise.resolve();
  if (!state.inflight.has(day)) {
    state.inflight.set(day, fetchJson(`./data/${day}.json`)
      .then((data) => {
        state.days.set(day, Array.isArray(data.items) ? data.items : []);
        state.dayErrors.delete(day);
      }, () => {
        state.dayErrors.add(day);
      })
      .finally(() => state.inflight.delete(day)));
  }
  return state.inflight.get(day);
}

async function showDate(day, notice) {
  state.mode = "date";
  state.date = day;
  state.notice = notice || null;
  renderControls();
  renderMain();
  if (state.days.has(day)) return;
  const token = ++state.token;
  await loadDay(day);
  if (token === state.token && state.mode === "date" && state.date === day) renderMain();
}

async function showAll() {
  state.mode = "all";
  state.notice = null;
  const token = ++state.token;
  const pending = dates().filter((day) => !state.days.has(day));
  state.allLoading = pending.length > 0;
  renderControls();
  renderMain();
  let next = 0;
  const worker = async () => {
    while (next < pending.length) {
      await loadDay(pending[next++]);
      if (token === state.token && state.mode === "all") renderMain();
    }
  };
  await Promise.all(Array.from({length: Math.min(DAY_CONCURRENCY, pending.length)}, worker));
  if (token !== state.token) return;
  state.allLoading = false;
  if (state.mode === "all") renderMain();
}

function openToday() {
  const list = dates();
  if (list.length === 0) {
    state.mode = "date";
    state.date = null;
    renderControls();
    renderMain();
    return;
  }
  const today = todayHongKong();
  // Never present an older day as today: say so, then show the most recent day.
  if (list.includes(today)) showDate(today);
  else showDate(list[0], {today});
}

// ---- Reports ----------------------------------------------------------------------------------

function renderReports() {
  const root = document.getElementById("reports");
  clear(root);
  root.appendChild(el("h2", {text: t("reportsTitle")}));
  const lang = state.reportLang || state.lang;
  for (const report of REPORTS) {
    const section = el("section", {className: "report"});
    section.appendChild(el("h3", {className: "headline", text: bilingual(report.title)}));
    const shownLang = report.files[lang] ? lang : "en";
    const picker = el("div", {className: "lang report-lang", attrs: {role: "group", "aria-label": t("reportLangLabel")}});
    for (const code of Object.keys(REPORT_LANGS).filter((code) => report.files[code])) {
      const button = el("button", {text: REPORT_LANGS[code], attrs: {type: "button", "aria-pressed": String(code === shownLang)}});
      button.addEventListener("click", () => {
        state.reportLang = code;
        renderReports();
      });
      picker.appendChild(button);
    }
    section.appendChild(picker);

    const href = report.files[shownLang];
    section.appendChild(el("p", {className: "count", text: t("reportMeta", {
      date: formatDay(report.date, "short"), lang: REPORT_LANGS[shownLang]})}));
    const actions = el("p", {className: "report-actions"}, [
      el("a", {className: "button", text: t("reportOpen"), attrs: {href, target: "_blank", rel: "noopener"}}),
      el("a", {className: "button", text: t("reportDownload"), attrs: {href, download: href.split("/").pop()}}),
    ]);
    section.appendChild(actions);
    section.appendChild(pdfViewer(href, bilingual(report.title)));
    root.appendChild(section);
  }
}

// Inline report reading uses PDF.js 6.3.289 hosted in vendor/pdfjs, not the browser's own PDF
// plugin: phones and some embedded browsers have no plugin and showed a blank pane. Pages are drawn
// to canvases only as they scroll into view. "ready" is set only after page 1 has been painted.
const reportDocs = new Map(); // href -> Promise<PDFDocumentProxy>, shared across re-renders
const reportProgress = new Map(); // href -> fraction loaded
const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];

function loadReport(href) {
  if (!reportDocs.has(href)) {
    const promise = import("./vendor/pdfjs/pdf.min.mjs").then((pdfjs) => {
      pdfjs.GlobalWorkerOptions.workerSrc = "vendor/pdfjs/pdf.worker.min.mjs";
      const task = pdfjs.getDocument({url: href, isEvalSupported: false, enableXfa: false});
      task.onProgress = ({loaded, total}) => reportProgress.set(href, total ? loaded / total : 0);
      return task.promise;
    });
    promise.catch(() => reportDocs.delete(href)); // a later attempt starts afresh
    reportDocs.set(href, promise);
  }
  return reportDocs.get(href);
}

function pdfViewer(href, title) {
  const viewer = el("div", {className: "pdf-viewer", attrs: {"data-src": href, "data-state": "loading"}});
  const tool = (cls, text, key) => el("button", {className: cls, text, attrs: {type: "button", "aria-label": t(key)}});
  const zoomOut = tool("pdf-zoom-out", "−", "zoomOut");
  const zoomIn = tool("pdf-zoom-in", "+", "zoomIn");
  const fit = tool("pdf-fit", t("zoomFit"), "zoomFit");
  const zoomLabel = el("output", {className: "pdf-zoom", text: "100%"});
  const count = el("span", {className: "pdf-count"});
  const scroll = el("div", {className: "pdf-scroll", attrs: {tabindex: "0", role: "region", "aria-label": title}});
  const status = el("p", {className: "state", attrs: {role: "status"}, text: t("reportLoading", {pct: ""})});
  scroll.appendChild(status);
  viewer.append(el("div", {className: "pdf-toolbar", attrs: {role: "toolbar", "aria-label": title}},
    [zoomOut, zoomLabel, zoomIn, fit, count]), scroll);
  const timer = setInterval(() => {
    const done = reportProgress.get(href);
    if (done) status.textContent = t("reportLoading", {pct: Math.round(done * 100) + "%"});
  }, 250);
  let zoom = 1;
  let pages = [];

  const fail = () => {
    clearInterval(timer);
    viewer.dataset.state = "error";
    const retry = el("button", {className: "retry", text: t("reportRetry"), attrs: {type: "button"}});
    retry.addEventListener("click", () => viewer.replaceWith(pdfViewer(href, title)));
    scroll.replaceChildren(el("div", {className: "state", attrs: {role: "alert"}}, [el("p", {text: t("reportError")}), retry]));
  };

  // Pages paint one at a time in scroll order (a chart-heavy page can take ~2 s), so page 1 is never
  // slowed by its neighbours. Fit width is the scroll area's width; zoom multiplies it.
  let queue = Promise.resolve();
  const paint = async (entry) => {
    const key = String(Math.round(zoom * 100));
    if (!entry.visible || entry.node.dataset.rendered === key) return;
    const width = parseFloat(entry.node.style.width);
    const ratio = Math.min(window.devicePixelRatio || 1, 2, 4096 / width); // >2x costs time, not legibility
    const viewport = entry.page.getViewport({scale: (width / entry.page.getViewport({scale: 1}).width) * ratio});
    const canvas = el("canvas", {attrs: {role: "img", "aria-label": entry.label}});
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);
    await entry.page.render({canvas, canvasContext: canvas.getContext("2d"), viewport}).promise;
    entry.node.replaceChildren(canvas);
    entry.node.dataset.rendered = key;
    if (entry.number === 1 && viewer.dataset.state === "loading") {
      viewer.dataset.state = "ready";
      status.remove();
    }
  };
  const draw = (entry) => {
    if (entry.queued) return;
    entry.queued = true;
    queue = queue.then(() => { entry.queued = false; return paint(entry); }).catch(fail);
  };

  const layout = () => {
    const width = Math.max(200, scroll.clientWidth - 24) * zoom;
    for (const entry of pages) {
      entry.node.style.width = width + "px";
      entry.node.style.height = width * entry.ratio + "px";
    }
    zoomLabel.textContent = Math.round(zoom * 100) + "%";
    zoomOut.disabled = zoom === ZOOMS[0];
    zoomIn.disabled = zoom === ZOOMS[ZOOMS.length - 1];
    for (const entry of pages) if (entry.visible) draw(entry);
  };

  loadReport(href).then(async (doc) => {
    const loaded = await Promise.all(Array.from({length: doc.numPages}, (_, i) => doc.getPage(i + 1)));
    clearInterval(timer);
    pages = loaded.map((page, i) => {
      const base = page.getViewport({scale: 1});
      return {page, number: i + 1, ratio: base.height / base.width, visible: false,
        label: t("reportPage", {n: i + 1, total: doc.numPages}),
        node: el("div", {className: "pdf-page", attrs: {"data-page": String(i + 1)}})};
    });
    count.textContent = t("reportPages", {n: doc.numPages});
    scroll.replaceChildren(...pages.map((entry) => entry.node));
    status.textContent = t("reportLoading", {pct: ""}); // stays in the toolbar until page 1 is painted
    count.before(status);
    const observer = new IntersectionObserver((changes) => {
      for (const change of changes) {
        const entry = pages[Number(change.target.dataset.page) - 1];
        entry.visible = change.isIntersecting;
        if (entry.visible) draw(entry);
      }
    }, {root: scroll, rootMargin: "600px 0px"});
    for (const entry of pages) observer.observe(entry.node);
    new ResizeObserver(layout).observe(scroll);
    layout();
  }).catch(fail);

  const step = (direction) => {
    const next = ZOOMS[ZOOMS.indexOf(zoom) + direction];
    if (!next) return;
    const position = scroll.scrollTop / Math.max(1, scroll.scrollHeight);
    zoom = next;
    layout();
    scroll.scrollTop = position * scroll.scrollHeight;
  };
  zoomOut.addEventListener("click", () => step(-1));
  zoomIn.addEventListener("click", () => step(1));
  fit.addEventListener("click", () => { zoom = 1; layout(); });
  return viewer;
}

function applyView() {
  const reports = location.hash === "#reports";
  document.getElementById("toolbar").hidden = reports;
  document.getElementById("main").hidden = reports;
  document.getElementById("reports").hidden = !reports;
  for (const link of document.querySelectorAll("[data-view]")) {
    if ((link.dataset.view === "reports") === reports) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  if (reports) renderReports();
}

function setLang(lang) {
  state.lang = lang;
  storeLang(lang);
  applyStaticText();
  renderStatus();
  renderControls();
  renderMain();
  if (location.hash === "#reports") renderReports();
}

// ---- Start-up -------------------------------------------------------------------------------

function bindEvents() {
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.addEventListener("click", () => setLang(button.dataset.lang));
  }
  document.getElementById("prev").addEventListener("click", () => {
    const list = dates();
    const position = list.indexOf(state.date);
    if (position >= 0 && position < list.length - 1) showDate(list[position + 1]);
  });
  document.getElementById("next").addEventListener("click", () => {
    const list = dates();
    const position = list.indexOf(state.date);
    if (position > 0) showDate(list[position - 1]);
  });
  document.getElementById("today").addEventListener("click", openToday);
  document.getElementById("allDates").addEventListener("click", showAll);
  document.getElementById("dateSelect").addEventListener("change", (event) => {
    if (event.target.value === "*") showAll();
    else showDate(event.target.value);
  });
  document.getElementById("gpSelect").addEventListener("change", (event) => {
    state.gp = event.target.value;
    renderMain();
  });
  document.getElementById("sectorSelect").addEventListener("change", (event) => {
    state.sector = event.target.value;
    renderMain();
  });
  document.getElementById("sortSelect").addEventListener("change", (event) => {
    state.sort = event.target.value;
    renderMain();
  });
  window.addEventListener("hashchange", applyView);
}

async function init() {
  const browserZh = (navigator.language || "").toLowerCase().startsWith("zh");
  state.lang = readStoredLang() || (browserZh ? "zh" : "en");
  bindEvents();
  applyStaticText();
  applyView();
  const [index, status, events] = await Promise.allSettled(
    ["./data/index.json", "./data/status.json", "./data/events.json"].map(fetchJson));
  if (index.status === "fulfilled") state.index = index.value;
  else state.fatal = true;
  // A missing status is shown as "status unavailable", never as a healthy refresh.
  state.status = status.status === "fulfilled" ? status.value : null;
  state.events = events.status === "fulfilled" ? validateEvents(events.value) : null;
  renderStatus();
  if (state.fatal) {
    renderControls();
    renderMain();
    return;
  }
  openToday();
}

init();
