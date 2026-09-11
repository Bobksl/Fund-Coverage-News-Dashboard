# Editorial rulebook

Version 0.1.0 — provisional calibration baseline, 2026-09-10.

## Purpose and authority

Select a small set of public events that could change an alternatives investor's assessment of a monitored manager/vehicle, strategy risk or return, deployment, fundraising, liquidity, valuation, financing or exit conditions. Private credit is the strongest focus; VC, PE and real estate remain in scope through explicit portfolio or market transmission.

The current handover defines scope. Config files define canonical IDs, score anchors and tunable defaults. This rulebook defines precedence and interpretation. If they disagree, record the conflict and resolve it before evaluating affected cases; do not quietly change a threshold. All Phase 1 examples are hypothetical editorial fixtures, not real news, analyst ground truth or demonstrated classifier accuracy.

The monitoring list is not a position ledger. Do not write that a fund is held, quantify portfolio sensitivity or infer a borrower exposure without an authorized private exposure record. Level A means direct involvement of a monitored entity; `held_status` remains separately `unknown`, `monitored` or `confirmed_held`.

## Ordered decision rules

1. **ED01 — Evidence:** Capture accessible evidence, source identity, dates and availability. A search snippet or title may discover a story but cannot support an invented full summary. Insufficient evidence → `review_required`, not a scored rejection.
2. **ED02 — Resolve identity and role:** Apply ER rules in entities.json. Record the direct entity and propagated parents separately. Resolve borrower, lender, sponsor, manager, fund, insurer and adviser/arranger roles. Namesake exclusion removes a match, not necessarily the entire story: it may still qualify under B/C.
3. **ED03 — Relevance:** Establish A, B or C with an event-specific explanation. Merely mentioning a monitored GP, being a large deal or being macroeconomic is insufficient. A routine manager portfolio-company transaction with no material transmission fails here.
4. **ED04 — Event and novelty:** Identify what changed, affected vehicle/asset and period. Combine duplicates, preserve sources, distinguish an update from a new event. No new information → duplicate/repeat suppression.
5. **ED05 — Economic gates:** For normal selection require materiality ≥15, transmission ≥10 for A/B or ≥15 for C, source credibility ≥7 and novelty ≥2. Choose anchors from scoring.json. An unresolved judgement is review, not fabricated precision.
6. **ED06 — Score:** Compute the six-component total deterministically. Keep component evidence and explanations. A high total never reverses a failed relevance/evidence gate.
7. **ED07 — Select:** Apply score bands, then soft geographic diversification, then analyst review. Record model recommendation, analyst disposition and final publication separately.
8. **ED08 — Critical override:** Escalate verified material direct risk immediately for analyst review. The override rules below determine what can bypass normal ranking.
9. **ED09 — Draft:** Write concise factual English and a separate investment interpretation from the approved evidence packet; derive Chinese from that English. Validate both before publication.

Never discard a candidate solely because no tracked manager matched. Never use a word-level exclusion such as “PE”, “insurance” or “Guggenheim Securities” as an unconditional article veto. The exclusion must apply to the event's actual subject and role.

## A/B/C eligibility

| Level | Required connection | Typical qualifying case | Common failure |
|---|---|---|---|
| A — Direct exposure relevance | Resolved tracked manager/vehicle or its relevant business directly involved, with material strategy or firm-wide consequence | OTF results; Pretium-linked servicing stress; major KKR firm-wide fundraising | KKR mentioned as historical PE sponsor of a routine bolt-on |
| B — Direct market read-through | New evidence directly changes assessment of a monitored sector/strategy without a tracked GP | Comparable BDC credit-quality deterioration; material CLO financing spread change | One irrelevant peer headline generalized to all private credit |
| C — Alternatives context | New observed trigger plus specific causal path to alternatives financing, returns or exits | Policy change affecting floating-rate borrower coverage or property refinancing | “Rates matter to markets” without event-specific consequences |

