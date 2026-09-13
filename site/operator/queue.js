// Operator review queue. Reads queue.json written by `python -m tools.manual_update build-queue`
// from the directory this page is served from. Same safety rules as site/app.js: DOM nodes and
// textContent only (model reasons and article titles are untrusted), http/https links only, and
// no call anywhere except a same-origin fetch of queue.json.
const HK_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Hong_Kong", year: "numeric", month: "short", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hour12: false,
});
const SECTIONS = [
  ["shortlisted", "Shortlisted — needs a draft and ledger approval before publishing"],
  ["reserve", "Reserve — manual approval only"],
  ["review", "Sent for review"],
  ["suppressed", "Suppressed"],
];

function el(tag, options, children) {
  const node = document.createElement(tag);
  if (options) {
    if (options.className) node.className = options.className;
    if (options.text !== undefined) node.textContent = options.text;
    if (options.attrs) for (const [key, value] of Object.entries(options.attrs)) node.setAttribute(key, value);
  }
  for (const child of children || []) if (child) node.appendChild(child);
  return node;
}

function clearChildren(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function formatInstant(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : `${HK_TIME.format(parsed)} HKT`;
}

function isSafeHttpUrl(value) {
  try {
    const url = new URL(value, window.location.href);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function sourceNode(source) {
  const label = `${source.publisher || "Unknown publisher"}: ${source.title || "Untitled"}` +
    (source.published_date ? ` (${source.published_date})` : "");
  if (source.url && isSafeHttpUrl(source.url)) {
    return el("div", {}, [el("a", {text: label, attrs: {href: source.url, target: "_blank", rel: "noopener noreferrer"}})]);
  }
  return el("div", {text: `${label} (no verifiable link)`});
}

function table(headers, rows) {
  return el("div", {className: "table-wrap"}, [el("table", {}, [
    el("tr", {}, headers.map((h) => el("th", {text: h}))),
    ...rows.map((row) => el("tr", {}, row.map((cell) => el("td", {text: cell ?? "—"})))),
  ])]);
}

function draftText(draft) {
  if (!draft) {
    return "No draft. Only an exact input drafted earlier can replay; drafting a new card needs " +
      "paid model calls, which are not approved for this demo.";
  }
  const approval = draft.approved_exact_in.length
    ? `approved at this exact revision and content in: ${draft.approved_exact_in.join(", ")}`
    : "not approved at this exact revision and content";
  return `Draft ${draft.status} · content ${draft.content_hash ? draft.content_hash.slice(0, 12) : "none"} · ` +
    `${approval}. It appears in an edition only after the operator's publish step.`;
}

function eventCard(event) {
  const title = (event.sources[0] && event.sources[0].title) || event.event_id;
  const shortlisted = event.bucket === "shortlisted";
  const pills = el("div", {}, [
    el("span", {className: "pill", text: event.recommendation}),
    el("span", {className: "pill", text: `score ${event.total_score ?? "n/a"}`}),
    event.relevance_level ? el("span", {className: "pill", text: `level ${event.relevance_level}`}) : null,
    event.edition_position ? el("span", {className: "pill", text: `edition: ${event.edition_position}`}) : null,
    el("span", {className: "pill", text: `publication: ${event.publication_status}`}),
    shortlisted ? el("span", {className: "pill", text: `draft: ${event.draft ? event.draft.status : "none"}`}) : null,
  ]);
  const why = el("ul", {className: "why"}, event.reasons.map((reason) =>
    el("li", {}, [el("strong", {text: `${reason.code}: `}), document.createTextNode(reason.explanation)])));
  const gatePills = el("div", {}, Object.entries(event.gates).map(([gate, outcome]) =>
    el("span", {className: `pill ${outcome}`, text: `${gate}: ${outcome}`})));
  const facts = [
    event.score_band ? el("div", {className: "muted", text: `Score-only band (gates decide the outcome): ${event.score_band}`}) : null,
    event.eligibility_reason ? el("div", {className: "muted", text: `Eligibility: ${event.eligibility_reason}`}) : null,
  ];
  const transmission = event.transmission || {};
  const details = el("details", {}, [
    el("summary", {text: "Gates, component scores and transmission"}),
    gatePills,
    table(["Component", "Points", "Model reason (untrusted)", "Evidence refs"],
          event.components.map((c) => [c.name, String(c.points ?? "null"), c.reason, (c.evidence_refs || []).join(", ")])),
    table(["Trigger", "Mechanism", "Outcome", "Uncertainty"],
          [[transmission.trigger, transmission.mechanism, transmission.outcome, transmission.uncertainty]]),
    el("div", {className: "muted", text: `Provenance: ${event.provenance.model} · prompt ${event.provenance.prompt_version} · ` +
      `${event.provenance.replayed_stored_response ? "replayed stored response (no new model call)" : "live response"} · event ${event.event_id} revision ${event.revision}`}),
  ]);
  const sources = el("div", {className: "sources"}, event.sources.map(sourceNode));
  const draft = shortlisted ? el("div", {className: "draft", text: draftText(event.draft)}) : null;
  const ledger = event.ledger_decisions.length === 0 ? null : el("div", {className: "ledger"}, [
    el("div", {text: "Ledger history for this event id (a row approves only the exact content hash it recorded):"}),
    ...event.ledger_decisions.map((row) => el("div", {
      text: `${row.ledger}: ${row.status} revision ${row.revision} by ${row.reviewer_id} at ${formatInstant(row.reviewed_at)}`})),
  ]);
  return el("div", {className: "card"}, [
    el("h3", {text: title}), pills, why, ...facts, sources,
    el("div", {className: "muted", text: `Article dates: ${event.article_dates.join(", ") || "undated"}`}),
    draft, ledger, details,
  ]);
}

function awaitingCard(entry) {
  return el("div", {className: "card"}, [
    el("h3", {text: entry.title}),
    sourceNode({publisher: entry.publisher, title: entry.title, url: entry.url, published_date: entry.published_date}),
    el("div", {className: "why", text: entry.reason}),
    el("div", {className: "muted", text: `article ${entry.article_id} · input ${entry.input_hash}`}),
  ]);
}

function render(queue) {
  const counts = queue.counts;
  document.getElementById("queueMeta").textContent =
    `Queue built ${formatInstant(queue.built_at)} · ${queue.profile.model_id} prompt ${queue.profile.prompt_version} · ` +
    `${counts.articles} articles: ${counts.shortlisted} shortlisted, ${counts.reserve} reserve, ` +
    `${counts.review} review, ${counts.suppressed} suppressed, ${counts.awaiting_classification} awaiting classification`;
  const main = document.getElementById("main");
  clearChildren(main);
  for (const [bucket, heading] of SECTIONS) {
    const events = queue.events.filter((event) => event.bucket === bucket);
    main.appendChild(el("h2", {text: `${heading} (${events.length})`}));
    if (events.length === 0) main.appendChild(el("p", {className: "empty", text: "None."}));
    for (const event of events) main.appendChild(eventCard(event));
  }
  main.appendChild(el("h2", {text: `Awaiting classification (${queue.awaiting.length})`}));
  if (queue.awaiting.length === 0) main.appendChild(el("p", {className: "empty", text: "None."}));
  for (const entry of queue.awaiting) main.appendChild(awaitingCard(entry));
  main.appendChild(el("p", {className: "muted", text: queue.limits}));
}

async function load() {
  const button = document.getElementById("reloadQueue");
  button.disabled = true;
  try {
    const response = await fetch("./queue.json", {cache: "no-store"});
    if (!response.ok) throw new Error(`queue.json: HTTP ${response.status}`);
    render(await response.json());
  } catch (error) {
    document.getElementById("queueMeta").textContent =
      `Could not load queue.json (${error.message}); the view below, if any, is from the previous load.`;
  } finally {
    button.disabled = false;
  }
}

document.getElementById("reloadQueue").addEventListener("click", load);
load();
