# Phase 7 frozen scope (P7-1) — 2026-09-13

This is the canonical statement of which articles Phase 7 classifies. It closes ticket P7-1 of
`docs/phase-7-pre-execution-review.md`. Where an earlier Phase 7-facing document says "57/21
articles" or "91 challenge probes", this document governs. Those documents carry a pointer here
and are otherwise left as written.

## Governing scope: 188 / 56 / 30 = 274 article inputs

The source is `work/phase2/freeze-001/split-manifest.json`, which is immutable and was not
modified. Its SHA-256 is `2a37ac10…23ea`, matching `freeze-record.json`, frozen
2026-09-12T10:13:04Z.

| Stage | Split-manifest field | Articles | Frozen run manifest | `article_ids_sha256` |
|---|---|---:|---|---|
| A — calibration | `natural_feed.calibration` | 188 | `stage-a-calibration.json` | `f92718b0…9963` |
| B/C — historical holdout | `natural_feed.holdout` | 56 | `stage-bc-holdout.json` | `fb094f88…f960` |
| D — challenge diagnostics | `challenge.article_ids` | 30 | `stage-d-challenge.json` | `033c5b4c…21a6` |
| **Total unique classifier inputs** | | **274** | | |

- The three lists are pairwise disjoint and contain no duplicates.
- Every ID has exactly one frozen evidence record.
- 273 body files were re-digested with `tools.evidence_capture.digest` and match their frozen
  `evidence_hash`. The remaining one is a metadata-only calibration record with no body and no
  hash.
- A repaired calibration rerun, if Decision 2's one repair is used, reruns the same Stage A
  manifest under a new run identity. It is not a new scope.

**Where the old numbers came from.**
- "57 calibration / 21 holdout" are the publish-worthy **event** counts in
  `docs/phase-2-disposition.md`, not article counts.
- "91 challenge probes" is the size of the broader, evaluator-only challenge registry. That
  registry is not the frozen scope (see the reconciliation below). Running all 91 is **not
  authorized**, and no tooling defaults to it.

## The two upstream exclusions

Both were removed from the analyst-review-003 packet before labeling, so neither is in any
freeze-001 list. The reasons below are from `work/phase2/analyst-review-003/packet-manifest.json`.

| Article | Registry role | Why excluded |
|---|---|---|
| `f6400cea-3e84-5bd7-b063-5a3aa338d076` (dated 2026-09-02) | linked natural-feed probe | Quarantined: the identical canonical article was already labeled in the starter batch as `45ac5e6b-6cc3-4134-8701-0f7323f35db3`, so a fresh label would not be independent (`work/phase2/natural-feed/starter-batch-overlaps.json`). This is the 245th natural record that never entered the 244-article split. |
| `e0f8d0fc-e619-5649-85cb-950a8c028ce9` | independent challenge probe | No established publication date. |

Both articles still have frozen evidence records; 276 evidence records = 274 + these 2. They are
recorded in `tools/phase7_scope.py:EXCLUDED_ARTICLES`. The builder refuses any partition that
contains one, and the run entry point refuses any scope manifest that contains one.

## Reconciling the 91-record registry, by ID projection only

Only `article_id` and `linked_natural_feed_article_id` were read from
`work/phase2/challenge/challenge-registry.jsonl`. No categories or selection reasons were read.

| Registry subset | Records | In the frozen scope | Excluded |
|---|---:|---:|---|
| Linked natural-feed probes | 60 | 59 (in calibration or holdout) | `f6400cea…` |
| Independent challenge probes | 31 | 30 (exactly `challenge.article_ids`) | `e0f8d0fc…` |
| Total | 91 | 89 | 2 |

This matches the audit's 60/31. The P7-1 handover's "59 linked / 32 independent" was a miscount
and carries a correction note. Running every registry probe would mean 276 unique inputs, which is
not the frozen 274-input experiment.

## Linked diagnostic: replay-only, never billed

`linked-diagnostic-replay-only.json` freezes the 59 included linked IDs, with
`article_ids_sha256` `1b14c84a…4ade`. It is a separately named view:

- It is marked `replay_only: true` and has no `partition`.
- It is never pooled into the 274-input comparison and never gets its own live run.
- `tools/run_model_experiment.py` refuses it without `--replay`, before any provider is built.
- With `--replay`, `ReplayProvider` reads saved outputs only and cannot fall back to a live call.
  A missing hash surfaces as `review_required`.

It adds no inputs: all 59 IDs are already Stage A or Stage B/C inputs. For its replay to hit, it
must read the raw store(s) that Stage A and Stage B/C wrote, under the identical final prompt,
model and settings. A replay under different settings cannot reuse an output; that is covered by
`tests/test_phase7_accounting.py::…::test_different_settings_do_not_replay_the_same_article`.

## Artifacts and how a run consumes them

All artifacts live in `work/phase2/phase7-scope/`, which is git-ignored. `scope-record.json`
records each file's SHA-256, the counts, the exclusions and the registry reconciliation.

| File | `file_sha256` |
|---|---|
| `stage-a-calibration.json` | `b6879b41…a837` |
| `stage-bc-holdout.json` | `7f4bd77c…a1d` |
| `stage-d-challenge.json` | `1947953f…78cc` |
| `linked-diagnostic-replay-only.json` | `bdb95266…87f6` |

The files were built with this command. It refuses to overwrite existing files:

```bash
python -m tools.phase7_scope work/phase2/freeze-001 work/phase2/phase7-scope --generated-at 2026-09-13T04:46:28+00:00 --evidence-store work/phase2/evidence-store --registry work/phase2/challenge/challenge-registry.jsonl
```

Each stage manifest is an object with `article_ids`, which is the shape
`tools/run_model_experiment.py` already accepts, e.g.
`run_model_experiment <run_id> calibration work/phase2/phase7-scope/stage-a-calibration.json …`.

Before any provider exists, `tools.phase7_scope.check_run_manifest` refuses a manifest that:

- has `article_ids` that no longer match its `article_ids_sha256`,
- is passed under a different partition name than the one it records,
- contains a recorded exclusion, or
- is replay-only but run without `--replay`.

This document authorizes no run. Provider settings and spending are governed by
`docs/phase-7-pre-execution-review.md` Decision 3 and the user's explicit cap approval.

**Prompt-input identity.** The frozen per-article inputs are the article ID plus its evidence
body. Each manifest's `evidence_hashes_sha256` pins `(article_id, evidence_hash)` for its members.
The per-article `input_hash` also covers model and settings, so it is recorded by each run's
article ledger (P7-2/P7-3). It cannot be frozen before the run configuration is.

## Verification

`tests/test_phase7_scope.py`:

- **Synthetic tests (always run):**
  - partitions must be disjoint;
  - exclusions are refused in every partition;
  - the ID hash ignores order and changes on any add or remove;
  - the diagnostic is a subset of the natural feed and is replay-only;
  - stray registry IDs are refused;
  - no evaluator-only key or registry text reaches any output;
  - tampered bodies are refused;
  - the live CLI refuses the diagnostic before building a provider;
  - tampered, mislabelled or exclusion-bearing manifests are refused;
  - overlapping linked IDs replay with zero new provider calls.
- **Real freeze-001 tests (skipped when `work/` is absent):**
  - 188/56/30 are disjoint, total 274, and contain no exclusion;
  - the registry reconciles to 60/59 and 31/30, with 276 as the all-probe alternative;
  - the written artifacts match a fresh rebuild byte-for-byte, with 273 bodies verified.