Use one primary level. A does not automatically rank above B or C. A systemic credit event can outrank a modest manager announcement. Unknown identity can still support independently evidenced B/C relevance, but do not preserve the unresolved A tag or a holdings-based override.

## Manager-level policy

Usually consider material firm-wide fundraising, actual results, manager acquisitions/disposals, ownership changes, key-person changes, strategy/geographic expansion, regulatory actions and major capital/platform changes. “Usually consider” means evaluate, not publish every press release. Include a material non-credit manager event when franchise capacity, governance, fundraising or shared capital transmission is explicit.

Usually reject routine PE portfolio acquisitions, minor hires, awards, sponsorship, appearances, generic interviews, marketing and office openings without economic consequences. An exception requires evidence of financing changes, meaningful exposure, scale relative to the entity, or structural franchise consequences. Mere membership of the manager's portfolio is not such evidence.

Pretium platform stories can resolve to the parent but not automatically to every Pretium fund. OTF deterioration cannot be reported as a Blue Owl-wide portfolio loss. Guggenheim Securities advising a borrower does not prove Guggenheim Investments lent money. HSBC group actions need an AM channel. Bain Special Situations is not automatically a private-credit classification. GP-led secondaries are not automatically GP stakes.

## Scoring interpretation

Retain 30/25/20/10/10/5 initially so Phase 2 can test the analyst's proposed rubric instead of introducing untested weights. The key improvement is **gates before scores plus discrete anchors**. Config contains the exact allowed values.

| Component | Max | Distinct question | Avoid double-counting |
|---|---:|---|---|
| Direct Portfolio Fit | 30 | How close is the event to a verified monitored entity/strategy? | A manager name earns no points for economic magnitude. |
| Materiality | 25 | How substantial is the event relative to affected entity or market? | Strong transmission does not prove large impact. |
| Investment Transmission | 20 | How does the observed change reach an investment outcome? | Proximity is not mechanism; identify the actual path. |
| Investor Actionability | 10 | What specific metric, diligence issue or GP question changes? | Do not require a trade; avoid repeating the mechanism verbatim. |
| Source Credibility | 10 | How well does the evidence support the key factual claim? | Prestige and number of syndicated copies do not establish truth. |
| Novel Information | 5 | What was newly learned relative to the existing event? | Recency of an article alone is not novelty. |

Source credibility and novelty have two roles: minimum eligibility gates and limited ranking differentiation. They cannot compensate for irrelevant content. Scores describe editorial priority, not return forecasts or probabilities. Evaluate an ablation without the six-component total in Phase 2; if simpler anchored ranking performs as well, reduce the rubric after recorded review.

### Materiality and financial quantities

Use disclosed fund NAV/AUM, commitments, assets or relevant prior-period measures as denominators where available. Record the denominator's entity, period, currency and source. Never compare a borrower loan with a manager's unrelated global AUM without explanation. Never invent a denominator or use an old figure as current. If no reliable denominator exists, use an evidenced qualitative basis (loss of a licence, key-person clause, blocked redemptions, loss of a core funding channel) and explain uncertainty. Merely calling something “major” does not justify 20/25.

Differentiate announced vs closed, commitments vs funded deployment, enterprise value vs debt financing, gross vs net, equity raised vs leverage-inclusive capacity, NAV vs NAV/share, cost vs fair-value non-accrual percentages, percentage points vs percent, and asset vs liability spreads. A falling NAV/share can reflect distributions, not necessarily credit losses. NII/PIK are not interchangeable with cash collections. No inference of realized loss from a markdown alone.

### Bands, capacity and reserves

80–100: priority shortlist, normally publish after checks. 70–79: ordinary shortlist. 60–69: reserve, only if fewer than six ordinary eligible shortlisted events and analyst explicitly approves. Below 60: suppress unless a valid critical override is approved. All bands remain subject to evidence and relevance. Six to ten is a target; publish zero or three when appropriate. A thin day never lowers quality gates.

If more than ten ordinary qualified events exist, keep the highest priority and log the remainder as capacity exclusions. Never label a capacity exclusion as irrelevant. Preserve a compact event-level record so missed important events can be audited.

