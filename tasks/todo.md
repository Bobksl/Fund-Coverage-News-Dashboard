# Friday extension checklist

Plan: [plan.md](plan.md). Detailed design: [deduplication and ranking](../docs/deduplication-ranking-design.md). Status: design accepted; offline pipeline implemented, UI/report work handed over in [Claude prompt](../docs/handover-claude-dashboard-extension.md). Preserve all existing features and UI controls.

- [ ] 1. Public GitHub PDF publication is authorized. Establish Chinese locale, chart translation scope and remaining paid-call budget; analyst orders 12–15 distinct examples. Freeze ranking contract. (1.5–2 technical hours)
- [x] 2a. Codex: lossless eight-pair event projection, conservative validated-identity grouping, revision retention, evidence-linked priority rules and regression tests implemented. 182 source cards -> 174 events; source daily files unchanged.
- [ ] 2b. Independent review, recovery of underlying evidence for broader historical grouping/priority backfill, and analyst ordering acceptance remain. Legacy events are Needs review; live brief-v2-priority has not been exercised.
- [ ] 3. Claude implements all-dates global list, intersecting filters, Priority/Newest and partial-load states against agreed contract. (2–3 hours)
- [ ] 4. Analyst reviews Chinese translation; Claude adds public EN/ZH PDF viewing/open/download in the existing repository and checks PDFs. (3–5 technical hours; 4–7 analyst hours)
- [ ] 5. Codex runs integration/browser/refresh checks; analyst checks separate 20-event set; release only reviewed behavior with rollback. (2–3 technical hours)

Checkpoints: contract before ranking; data/UI review before integration; PDF content/layout and all existing UI features verified before release. Existing baseline FAIL remains recorded. No full recalibration or authentication platform within Friday base scope. No source records deleted during grouping.
