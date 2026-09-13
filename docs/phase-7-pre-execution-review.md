# Phase 7 pre-execution review — 2026-09-13

Reviewed local `main` at `89b5da8`. No classifier inference, evaluator-label access, prompt repair, provider change, or spending authorization occurred. Production code and frozen artifacts were not changed. Audit outputs are private under `work/phase2/phase7-preflight/`.

## Decision 1 — SEND BACK WITH SPECIFIC FIX

The observed evidence shapes do not justify redesigning p2/rc4. However, the execution path is not ready for a reproducible, fully accounted historical comparison. Tickets below are pre-execution requirements, not permission to implement or run the experiment in this review.

### Frozen counts and scope conflict

| Scope | Article inputs | Exact overlap with included natural partitions | Unique additional inputs |
|---|---:|---:|---:|
| Natural calibration | 188 | — | 188 |
| Historical holdout | 56 | 0 with calibration | 56 |
| Actual frozen challenge partition | 30 | 0 | 30 |
| Broader challenge registry, alternative scope only | 91 | 59 | 32 |

The immutable split therefore specifies **274 unique classifier inputs**, not 78 natural inputs plus 91 challenge calls. Its cutoff is 2026-09-04; calibration/holdout are disjoint, with zero recorded split date exceptions and zero quarantined cross-cutoff lineages. The source collection contains 245 natural records; only 244 entered the split.

There are two upstream packet exclusions, not listed again in the split's empty date-exceptions list:

- `f6400cea-3e84-5bd7-b063-5a3aa338d076`, dated 2026-09-02: excluded because the same canonical article was already labeled in the starter packet; the packet records that another label would not be independent. This is the missing natural record.
- `e0f8d0fc-e619-5649-85cb-950a8c028ce9`: independently curated challenge record with unknown publication date, excluded from the packet.

The registry's 60 linked natural probes include that excluded natural article. Thus only **59** match the included calibration/holdout inputs. The 31 independent registry records include the undated exclusion, leaving the frozen challenge partition's 30. Running all 91 registered probes would involve 276 unique inputs across stages, including both exclusions. That is not the frozen 274-input experiment and must not happen silently.

Recommendation: retain 188/56/30 as the frozen historical comparison. If a separate linked diagnostic report is wanted, explicitly freeze its 59 included article IDs as a supplementary replay-only cohort; preserve both exclusions. Do not label a 30-article result as a 91-probe result. The handover's requested Stage D scope must be reconciled in the execution record before Stage A.

Hashes were independently recomputed: frozen evidence JSONL and split match freeze-record.json; all 275 available bodies match their recorded hashes using the repository's `evidence_capture.digest` normalization. No missing hashed body. All three smoke manifests' article-ID hashes verify: preserved v1 has 11 articles, v2 has 9, current v3 has 9. Smoke manifest versions and live-run versions are separate identifiers.

### Metadata/input-shape audit

| Shape | Calibration | Holdout | Frozen challenge | Current smoke |
|---|---:|---:|---:|---:|
| Accessible / partial / unavailable | 102 / 86 / 0 | 29 / 27 / 0 | 26 / 4 / 0 | 6 / 3 / 0 |
| Primary excerpt / metadata only | 187 / 1 | 56 / 0 | 30 / 0 | 9 / 0 |
| Body present / absent | 187 / 1 | 56 / 0 | 30 / 0 | 9 / 0 |
| Body characters: min / median / p95 / max | 0 / 470.5 / 800 / 800 | 283 / 466 / 800 / 800 | 215 / 585 / 800 / 800 | 294 / 507 / 799 / 799 |
| Multiple tracked entity matches | 9 | 2 | 3 | 3 |
| Maximum tracked matches | 2 | 2 | 3 | 2 |
| Maximum serialized message UTF-8 bytes | 34,317 | 34,292 | 34,257 | 34,265 |

Matches use the existing deterministic alias/ticker matcher on title plus body; they are candidate mentions, not inferred involvement or semantic entity-resolution results. The entity-matches list can structurally represent three or more entries. Optional body and null/unscorable fields structurally support metadata-only evidence; the prompt's unknown-evidence instruction applies. Evidence sufficiency remains a model judgment and must be measured, not assumed to pass from source reputation.

No full-text records occur. The larger partitions add a metadata-only candidate and a three-entity candidate beyond live smoke coverage; 800 versus 799 maximum excerpt characters is not a context-limit concern. Current official model context is 1M tokens. Messages are approximately 33.3–34.3k characters including the provider system message, comfortably below that even using a deliberately loose UTF-8-size proxy plus the 16,384-token output cap. This is not an exact tokenizer measurement.