## Critical events and overrides

Examples: payment default/restructuring, enforcement, fund gate, major NAV impairment or key-person departure at a directly held manager/vehicle. These categories alone do not trigger publication; materiality and facts must be substantiated. A minor routine management change is not a critical departure.

For a confirmed-held entity, an analyst can override a low numerical band, disagreement about a materiality anchor, geographic preference or ten-card target. Record reviewer, timestamp, affected entity, source evidence, reason and normal decision. This is an explicit editorial judgement, not a model-selected bypass.

An override cannot bypass identity, source sufficiency, factual attribution, novelty or analyst review. Unverified allegations are not stated as findings. An investigation may itself be news if verified and accurately described. For unknown held status, escalate a tracked risk event for urgent review without claiming a holding; it can still publish through ordinary eligibility or an explicitly documented analyst decision once exposure is resolved. Preserve overflow when several critical events occur; do not sacrifice risk coverage to the daily card target.

## Sources and evidence

Preferred primary evidence: GP/borrower IR, public BDC filings, SEC EDGAR, central banks and relevant regulators (Fed, NAIC, ECB, BoE, FCA), plus accessible rating-agency research/presales. Ratings are the agency's analysis, not proof of future losses. GP announcements are reliable evidence of what the GP announced, not independent validation of promotional claims or investment performance.

Accessible reputable financial reporting and public specialist publications can support events, especially stress underrepresented in releases. A Business Wire/PR Newswire issuer release is issuer-origin evidence distributed by a wire; it is not independent journalistic corroboration. Classify origin and distribution separately. Public availability and evidence quality are separate dimensions.

Discovery through GDELT, RSS or search must retain the eventual evidence URL and originating publisher. Ten copies of one release are one origin, not ten confirmations. Full article access is not mandatory if an accessible primary record independently supports all material facts. If only a paywalled title/snippet is available, mark evidence incomplete and seek an accessible primary record; never extrapolate a detailed summary.

Resolve contradictions at claim level: preserve both values, dates and bases; an explicit official correction supersedes the old claim with history retained. Primary-source status does not automatically settle an unrelated allegation. Unresolved material contradictions block publication pending review.

## Events, duplicates and corrections

An article is a source; an event is what happened. Normalize URLs conservatively: drop known tracking parameters, retain meaningful query IDs, and record original and canonical URLs. Exact-content duplicates merge first. Then compare resolved parties, vehicle/asset/deal identity, primary event/subtype, reporting period and action dates. Similar headlines alone cannot merge stories. No embeddings are needed for the first small sample.

Same deal + same milestone across sources → one event, multiple sources. Same manager + different fund/borrower → different events. Announcement and closing can be two milestones of one event; publish an update only if it adds material information. A fresh story about last week's announcement without new facts is a repeat. A refinancing and reset require the correct subtype and deal identity.

Use persistent event IDs assigned once. Corrections and updates append revisions instead of silently overwriting prior decisions. An earnings event may contain NAV/NII/non-accrual facts in one card; split out a separate borrower default only when it is a distinct material event, cross-linking to avoid duplicate explanations. Peer trends require comparable data, not a claim that every private-credit portfolio behaves alike.

## Dates, geography and selection

Proposed MVP publication timezone: Asia/Hong_Kong. Preserve source timestamp/timezone, event date (nullable), first-seen UTC time, and editorial publication date independently. Assign dashboard date when approved for that day's edition. Do not backdate a newly discovered old article to manufacture history. Date navigation begins with actual retained editions, not automatically the developer's start date.

The future dashboard opens on today's date, displaying a clear empty/not-yet-reviewed state if no edition exists; it must not silently substitute yesterday's feed. About 90 days is a visible-history policy to implement later. Corrections need visible update labels. Weekend silence is permitted.

Geography is outside the intrinsic 100 points. Tag countries and primary **economic-impact** region, not newsroom location or manager headquarters. Europe includes the UK; use Global/Unknown when assigning a single region would be misleading. Multi-region context can carry multiple country tags but each event counts once in the selection denominator.

