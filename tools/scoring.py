"""Deterministic gates, anchor summation, publication bands and ranking.

Python owns every number here. A model may select anchors and supply reasons; it never sums a
total, sets a band, approves publication or overrides a gate. Unscorable evidence stays null and
review_required; it is never imputed to zero.
"""
from collections import Counter

from tools.records import COMPONENTS, GATE_NAMES

GATE_REASONS = {"evidence": "insufficient_evidence", "identity": "ambiguous_identity",
                "relevance": "no_relevance", "materiality": "below_materiality",
                "transmission": "weak_transmission", "novelty": "no_new_fact"}
CRITICAL_REVIEW_TYPES = ("credit_stress", "regulatory", "financial_results",
                         "liquidity_secondaries", "leadership")


def anchor_values(scoring):
    return {component["canonical_id"]: {anchor["points"] for anchor in component["anchors"]}
            for component in scoring["components"]}


def band_for(total, scoring):
    return next((band["decision"] for band in scoring["bands"]
                 if band["min"] <= total <= band["max"]), None)


def evaluate(proposal, scoring):
    """Return (gates, total, recommendation, reason_codes) for one proposed event."""
    allowed = anchor_values(scoring)
    eligibility = scoring["eligibility"]
    points, invalid = {}, []
    for name in COMPONENTS:
        component = proposal["components"].get(name) or {}
        value = component.get("points")
        if value is None:
            continue
        if value not in allowed[name]:
            invalid.append(name)
            continue
        points[name] = value
    complete = len(points) == len(COMPONENTS)
    total = sum(points.values()) if complete else None

    gates = {name: proposal.get("gates", {}).get(name, "not_evaluated") for name in GATE_NAMES}
    if invalid or not complete:
        for name in GATE_NAMES:
            if gates[name] == "not_evaluated":
                gates[name] = "review_required"
    else:
        relevance = proposal.get("relevance_level")
        minimum_transmission = (eligibility["min_transmission_C"] if relevance == "C"
                                else eligibility["min_transmission_A_B"])
        gates["evidence"] = "pass" if points["source_credibility"] >= eligibility["min_source_credibility"] else "fail"
        gates["materiality"] = "pass" if points["materiality"] >= eligibility["min_materiality"] else "fail"
        gates["transmission"] = "pass" if points["investment_transmission"] >= minimum_transmission else "fail"
        gates["novelty"] = "pass" if points["novelty"] >= eligibility["min_novelty"] else "fail"
        if relevance not in eligibility["levels"]:
            gates["relevance"] = "fail"

    outcomes = set(gates.values())
    reasons = sorted({GATE_REASONS[name] for name, outcome in gates.items() if outcome == "fail"})
    if "review_required" in outcomes or "not_evaluated" in outcomes:
        recommendation = "review_required"
        reasons = reasons or ["conflicting_evidence"]
        if invalid:
            reasons = sorted(set(reasons) | {"draft_invalid"})
    elif "fail" in outcomes:
        recommendation = "suppress"
    else:
        recommendation = band_for(total, scoring)
        if recommendation == "suppress":
            reasons = ["below_band"]
        elif recommendation == "reserve_manual_only":
            reasons = ["below_band"]
        else:
            reasons = ["shortlisted"]
    if proposal.get("critical_candidate") and proposal.get("primary_event_type") in CRITICAL_REVIEW_TYPES:
        # A tracked critical event is always surfaced, never silently suppressed by a band.
        if recommendation in {"suppress", "reserve_manual_only"}:
            recommendation = "review_required"
        reasons = sorted(set(reasons) | {"critical_review"})
    return gates, total, recommendation, reasons


SELECTED = {"priority_shortlist", "shortlist"}


def _europe_share(region_history):
    counts = Counter(region_history or [])
    published = sum(counts.values())
    return (counts.get("Europe", 0) / published) if published else 0.0


def rank(decisions, scoring, region_history=None):
    """Order selected events. Geography is a post-hoc tie-break, never part of the score."""
    geography = scoring["geography"]
    ordered = sorted(decisions, key=lambda d: (not _is_critical(d), -(d.get("total_score") or 0),
                                               d["event_id"]))
    if _europe_share(region_history) >= geography["europe_target"]:
        return ordered
    window = 5  # scoring.json geography.tie_break: same band, within five points.
    for index in range(len(ordered) - 1):
        first, second = ordered[index], ordered[index + 1]
        if _is_critical(first) or _is_critical(second):
            continue
        if first.get("recommendation") != second.get("recommendation"):
            continue
        if (first.get("total_score") or 0) - (second.get("total_score") or 0) > window:
            continue
        if second.get("primary_region") == "Europe" and first.get("primary_region") != "Europe":
            ordered[index], ordered[index + 1] = second, first
    return ordered


def rank_ablation(decisions):
    """Ablation: critical status, then materiality and transmission anchors, then direct fit."""
    def key(decision):
        components = decision.get("components", {})

        def anchor(name):
            return (components.get(name) or {}).get("points") or 0
        return (not _is_critical(decision), -anchor("materiality"),
                -anchor("investment_transmission"), -anchor("portfolio_fit"), decision["event_id"])
    return sorted(decisions, key=key)


def _is_critical(decision):
    return "critical_review" in (decision.get("disposition_reason_codes") or [])


def group_by_date(decisions, dates_by_event_id):
    """Bucket decisions by their calendar date. An event with no established date buckets to None."""
    buckets = {}
    for decision in decisions:
        key = dates_by_event_id.get(decision["event_id"])
        buckets.setdefault(key, []).append(decision)
    return buckets


def select_editions_by_day(decisions, dates_by_event_id, scoring, region_history=None):
    """Apply the daily capacity target once per calendar day, not once across a whole partition.

    A single select_edition() call over a month of decisions lets one busy day consume the whole
    target_max capacity, starving every other day -- the daily selection is then a run-wide cap in
    disguise. This re-ranks and re-selects within each dated bucket independently, so the target
    (6-10, no minimum) is a per-day preference as the rulebook specifies. region_history rolls
    forward day by day so the Europe/US tie-break reflects an actual trailing calendar window
    rather than a single partition-wide snapshot. Returns (editions_by_date, undated_decisions).
    """
    buckets = group_by_date(decisions, dates_by_event_id)
    undated = buckets.pop(None, [])
    editions, history = {}, list(region_history or [])
    for day in sorted(buckets):
        ranked_day = rank(buckets[day], scoring, history)
        edition = select_edition(ranked_day, scoring, history)
        editions[day] = edition
        history = history + [d["primary_region"] for d in edition["selected"]]
    return editions, undated


def select_edition(ranked, scoring, region_history=None):
    """Apply the daily target as a capacity preference. No artificial minimum is enforced."""
    publication = scoring["publication"]
    selected, overflow, urgent, capacity = [], [], [], publication["target_max"]
    for decision in ranked:
        shortlisted = decision.get("recommendation") in SELECTED
        if _is_critical(decision) and not shortlisted:
            # Critical events are surfaced for urgent review; a band never silences one.
            urgent.append(decision)
        elif shortlisted and (len(selected) < capacity or _is_critical(decision)):
            selected.append(decision)
        elif shortlisted:
            overflow.append(decision)
    return {"selected": selected, "overflow": overflow, "urgent_review": urgent,
            "below_target": len(selected) < publication["target_min"],
            "enforce_min": publication["enforce_min"],
            "europe_share": _europe_share(region_history),
            "note": "Analyst review required before any publication."}