No source-language metadata exists. A Unicode scan found no CJK characters in any title/body; that does not prove all sources are English or validate multilingual performance. Source language remains unmeasured rather than an invented detected-language distribution.

Publisher distribution:

- Calibration: Alternative Credit Investor 81; Commercial Observer 63; KKR 10; HSBC Asset Management 9; Blue Owl Capital 4; Blue Owl Technology Finance Corp. 3; BLUE OWL CAPITAL INC. 3; Apollo Global Management 3; Bain Capital 3; KKR & Co. Inc. 2; Apollo Global Management, Inc. 2; CIFC 2; Guggenheim Investments 1; BasePoint Group Inc. 1; PAG 1.
- Holdout: Alternative Credit Investor 28; Commercial Observer 20; HSBC Asset Management 4; Blue Owl Technology Finance Corp. 2; Pretium 1; Apollo Global Management 1.
- Frozen challenge: Commercial Observer 13; HSBC Asset Management 6; KKR 4; Apollo Global Management 3; U.S. Securities and Exchange Commission 3; Blue Owl Capital 1.
- Smoke: Alternative Credit Investor 3; Apollo Global Management 2; KKR 2; Commercial Observer 1; Blue Owl Technology Finance Corp. 1.

There are zero exact canonical-URL duplicate groups, zero exact recorded-body-hash duplicate groups and zero explicit supersedes links within each audited partition, including smoke. The smoke log's merged pair is therefore not evidence of an exact URL/body duplicate; semantic grouping can still merge it. No evaluator event IDs were used to discover additional event/update groups. Pairwise grouping reaches 17,578 pairs for calibration versus 36 for smoke, a small computational workload but materially more opportunities for semantic ambiguity. False merges/splits remain measured outcomes, not pre-cleared accuracy.

### Scoped Codex tickets

**P7-1 — Freeze the actual Stage D scope.** Failure: the handover describes 91 challenge probes, but the immutable split lists 30 and excludes two source records before partitioning. Change: record the 188/56/30 governing membership and explicit exclusions; optionally add a separately named, hashed 59-input linked replay diagnostic manifest without changing freeze-001. Verify exact IDs, counts, disjointness/overlap, and prompt-input hashes, using only ID projections of the registry. Synthetic test: overlapping cohort IDs replay once, excluded IDs cannot enter the frozen comparison, and same article with different settings cannot replay. Prompt/schema change: no. New live smoke: no.

**P7-2 — Freeze effective requests and preserve provider outcomes.** Failure: `DeepSeekProvider` has no thinking/effort controls; canonical settings omit thinking; runner's provider kwargs and settings can diverge; the provider system message is outside `input_hash`; provider model/version, finish reason and complete usage are discarded. Change only provider/runner/classifier provenance boundaries: one validated configuration supplies both request and hash, with enabled thinking, high effort, top_p=1, 16,384 output tokens, JSON object mode, system-message hash, timeout and bounded retry policy. Preserve returned model identifier/fingerprint when exposed, response ID, finish reason and original usage per attempt. Snapshot code commit, prompt/rc4/config hashes and verified split/body hashes before calls; verify the bodies actually loaded, not only their JSONL references. Ensure config loaded is the config hashed. Do not fabricate a pin-able snapshot if the API exposes only a moving alias. Synthetic tests: capture exact HTTP request; each operative setting/system-message change changes request identity; request/manifest agree; tampered split/body is rejected before provider access; finish_reason=length and missing model metadata remain explicit. Prompt/schema change: no; settings/run identity changes. New live smoke: not required solely to make today's documented defaults explicit after synthetic contract tests; model/version change would require its own authorized smoke.

**P7-3 — Account before grouping, replay without new billing, and stop at the cap.** Failure: `runner.build_decision` keeps only the primary member's model_metadata, while `run_experiment` totals those event rows and looks for attempts that are absent there. Synthetic two-member example billed 200 input/40 output tokens but retained 100/20; attempts were absent. RawOutputStore does not preserve usage, and replay returns only raw text, so provenance/accounting cannot be reconstructed from it. Change: append an article/attempt ledger before grouping, with raw-response reference, usage, latency, status and request identity; aggregate calls from that ledger, not event representatives. Retain historical usage separately from incremental replay cost (zero); use one pinned response/attempt lineage for exact-hash hits, including terminal invalid outcomes, with no paid fallback on a cache hit. Run only missing hashes through paid inference; regroup the whole challenge cohort afterward. Add bounded spend reservation/checkpointing before every dispatch/retry, accounting conservatively for timed-out requests whose billing is unknown; never treat unknown usage as zero. Test: merged articles retain all usage/failures; schema retries are counted; replay adds zero paid calls and preserves source usage; exhausted budget prevents the next request; restart does not rebill completed hashes. Prompt/schema change: no. New live smoke: no; synthetic integration tests suffice.

