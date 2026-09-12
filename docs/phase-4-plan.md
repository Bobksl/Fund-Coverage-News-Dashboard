# Phase 4: analyst-reviewed bilingual demo and bounded model experiment

Review date: 2026-09-12. Reviewed implementation: `15c11c7`.

## Current result and revised scope

Phase 2 closed with a measured deterministic-baseline FAIL. The structured LLM remains untested.
Phase 3 delivered the deadline fallback: a static local mechanics demo, not the originally planned
ingestion pilot. This is a useful scope reduction; do not retrospectively label it a passed
ingestion gate. Phase 4 should complete an analyst-reviewed research demo using the existing
corpus, with a separately reported model experiment. No infrastructure expansion is needed.

| Result independently checked | Finding |
|---|---|
| Frozen labels, evidence and split file hashes | All match freeze-001 |
| Three prediction file hashes | All match the saved evaluation |
| Headline metrics recomputed from predictions and labels | Match saved calibration, holdout and challenge results |
| Natural holdout | 21 positive events; 4 selected; precision 75%; recall 3/21 = 14.3%; critical surfaced 1/2 |
| Natural calibration | 57 positive events; 12 selected; precision 83.3%; recall 10/57 = 17.5%; critical surfaced 6/6 |
| Independent challenge partition in saved evaluation | 10 positive events; 6 selected; precision 50%; recall 3/10 = 30%; critical surfaced 1/3; undersized |
| Tests | 219 pass outside sandbox; sandbox had two temporary-directory permission errors |
| Spec validator | Zero errors |
| Browser smoke | Local page loads; September 9 cards and September 10 empty state render; Next disables at end |

Hash matching verifies present artifacts, not independently witnessed historical freeze ordering.
This was a focused code/artifact review and browser smoke check, not a complete security audit.
Evidence remains short excerpts (including gated ledes), one-reviewer labels, and a publication-skewed
corpus. No second-reviewer agreement, bilingual utility or automated readiness is established.

## Findings that affect implementation

1. **Classifier context is incomplete.** `tools/classifier.py:build_prompt` passes event subtype
   enums, sector/theme IDs and numeric anchors, but omits entity mappings, A/B/C definitions,
   sector/theme inclusion and transmission rules, and anchor meanings. A real provider alone
   cannot make this a well-specified classification experiment. Supply compact substantive rules
   and an explicit complete response schema before making paid calls. Validate nested identity,
   entity IDs, gates, component reasons and evidence references; missing identity currently
   defaults to pass in `_to_proposal`. Invalid/uncertain output must become review, not an exception
   or a fabricated pass.
2. **The baseline diagnosis overstates the specification gap.** Level B already exists in the
   ontology and `baseline.propose` has a sector-only branch. The demonstrated gap is inadequate
   deterministic recognition/transmission/materiality handling, compounded by short evidence.
   Do not add unconditional sector publication or alter the editorial scope merely to raise recall.
3. **Freeze enforcement is incomplete.** `evaluator.require_freeze` verifies prediction bytes but
   only tests presence of other hashes; `runner.run` does not require a joint evidence/label
   freeze. The checked historical files do match, so this does not invalidate the reproduced
   counts. Add a small custodian preflight that verifies actual files, including evidence-text
   hashes, and writes an inference-only manifest without gold. Do not claim the current helper
   proves every future run is frozen. Freeze prompt/config/model parameters as well.
4. **Daily selection is not yet daily end to end.** `runner.run` calls `select_edition` once for a
   whole partition. The demo exporter instead includes all shortlist recommendations and mixes
   calibration, holdout and challenge into one calendar. Keep recommendation metrics separate
   from capacity-limited edition metrics. Build editions per Asia/Hong_Kong day, from natural
   records only; keep historical challenge examples in a separate diagnostic view.
5. **UI safety and correctness need a small repair.** `site/app.js` interpolates source text/URLs
   into `innerHTML`. Use DOM nodes/textContent and an http/https URL allowlist. Add protection
   against out-of-order day fetches; date dropdown changes must refresh navigation buttons.
   Default to today's Hong Kong date with an honest no-edition state, plus an explicit latest
   historical edition shortcut. Current automatic last-nonempty default is not today's news.
6. **Serving the repository root exposes unnecessary local files.** The documented plain
   `http.server` binds beyond localhost by default and serves `work/` and repository files.
   Export a dedicated ignored demo directory containing only UI and approved edition JSON;
   serve it on 127.0.0.1. No web service may expose gold, raw outputs, secrets or `.git`.
