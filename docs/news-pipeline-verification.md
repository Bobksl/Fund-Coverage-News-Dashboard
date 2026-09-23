# Pipeline implementation verification — 23 September 2026

Branch: codex/news-events-priority. Pipeline commit: debaea9. Base: origin/main b0edb36. UI/report handover: docs/handover-claude-dashboard-extension.md. Local commits only; no push/deployment.

## Implemented and verified
- Lossless events.json projection over existing date files. Eight hash-frozen duplicate groups reduce 182 source cards to 174 event records. Six pairs are same-day, two span different dates. The per-day data and existing UI files are unchanged.
- All event member IDs form a complete, disjoint partition of source card IDs. Sources retain links and dates. Rebuilding with the same as_of and prior index preserves identity/order. Mapping invalidates on source-card mutation.
- New source fingerprints permit repeat detection and retention of changed same-URL content as revisions, with compatible-event checks. Different-source coverage is retained rather than silently discarded by fuzzy headline filtering. Paid-call cap remains bounded by the existing refresh settings; retaining sources can increase call demand within that cap.
- Ordinal priority classification and stable tie-breakers, deadline expiry, missing/unsupported evidence -> Needs review, separate potential-risk flag, and evidence-span/hash validation. One structured brief call extended; no six-component score.
- Conservative near-duplicate grouping requires matching source-grounded subject/action/object/explicit period and numeric signatures. Generic same headlines, different amounts/periods and conflicting/unknown identities remain separate.
- OTF parent propagation and explicit Technology Income versus Technology Finance display guard. Existing historical raw tags are preserved; event display tags provide the correction.
- Corrupt prior event index recovers from preserved raw cards, recording a warning.
- Legacy date-only publication timestamps use an explicitly marked date-only HKT sorting fallback.

## Test evidence
Baseline before code changes: 361 passed, 14 subtests passed using python -m pytest -q outside the restricted Windows sandbox.
Final regression: 381 passed, 14 subtests passed (full suite). Focused lint uses python -m ruff check on all changed Python files. git diff --check passes.
Initial sandbox runs failed Windows temporary-directory permissions, including with a workspace-local TEMP; the same baseline passed outside the sandbox. No failing test was weakened to bypass that environment issue.
Tests were first observed failing for missing event/priority modules, source metadata, vehicle correction, changed-source retention, legacy dates, unrelated same-URL changes, display tags and corrupt-index recovery, then passed after implementation.
Synthetic end-to-end refresh proves evidence-linked assessment -> Urgent event priority; it is not live inference or calibrated editorial accuracy.
Tests use temporary directories/fake feeds/model responses, not repository public/data output.
Real snapshot projection was generated as an explicit build operation (not a test):
    python -m tools.news_events --data-dir public/data
Result: article_count=182, event_count=174.
cards_sha256=834269018333eb303dbb47a0cd736a543a6f4b5ae43e78a8f0097d17307be908

## Honest boundaries and remaining work
- Frontend is not yet wired to events.json, so the existing public UI still shows its old behavior until Claude integrates and the change is deployed.
- All legacy events are Needs review, because original source-backed priority metadata was not collected. No urgency/materiality labels fabricated from model-written summaries. The ranking engine is implemented; historical priority assessment is not complete.
- No paid DeepSeek call, token-price estimate, live prompt acceptance, full historical recalibration or user-ranked holdout evaluation was performed.
- Evidence-span validation establishes references to input text, not correctness of the model's interpretation. Current automatic feed evidence defaults to reported; primary strength requires separately verified metadata.
- Actual retained source text is not restored by a hash/offset. Historical source recovery and a reviewable evidence packet remain necessary for independent semantic validation.
- Google redirect resolution and broad historical near-duplicate reconciliation are not implemented. The eight explicit groups are handled now; other legacy near duplicates remain separate.
- Same-source revisions are visible, but text change alone does not advance last_material_update_at without material_update_confirmed metadata. This avoids claiming every wording change is material.
- Report conversion/Chinese review, real-browser UI verification and deployment belong to the Claude lane. Public PDF upload is already authorized.
- Existing tracked data/UI files remain unchanged. Untracked .claude/ was not modified.
