# Friday extension checklist

Plan: [plan.md](plan.md). Detailed design: [deduplication and ranking](../docs/deduplication-ranking-design.md). Status: pipeline, UI and approved EN/ZH reports deployed on 24 September; [release evidence](../docs/release-2026-09-24.md). Preserve all existing features and UI controls.

- [ ] 1. Public GitHub PDF publication is authorized. Establish Chinese locale, chart translation scope and remaining paid-call budget; analyst orders 12–15 distinct examples. Freeze ranking contract. (1.5–2 technical hours)
- [x] 2a. Codex: lossless eight-pair event projection, conservative validated-identity grouping, revision retention, evidence-linked priority rules and regression tests implemented. 182 source cards -> 174 events; source daily files unchanged.
- [ ] 2b. Independent semantic review, recovery of underlying evidence for broader historical grouping/priority backfill, and analyst ordering acceptance remain. Legacy events are Needs review. A post-release automatic refresh succeeded, but live ranking accuracy has not been accepted; all 193 current events remain Needs review.
- [x] 3. All-dates global list, intersecting filters, Priority/Newest and partial-load states implemented and browser-tested. Release review also covers omitted-member stale-index fallback.
- [x] 4. Public EN/ZH PDF viewing/open/download implemented; English v2 and analyst-approved Simplified Chinese v2 published. Chinese afternoon review may produce v3; v2 remains approved meanwhile. Publication evidence: ../docs/release-2026-09-24.md.
- [ ] 5. Integration and release complete: 397 tests and 14 subtests passed; live assets and archive verified, rollback documented. Still open: native desktop PDF embedding check (only in-app browser connected), analyst separate 20-event acceptance, and live evidence-backed ranking validation.

Checkpoints: contract before ranking; data/UI review before integration; PDF content/layout and all existing UI features verified before release. Existing baseline FAIL remains recorded. No full recalibration or authentication platform within Friday base scope. No source records deleted during grouping.