**P7-4 — Prevent null/non-text response content from aborting the batch.** Failure: provider content=None reaches json.loads; run_attempts catches JSONDecodeError but not TypeError. Synthetic null and integer content both raised uncaught TypeError. A failure late in calibration loses the in-memory proposal set even though previous calls were billed. Change: preserve the response and classify absent/non-text content as an explicit bounded operational failure, with a review-required candidate after exhaustion; do not abort remaining candidates. Keep transport failure distinct from invalid/missing content. Synthetic tests: null, number, empty and truncated content; valid next article still completes; all attempts/usage persist. Prompt/schema change: no. New live smoke: no.

These tickets do not reopen the closed economic-role, ontology-ancestry or A/B/C decisions. Structurally complete but semantically weak reasoning remains the accepted review limitation. Do not tune it away before evaluation.

## Decision 2 — ONE_REPAIR_ALLOWED

This Phase 7 decision governs, adopting Phase 6 completion's explicit independent Phase 7 allowance. Phase 5's log remains authoritative for the exhausted nine-article smoke experiment; its broad future-run wording does not govern the separately disclosed full-population calibration stage. This is an explicit policy supersession for Phase 7, not a claim that the documents already agreed.

One repair is available only after the entire initial 188-article calibration prediction set is preserved and frozen, then evaluated. It requires either the same demonstrated specification defect across at least two distinct source-described events (duplicates count once), or an article-independent structural counterexample showing a valid rulebook output cannot be represented/interpreted/processed.

Only omitted, contradictory or ambiguous instructions, incomplete contracts, schema defects or otherwise demonstrated specification failures qualify. Ordinary false positives/negatives, wrong anchors, borderline A/B/C calls, stochastic differences, factual/model-reasoning errors against clear instructions, metric-driven improvements and article-specific exceptions do not qualify, however frequent.

If used, preserve originals; identify affected calibration cases and public rulebook authority; document specification-versus-model diagnosis; make one minimal generic change; increment affected prompt/schema versions; add synthetic regressions; rerun all 188 unchanged calibration inputs under a new run identity; use that repaired version regardless of headline accuracy; freeze final configuration before any holdout generation. Never pool pre/post-repair predictions. No second repair; no repair after holdout outputs have been generated OR inspected; challenge outcomes cannot trigger one. An unsuccessful structural repair stops with `historical_model_comparison = inconclusive_structural_failure`. If unused, record `phase7_calibration_prompt_repair = not_used`.

Provider/settings and operational fixes above are not prompt repairs. They must be completed before Stage A. A subsequent settings change requires a new configuration/run and a complete comparable calibration result; it is not permission for unlimited retries or tuning. No configuration change after holdout starts.

## Decision 3 — Provider/settings/budget

Retain **DeepSeek / deepseek-flash**. Official documentation checked 2026-09-13 identifies its served version as **DeepSeek-V4.1-Flash**; the old Flash aliases route to this version rather than pinning old weights. This preserves the requested provider/model continuity, but historical smoke artifacts do not independently prove the served weight revision because the adapter dropped that metadata.

Recommended explicit configuration: `thinking={"type":"enabled"}`, `reasoning_effort="high"`, `top_p=1.0`, `max_output_tokens=16384`, `response_format={"type":"json_object"}`. Omit temperature: it has no effect in thinking mode. **top_p does have an effect**, defaults to 1, and values below 0.95 are raised to 0.95. Do not copy the handover's conditional suggestion that both controls might be ignored. Record omitted/default parameters separately from operative settings. These are recommendations awaiting implemented request/hash verification, not a claim that the configuration is already frozen.

