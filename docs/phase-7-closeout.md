# Phase 7 closeout — demo scope

2026-09-13. The user explicitly replaced the full historical experiment with a
time-limited manager demonstration and Phase 8 planning. This decision supersedes
the requirement to execute 188/56/30 before closing Phase 7; it does not modify
the immutable scope manifests or imply that experiment was completed.

## Disposition

- phase7_status = closed_demo_scope_by_user_direction
- historical_model_comparison = not_run
- automated_selection_readiness = inconclusive_pending_fresh_temporal_validation
- reviewed_demo_ready = passed_for_exactly_one_card (Phase 6 evidence)
- phase7_calibration_prompt_repair = not_used
- additional_paid_calibration = not_required_for_existing_card_walkthrough
- spending_approval = not_granted; the prior USD 25 recommendation is not active authorization

The necessary minimum is mechanics verification, not another accuracy estimate.
The existing nine-article live smoke and one human-approved bilingual card support
this limited walkthrough. No smaller sample is relabelled as full calibration.
No new model calls, label joins, prompt repairs, or tuning occurred at closeout.
Any future measured comparison needs a separately recorded scope and approval.

T1/T2 were committed at f7f7943; all 392 tests passed for that implementation.
At this closeout, 37 focused tests passed: reviewed export (8), scoring (17),
grouping (12). These verify mechanics, not classifier accuracy. The existing
reviewed export index contains exactly one card dated 2026-09-04. Its browser
verification is the preserved Phase 6 verification, not a new browser test.

The current dashboard reads a static index on page load and edition JSON on date
navigation. No collection, classifier invocation, timer or scheduler is triggered
by those actions. Source collection is manual; the operator must process, review
and export a new edition before it can appear. A browser reload only reloads
the exported snapshot. There is no scheduled update frequency today.

Use [manager demo guide](manager-demo-guide.md) for the meeting and
[Phase 8 plan](phase-8-plan.md) for the next implementation scope.

Phase 7 demo closeout: CLOSED. Phase 8 planning: READY.
Paid inference and automatic publication remain unauthorized.
