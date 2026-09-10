"""Static Phase 1 consistency checks; does not classify news or validate investment quality."""

import json
import re
from pathlib import Path


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


def main():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "config").glob("*.json"))
    paths.append(root / "examples/editorial-cases.json")
    data = {
        p.stem: json.loads(p.read_text(encoding="utf-8"),
                          object_pairs_hook=unique_keys, parse_constant=reject_constant)
        for p in paths
    }
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    def index(name, collection, key="canonical_id"):
        items = data[name][collection]
        ids = [item[key] for item in items]
        check(len(ids) == len(set(ids)), f"Duplicate IDs in {name}/{collection}")
        return dict(zip(ids, items))

    entities = index("entities", "entities")
    sources = index("sources", "sources", "source_id")
    sectors = index("sectors", "sectors")
    themes = index("themes", "themes")
    events = index("event_types", "event_types")
    rules = index("entities", "matching_rules", "rule_id")
    cases = index("editorial-cases", "cases", "case_id")
    scoring = data["scoring"]
    components = index("scoring", "components")
    check(all(d["schema_version"] == "0.1.0" for d in data.values()), "Version mismatch")
    watchlist = data["entities"]["watchlist"]
    check(len(watchlist) == len(set(watchlist)) == 13, "Expected 13 unique watchlist entries")
    check(set(watchlist) <= entities.keys(), "Unknown watchlist ID")
    check(len(sectors) == 8 and len(themes) == 11, "Required sector/theme coverage")
    required = set("canonical_id display_name entity_type parent parent_relationship aliases "
                   "legacy_names ticker official_domains relevant_business_lines relevant_subsidiaries "
                   "relevant_funds excluded_contexts ambiguity_rules search_terms notes evidence_refs "
                   "needs_review review_note".split())
    for eid, entity in entities.items():
        check(required <= entity.keys(), f"{eid}: missing entity fields")
        check(bool(entity["evidence_refs"]) and set(entity["evidence_refs"]) <= sources.keys(),
              f"{eid}: missing/unknown source")
        check(set(entity["ambiguity_rules"]) <= rules.keys(), f"{eid}: unknown rule")
        related = entity["relevant_subsidiaries"] + entity["relevant_funds"]
        check(set(related) <= entities.keys(), f"{eid}: unknown related entity")
        check((entity["parent"] is None) == (entity["parent_relationship"] is None),
              f"{eid}: untyped parent")
        check(not entity["needs_review"] or bool(entity["review_note"]), f"{eid}: review note missing")
        check("adviser" not in entity or entity["adviser"] in entities, f"{eid}: unknown adviser")
        check(all(re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}", host)
                  for host in entity["official_domains"]), f"{eid}: malformed domain")
        seen, cursor = set(), eid
        while cursor is not None:
            if cursor not in entities or cursor in seen:
                errors.append(f"{eid}: unknown/cyclic parent")
                break
            seen.add(cursor)
            cursor = entities[cursor]["parent"]
    for sid, sector in sectors.items():
        check(set(sector["high_signal_event_types"]) <= events.keys(), f"{sid}: unknown event")
    for tid, theme in themes.items():
        check(set(theme["linked_sectors"]) <= sectors.keys(), f"{tid}: unknown sector")
    check(sum(c["max_points"] for c in components.values()) == scoring["total_max"] == 100,
          "Score weights must total 100")
    check(not scoring["geography"]["included_in_score"], "Geography cannot affect score")
    covered = [v for band in scoring["bands"] for v in range(band["min"], band["max"] + 1)]
    check(sorted(covered) == list(range(101)), "Score bands overlap or have gaps")
    check(set(scoring["critical_override"]["eligible_types"]) <= events.keys(), "Unknown override type")
    for cid, case in cases.items():
        check(case["hypothetical"] is True, f"{cid}: missing hypothetical flag")
        check(set(case["direct_entity_ids"]) <= entities.keys(), f"{cid}: unknown entity")
        check(set(case["sector_ids"]) <= sectors.keys(), f"{cid}: unknown sector")
        event = events.get(case["primary_event_type"])
        check(event is not None and case["subtype"] in event["subtypes"], f"{cid}: invalid type/subtype")
        scores = case["components"]
        if scores is None:
            check(case["expected_total"] is None, f"{cid}: unscored total must be null")
            continue
        check(set(scores) == set(components), f"{cid}: missing/extra score component")
        for key, value in scores.items():
            allowed = [a["points"] for a in components.get(key, {}).get("anchors", [])]
            check(type(value) is int and value in allowed, f"{cid}: invalid anchor {key}")
        total = sum(scores.values())
        check(total == case["expected_total"], f"{cid}: incorrect total")
        gate = scoring["eligibility"]
        transmission_min = gate["min_transmission_C"] if case["relevance_level"] == "C" else gate["min_transmission_A_B"]
        qualifies = (case["relevance_level"] in gate["levels"]
                     and scores["materiality"] >= gate["min_materiality"]
                     and scores["investment_transmission"] >= transmission_min
                     and scores["source_credibility"] >= gate["min_source_credibility"]
                     and scores["novelty"] >= gate["min_novelty"])
        band = next((b["decision"] for b in scoring["bands"] if b["min"] <= total <= b["max"]), None)
        expected = band if qualifies else "suppress"
        check(expected == case["expected_recommendation"], f"{cid}: expected {expected}, not fixture band")
    report = {"json_files": len(paths), "entities": len(entities), "sources": len(sources),
              "sectors": len(sectors), "themes": len(themes), "event_types": len(events),
              "hypothetical_cases": len(cases), "errors": errors}
    print(json.dumps(report, indent=2))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