7. **English explanations are not finished summaries.** Current cards say things such as
   'Monitored sector without a tracked entity subject'; Chinese is absent. Preserve this
   historical mechanics output, but build factual summaries and distinct interpretations from
   evidenced claims. Drafting's numeric/parity checks are useful heuristics, not proof of grounding.

## Ordered implementation slices

### 4A — safe, reproducible foundation

Fix findings 1, 3, 4 and 5 with focused tests, before live model inference or broader sharing.
Preserve freeze-001/run-001 and their FAIL. Add an explicit run command, immutable run IDs,
actual evidence-body loading with digest checks, retries/timeouts, saved raw responses and replay.
Use one provider and one structured classifier call per candidate; one bilingual draft call per
shortlisted event. No multi-agent runtime or replacement framework.

### 4B — bounded model comparison

Use a configured local credential, never pasted into chat or Git. If unavailable, finish adapter,
replay and demo work, and report live inference as unavailable. Do not promise a one-hour result.
Confirm a provider/model and spending cap before a billed run if not already authorized.

First use synthetic contract tests, then 10-15 calibration articles for a smoke run. Choose them
before seeing model outputs to cover direct vehicles, sector-only relevance, macro transmission,
ambiguous roles, irrelevant marketing and inaccessible evidence. At most one calibration-driven
prompt repair, then freeze prompt, config, model and sampling parameters. Run the full calibration
partition and one historical holdout comparison in fresh inference context, with no gold material.
Save predictions before evaluator access; report costs, failures and latency, not only precision.

The old holdout has already been inspected and its failures discussed. Reuse it transparently as
a historical comparison, not a newly sealed validation. A later readiness claim needs a fresh
temporal holdout with enough independently labeled publish-worthy events. Do not delay the
reviewed demo for recollection, pad the existing challenge set or change old labels to pass.
Report natural and challenge metrics separately; distinguish the 31 independently curated records
from the 60 natural-linked challenge coverage annotations when describing independence.

### 4C — reviewed bilingual editions

Produce one complete historical edition of up to 6-10 useful events (no minimum), preferably
several editions if supply/time permits. Use natural-feed evidence; show the actual historical
date. Model-selected events and analyst-added events must remain distinguishable in the private
audit. If selection still performs poorly, an explicitly analyst-curated demonstration is an
acceptable product outcome; never count manual additions as model recall.

Create minimal claim records with source/excerpt references, draft summary and 'Why it matters'
in English/Simplified Chinese, and record reviewer ID, reviewed card revision/hash, time and
approve/reject status in a separate local CSV/JSON. A simple file-based review step is sufficient;
no approval UI/backend is necessary. Only export approved exact revisions. Later edits invalidate
approval. Never reuse benchmark labels as publication approval.

### 4D — finish the existing static page and handover

Reuse `site/`, Python and JSON. Add EN/ZH toggle, factual headline/summary, separate interpretation,
manager/vehicle, sector, geography and event tags, safe source links, honest stale/empty/error
states and accessible keyboard/mobile layout. Keep score/rule details in an optional diagnostics
area, not the main investment-reading flow. Serve a minimal isolated bundle as described above.
Retain the existing corpus window; do not implement a 90-day collector or retention job now.

## Acceptance and stopping rules

- Engineering: tests pass, offline replay works, real body hashes verified, malformed output
  enters review, no gold crosses inference boundary, daily caps apply per day.
- Product: at least one actual historical edition with all exported cards explicitly reviewed;
  factual and interpretation text separated, EN/ZH reviewed for amounts, currency, roles and
  uncertainty. No fabricated items to fill the daily target. Record if useful supply is too thin.
- Browser: today/previous/latest historical dates, empty/error states, rapid navigation, safe
  hostile-text rendering, language toggle, source links and small-screen layout verified.
- Packaging: no private corpus, labels or credentials served; localhost-only command works.
- Evaluation: preserve the baseline FAIL, disclose historical reuse and undersized challenge;
  no automated-readiness claim unless the original applicable criteria are actually met.
- Deliver two independent dispositions: `reviewed_demo_ready` and `automated_selection_readiness`.
  The former may pass while the latter remains fail/untested/inconclusive.

Defer ingestion scheduling, hosting, databases, authentication, notifications, vector search and
extra agents. The next phase after this demo is fresh-sample validation and a small manual refresh
pilot if warranted, not automatic production deployment.