Provisional target: Europe about 20% of all unique published events over 30 calendar days, with US dominant. Use the exact counting and tie-break policy in scoring.json. Prefer Europe only among comparably scored eligible stories (same band, within five points) when below target; then prefer US when the target is met. Remaining tie order: higher materiality, stronger direct linkage, earlier first-seen timestamp, stable event ID. Never alter the stored intrinsic score. Report available eligible European supply and selected share separately; lack of supply is not permission to pad the feed. Material APAC/other direct events may qualify.

## Summary and “Why it matters”

English headline plus factual summary: usually 2–3 sentences, about 45–90 words. State what changed, who acted, relevant instrument/vehicle, amount basis and dates. Omit unknown facts. Every substantive fact and number must map to an evidence claim/span. Attribute forecasts, allegations and issuer assertions. Source links must be usable and point to the underlying evidence.

Interpretation: 1–2 sentences, about 20–45 words. Structure: **observed event → specific possible investment consequence → useful monitoring point**. Label inference with “may”, “could” or an explicit condition when appropriate. Do not add unsupported loss estimates, suggest an investment action without mandate context, or imply actual portfolio exposure. Avoid generic phrases such as “underscores strong momentum.” Include countervailing channels when their omission would mislead (higher base rates can raise lender income and borrower stress).

Chinese: translate the approved English meaning, including headline, summary, interpretation and visible tag labels. Keep canonical IDs and official entity/fund names stable; use a controlled term glossary. Proposed first locale is Simplified Chinese (`zh-Hans`), reversible without architecture change. Preserve figures, currency, units, source attribution, uncertainty and tense. No stronger claims or extra facts in Chinese. Use English as canonical; a failed Chinese check leaves the edition in review, not falsely marked bilingual-ready.

## Examples: paired decisions

| Hypothetical event | Decision | Why |
|---|---|---|
| KKR-backed company acquires a small competitor; only equity sponsorship is disclosed | Reject | Routine PE bolt-on; no financing/material franchise transmission. |
| Same transaction includes a documented material debt restructuring affecting a monitored credit strategy | Include candidate A | The new credit fact changes risk; identify actual lender and scope. |
| Fed speaker repeats known policy view | Reject | No new trigger; generic macro channel does not rescue it. |
| New policy decision changes floating-rate financing conditions; evidence establishes borrower coverage sensitivity | Include candidate C | Event-specific mechanism; no claim every loan reprices immediately. |
| OTF quarterly disclosure shows a material portfolio-quality change | Include candidate A | Vehicle-specific evidence; preserve OTF and Blue Owl tags without sharing losses. |
| Page describes OTF font rendering | Reject match | Wrong entity; no independent alternatives relevance. |
| NB Strategic Capital II announces a material continuation transaction | Include candidate A | Secondaries/liquidity channel, not GP stakes. |
| Guggenheim Securities advises routine unrelated corporate acquisition | Reject A | Arranger/adviser role is not investment exposure. |
| Material Pretium-platform mortgage-servicing failure | Include candidate A | Operating disruption can affect collections, advances and recoveries. |
| HSBC opens a retail bank branch | Reject | No AM/alternatives transmission. |
| Tracked manager wins an award on its official website | Reject | Correct identity and primary source cannot rescue immaterial marketing. |
| Material PAG credit fund event outside US/Europe | Include candidate A | Assess direct relevance first; geography is a later preference. |

“Include candidate” means eligible for scoring/review, not guaranteed publication. Machine-readable hypothetical examples with expected bands are in examples/editorial-cases.json. Actual readiness requires the real-article experiment.

## Changes and analyst feedback

Version ontology, scoring, prompt and model identifiers on every decision. Preserve original recommendation, final label, changed components, reviewer, timestamp and reason codes. Record false positives, false negatives, capacity exclusions, inaccessible evidence and discovery misses separately. Do not overwrite labels to make accuracy look better. See phase-2-experiment.md for the experiment and decision-record.md for the minimum audit contract.
