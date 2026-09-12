# Phase 2 engineering — local pipeline implementation

Date: 2026-09-11. Scope: the implementation tickets in [phase-2-experiment.md](phase-2-experiment.md).

**Engineering status and empirical status are separate.** The local baseline, structured-classifier
adapter, decision validation, predicted grouping, deterministic scoring/ranking, saved-output
replay, evaluator, corpus tooling, shortlist-only bilingual drafting and the calibration stability
harness now exist and are tested on synthetic fixtures. Every implementation ticket in the
experiment plan is now built. No benchmark
inference has run, no holdout exists and no performance is claimed. Phase 2 remains incomplete and
the [Phase 3 gate](phase-3-entry-gate.md) stays closed.

## Modules

| Module | Responsibility |
|---|---|
| [tools/records.py](../tools/records.py) | Evidence and decision contract from [decision-record.md](decision-record.md): field/enum validation, the inference allowlist, recursive leakage scan, byte-exact atomic JSONL. |
| [tools/baseline.py](../tools/baseline.py) | Deterministic comparison floor: config-driven entity resolution with the ER01–ER08 safeguards, event-phrase typing, sector lexicon, transparent anchor rules. |
| [tools/classifier.py](../tools/classifier.py) | Structured-classifier adapter: prompt assembly from allowlisted evidence, bounded retries, preserved raw outputs, replay provider. The provider is injected; the module performs no network access. |
| [tools/grouping.py](../tools/grouping.py) | Predicted event clustering from pipeline output only. Conservative: ambiguous identity stays split and flagged. |
| [tools/scoring.py](../tools/scoring.py) | Gates, anchor summation, publication bands, ranking, the ranking ablation and daily edition selection. |
| [tools/runner.py](../tools/runner.py) | Orchestration, decision assembly, contract validation, frozen predictions, article-only review CSV, run report. |
| [tools/evaluator.py](../tools/evaluator.py) | The only module that reads analyst labels. Freeze enforcement, one-to-one event matching, per-cohort metrics, no pooling. |
| [tools/corpus.py](../tools/corpus.py) | Cohort registry, blinded review packet, temporal split with lineage isolation, holdout sufficiency, freeze record. |
| [tools/drafting.py](../tools/drafting.py) | Shortlist-only bilingual card drafting with grounding, cross-language quantity/currency/party/uncertainty parity and defect reporting. |
| [tools/stability.py](../tools/stability.py) | Calibration-only repeated-run stability: inclusion, band and entity variation, with unstable cases routed to review. |

## Boundaries the code enforces

- `to_inference_input` projects evidence onto an allowlist and raises if an evaluator-only key
  survives at any nesting depth. The runner refuses a manifest carrying gold metadata.
- The pipeline receives article IDs and a partition name. It proposes its own event groups.
- Python sums every total, selects the band and sets ranking. A model supplies anchors and reasons.
  Model-supplied totals or publication statuses are discarded.
- An unconfigured anchor, an unknown enum, unparsable output or a transport failure becomes
  `review_required` with the raw output preserved — never a zero-score rejection.
- `publication.status` cannot be `approved`, `published` or `corrected` without a recorded
  analyst review.
- `held_status` is exactly `monitored`.
- Date-only evidence keeps its date and never acquires a midnight timestamp; month/unknown
  precision records are excluded from the headline split and disclosed.
- The evaluator raises `FreezeError` unless label, evidence, split and prediction hashes are
  recorded, and again if the predictions file changed after the freeze.
- Drafting runs only for shortlisted events and refuses anything else. A card with an unsupported
  figure, a quantity that changes across languages, a dropped party or dropped uncertainty becomes
  `review_required` and cannot be published.
- Stability reruns refuse any partition whose name is not calibration, so a stability pass cannot
  become extra holdout inference.
- Token counts, latency and cost basis are recorded from what the provider actually reported. No
  price is ever invented; `cost_basis` stays null until a real rate card is recorded.
- Cohorts are reported separately. `evaluator.report` exposes `pooled_metrics: None` and never
  emits a pass; disposition is `pending_human_disposition`.

## How to run it

From the repository root, with Python 3.13. Keep all inputs and outputs under ignored `work/`.

```bash
python -m tools.runner work/phase2/demo/manifest.json work/phase2/demo/evidence.jsonl work/phase2/demo/out
```

Replay a recorded classifier run from saved raw outputs instead of the baseline:

```bash
python -m tools.runner work/phase2/demo/manifest.json work/phase2/demo/evidence.jsonl work/phase2/demo/replay --engine replay --raw-store work/phase2/demo/raw --model <exact-snapshot> --prompt-version <version>
```

Custodian commands, which read gold data and never feed the pipeline:

```bash
python -m tools.corpus packet <evidence.jsonl> <destination>
python -m tools.corpus split <evidence.jsonl> <cutoff-date> <output.json> --gold-groups <groups.json>
python -m tools.corpus freeze <labels.csv> <evidence.jsonl> <split.json> <freeze.json> --predictions <predictions.jsonl> --frozen-at <iso-instant>
python -m tools.evaluator <predictions.jsonl> <labels.csv> <freeze.json> <result.json> --cohort natural_feed --split holdout
```

The evaluator command structurally audits the label sheet first and refuses to compute a metric on
an invalid one. Live inference has no command-line path on purpose: a provider must be injected in
code, and the label/evidence freeze must exist first. Outputs are `predictions.jsonl`, `review.csv`,
`run-report.json` and `predictions-sha256.txt`. The runner refuses to overwrite an existing
prediction set.

A synthetic six-article demo run produced five predicted events (one duplicate collapsed), three
selected, one `review_required` for a bare-namesake match, one suppressed, zero invalid decisions
and zero silent drops. Those are fixture mechanics, not editorial performance.

## Bilingual QA coverage and its limits

Automated card checks cover claim references, unsupported figures, cross-language quantity parity
(7.3 billion and 73亿 normalize to the same value), currency parity, party retention and dropped or
added uncertainty. Prose quality, tone and the factual correctness of an interpretation still need
human review, and the unsupported-figure check reads years and ordinals too, so claims must carry
their period. No card is published without analyst approval.

## Deliberate baseline limits

These are the floor's known weaknesses, recorded rather than tuned away, because the point of the
baseline is to show what semantic reasoning must add:

- Event typing is a whole-token phrase lexicon checked in a fixed order, so "closes the acquisition"
  types as capital formation before corporate transaction.
- Config `excluded_contexts` are matched literally, so descriptive entries ("property/street
  names") never fire.
- Themes carry prose trigger conditions the baseline cannot evaluate, and one tagged sector links
  many themes. The baseline therefore assigns no theme and reports
  `unassigned_theme_candidates` instead.
- Region is always `Unknown`: the baseline never infers geography from a publisher domain or a
  manager's headquarters.
- Generic macro reaches Level C with a low transmission anchor and fails the Level C threshold by
  design, so justified macro stories are a known recall gap for the structured pipeline to close.

## What this does not establish

Synthetic fixtures prove wiring, boundaries and arithmetic. They say nothing about precision,
recall, clustering quality, identity accuracy, bilingual grounding, analyst usefulness, cost or
latency on real articles. Identity and role correctness is not scored automatically: the evaluator
emits a worksheet marked `pending_human_review` because analyst roles are free text.

## Exact next analyst input required

In dependency order. The first three unblock a calibration freeze; the fourth unblocks a holdout.

1. Resolve the two open calibration disagreements recorded in
   [phase-2-batch-review.md](phase-2-batch-review.md): the relevance-level taxonomy reading and the
   reserve/materiality rubric. Resolve on calibration records only.
2. Supply independent second-reviewer labels covering all critical cases, the borderline cases and
   a random subset — or, if only one analyst is available, a shuffled relabel after a gap, with the
   weaker independence disclosed.
3. Capture the permitted evidence payload for the 20 starter articles (text or excerpt, retrieval
   time, access status, hash) so labels and evidence can be frozen together. A link packet hash
   does not freeze article content.
4. Approve or amend the [natural-feed collection policy](natural-feed-policy.md), which is drafted
   and waiting: confirm the roster's newsroom paths, name the independent public outlets, decide
   whether PAG is in scope given its blocked site access, and decide how HSBC AM's UK pages count
   regionally. Then collect under it, with challenge curation kept separate, until each evaluable
   cohort holds at least 20 distinct analyst-publish-worthy events. Do not top up a natural feed
   with challenge positives and do not resize a cohort after seeing model results.

Only after 1–4 may a provider be injected and a frozen run evaluated. Benchmark inference must run
in a fresh context with no access to labels, rationales, gold groups or challenge categories; the
code enforces that on the input side regardless of who or what runs it.