Sources: [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/), [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/), [Models and Pricing](https://api-docs.deepseek.com/quick_start/pricing/).

### Planning estimate, not a bill

Current USD/million-token rates are input cache miss $0.30 peak / $0.15 off-peak; output $1.20 peak / $0.60 off-peak. No cache-hit discount assumed. Peak windows are weekdays 01:00–04:00 and 06:00–10:00 UTC (Hong Kong 09:00–12:00 and 14:00–18:00); all other hours are off-peak. Recheck the rate card at authorization/execution.

The supplied v3 baseline is 90,686 input and 65,324 output tokens / 9 articles: 10,076.22 input and 7,258.22 output per article. The accounting defect means those saved run totals cannot be certified as complete marginal provider usage. Use them only provisionally, with explicit headroom; do not recalculate a supposed actual bill from the discarded usage.

Actual serialized message totals are 6,372,767 calibration characters, 1,898,159 holdout characters, 1,019,723 frozen-challenge characters, versus 305,338 for smoke. Source-length differences are tiny relative to the common prompt. Cheap message-size scaling against smoke yields approximately the same 2.76M input-token proxy as article-count scaling; no exact DeepSeek tokenizer was run. Output length and retry frequency remain uncertain.

| Scenario | Article-config evaluations before retries | Estimated input / output tokens | Peak USD | Off-peak USD |
|---|---:|---:|---:|---:|
| Initial calibration | 188 | 1.894M / 1.365M | 2.21 | 1.10 |
| Historical holdout | 56 | 0.564M / 0.406M | 0.66 | 0.33 |
| Frozen challenge | 30 | 0.302M / 0.218M | 0.35 | 0.18 |
| All frozen stages, no repair | 274 | 2.761M / 1.989M | 3.21 | 1.61 |
| All frozen stages + full calibration repair rerun | 462 | 4.655M / 3.353M | 5.42 | 2.71 |
| Same, 50% planning headroom | — | — | 8.13 | 4.07 |

For the unapproved all-91-registry alternative, 59 would replay and 32 need calls, giving 276 unique inputs and 464 article-config evaluations with a calibration rerun: $3.24 without repair / $5.44 with repair, or $8.17 including 50% headroom. This is a scope illustration, not permission to restore excluded inputs.

Recommend a **US$25 hard authorization cap**, not an authorization. This includes initial calibration, one possible full repaired calibration, holdout and only missing challenge inputs. As a stress calculation, two schema attempts for every one of the 462 evaluations, each reaching 16,384 output tokens, plus the provisional input baseline, costs about $20.96 at peak/cache-miss rates. $25 gives further limited headroom. It is not a mathematical ceiling on uncontrolled transport retries or unknown billing; P7-3 must stop dispatches conservatively at the cap. If losses/retries exhaust it, stop incomplete and report; never silently top up. No drafting or unlimited tuning included. The old Phase 5 cap is not transferable authorization.

## Verification and dispositions

Private evidence: `input-audit.json`, `synthetic-findings.json`, `test-suite.log` under `work/phase2/phase7-preflight/`. Source evidence was used only for input assembly, sizes, hashes and lexical metadata checks. Registry categories/reasons were not inference inputs. Evaluator label files were not opened. Existing unittest fixtures are synthetic.

346 existing tests ran: 0 assertion failures, 4 errors, all Windows PermissionError during temporary-directory cleanup in two review-packet and two smoke-manifest tests. Thus **full suite not green in this environment**; 342 tests completed without error. The spec validator returned zero errors. The separate synthetic defect reproductions are affirmative failures of the current implementation, not regression tests passing a patch. No production patch was made.

After ticket implementation, require targeted synthetic regressions and the full suite in a functioning temporary-directory environment; preserve/report any remaining environmental failure rather than weakening tests. No browser retest is needed for this read-only classifier preflight.

Execution sequence remains: complete/freeze calibration predictions before evaluator join; adjudicate the one repair; freeze final code/prompt/contract/config/provider/settings; run holdout once and freeze predictions before evaluator join; run/replay the approved separate challenge scope; no challenge-driven tuning. Reports must separately include article/event/selected counts, precision, recall, must-not-miss coverage, false merges/splits, review rate, schema-invalid and transport outcomes, all-call usage/latency and calculated cost with its rate basis. Undefined precision or incomplete evidence cannot pass.

Historical bars remain precision >=90%, recall >=85%, must-not-miss 100%. Report meets_bars / fails_bars / inconclusive, with the structural-failure disposition above when applicable. `historical_model_comparison = not_run` today. `automated_selection_readiness = inconclusive_pending_fresh_temporal_validation` regardless of historical performance. Challenge remains diagnostic. No fresh temporal corpus or historical drafting is authorized here.

## Gate

PRE-EXECUTION GATE: BLOCKED

Blocking items: P7-1 Stage D membership reconciliation; P7-2 effective request/provenance freeze; P7-3 complete per-call accounting, replay and cap enforcement; P7-4 null-content containment; successful required regression verification after fixes; explicit user spending-cap approval.

Next Codex action: implement and synthetically verify P7-1 through P7-4, then present the exact frozen run configuration and US$25 cap for user approval before any billed call.
