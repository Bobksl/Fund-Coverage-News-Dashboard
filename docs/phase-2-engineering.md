# Phase 2 engineering — local pipeline implementation

Date: 2026-09-11. Scope: the implementation tickets in [phase-2-experiment.md](phase-2-experiment.md).

**Engineering status and empirical status are separate.** The local baseline, structured-classifier
adapter, decision validation, predicted grouping, deterministic scoring/ranking, saved-output
replay, evaluator and corpus tooling now exist and are tested on synthetic fixtures. No benchmark
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

Live inference has no command-line path on purpose: a provider must be injected in code, and the
label/evidence freeze must exist first. Outputs are `predictions.jsonl`, `review.csv`,
`run-report.json` and `predictions-sha256.txt`. The runner refuses to overwrite an existing
prediction set.

A synthetic six-article demo run produced five predicted events (one duplicate collapsed), three
selected, one `review_required` for a bare-namesake match, one suppressed, zero invalid decisions
and zero silent drops. Those are fixture mechanics, not editorial performance.

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
4. Expand the corpus under a predeclared natural-feed roster, consecutive window and completeness
   policy, with challenge curation kept separate, until each evaluable cohort holds at least 20
   distinct analyst-publish-worthy events. Do not top up a natural feed with challenge positives
   and do not resize a cohort after seeing model results.

Only after 1–4 may a provider be injected and a frozen run evaluated.
