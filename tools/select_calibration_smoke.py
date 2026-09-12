"""Select and freeze the 10-15 article calibration-smoke manifest (Phase 5 handover section 6).

Selection is by category -- what kind of classification challenge an article's title, publisher
and access metadata present -- never by gold label. This module reads only fields already on the
INFERENCE_ALLOWLIST (title, publisher, source_kind, access_status, evidence_scope) plus the public
entity/sector ontology in config/; it never opens an evaluator or label file, so a category match
cannot be "the model will get this one right" in disguise.

Run once, before any model output exists, and freeze the result (`freeze()` below writes an
immutable manifest with a SHA-256 of its own article-ID list). Per the one-repair rule
(Phase 5 handover section 7), this selection itself is never revisited after seeing a calibration
result -- only the prompt/schema may change, at most once.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from tools.baseline import load_config
from tools.records import dumps_jsonl, read_jsonl

# One example per category is enough for a 10-15 article smoke set; categories are listed in the
# order given by Phase 5 handover section 6 so a reviewer can check coverage at a glance.
CATEGORIES = (
    "direct_tracked_vehicle_event",
    "tracked_manager_wrong_strategy",
    "sector_only_level_b_event",
    "macro_context_level_c_event",
    "manager_level_financing",
    "routine_marketing_or_conference_notice",
    "ambiguous_or_namesake_identity",
    "multi_article_same_event_or_update",
    "routine_single_asset_cre_transaction",
    "strong_private_credit_capital_formation",
    "inaccessible_or_partial_evidence",
    "high_materiality_outside_scope_negative",
)
MACRO_TERMS = ("federal reserve", "fed ", "rate cut", "rate hike", "inflation", "spread widen",
              "treasury yield", "recession", "rate outcomes", "bond yield", "interest rate")
MARKETING_TERMS = ("conference", "summit", "webinar", "panel", "roundtable", "award", "appoints",
                  "joins as", "names ")
FINANCING_TERMS = ("credit facility", "term loan", "refinanc", "unitranche", "revolver",
                   "financing", "bridge loan", "debt facility")
# Short aliases (ED03/entities.json) that also read as ordinary words or acronyms elsewhere,
# so a bare match needs a human to resolve which entity, if any, the title actually means.
SHORT_ALIAS_TOKENS = ("nb", "pag", "kkr", "cifc")
CAPITAL_FORMATION_TERMS = ("final close", "closes", "closed", "raised", "raises", "commitments",
                           "fund iii", "fund iv", "fund v")
CRE_TERMS = ("shopping center", "retail center", "office tower", "apartment complex", "multifamily",
            "refi for", "provides", "loan for")
WRONG_STRATEGY_TERMS = ("venture", "buyback", "ipo", "initial public offering", "share repurchase")
HIGH_MATERIALITY_TERMS = ("sec charges", "fraud", "bankruptcy", "chapter 11", "indictment",
                          "enforcement action")


def _entity_aliases(config):
    aliases = {}
    for entity in config["entities"]["entities"]:
        for alias in [entity["display_name"], *entity.get("aliases", [])]:
            aliases[alias.lower()] = entity["canonical_id"]
    return aliases


def _matched_entities(title, aliases):
    lowered = title.lower()
    return sorted({entity_id for alias, entity_id in aliases.items()
                  if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered)})


def _has_any(text, terms):
    lowered = text.lower()
    return any(term in lowered for term in terms)


def categorize(record, aliases):
    title = record["title"]
    tracked = _matched_entities(title, aliases)
    reasons = []
    if tracked and _has_any(title, CAPITAL_FORMATION_TERMS):
        reasons.append("direct_tracked_vehicle_event")
    if tracked and _has_any(title, WRONG_STRATEGY_TERMS):
        reasons.append("tracked_manager_wrong_strategy")
    if tracked and _has_any(title, FINANCING_TERMS):
        reasons.append("manager_level_financing")
    if not tracked and _has_any(title, MACRO_TERMS):
        reasons.append("macro_context_level_c_event")
    if not tracked and _has_any(title, MARKETING_TERMS):
        reasons.append("routine_marketing_or_conference_notice")
    if not tracked and _has_any(title, HIGH_MATERIALITY_TERMS):
        reasons.append("high_materiality_outside_scope_negative")
    if not tracked and record["publisher"] == "Commercial Observer" and _has_any(title, CRE_TERMS):
        reasons.append("routine_single_asset_cre_transaction")
    if not tracked and record["publisher"] == "Alternative Credit Investor" and \
            _has_any(title, CAPITAL_FORMATION_TERMS):
        reasons.append("strong_private_credit_capital_formation")
    if not tracked and not reasons and record.get("evidence_scope") != "metadata_only":
        reasons.append("sector_only_level_b_event")
    if record.get("access_status") == "partial" or record.get("evidence_scope") == "metadata_only":
        reasons.append("inaccessible_or_partial_evidence")
    if re.search(r"(?<!\w)(" + "|".join(SHORT_ALIAS_TOKENS) + r")(?!\w)", title.lower()):
        reasons.append("ambiguous_or_namesake_identity")
    return reasons


def _duplicate_groups(records):
    """Group by canonical_url first (an exact same-article republish); fall back to an identical
    title (a same-event report carried by more than one outlet) when no canonical_url repeats."""
    by_url = {}
    for record in records:
        by_url.setdefault(record["canonical_url"], []).append(record["article_id"])
    groups = {key: ids for key, ids in by_url.items() if len(ids) > 1}
    if groups:
        return groups
    by_title = {}
    for record in records:
        by_title.setdefault(record["title"], []).append(record["article_id"])
    return {key: ids for key, ids in by_title.items() if len(ids) > 1}


def select(evidence_records, config, target_min=10, target_max=15):
    """Return {category: article_id} for the first matching record per category, deterministically
    (natural evidence-file order, which is not gold-informed), plus the duplicate-group pick."""
    aliases = _entity_aliases(config)
    picks = {}
    for record in evidence_records:
        for category in categorize(record, aliases):
            picks.setdefault(category, record["article_id"])
    duplicates = _duplicate_groups(evidence_records)
    if duplicates:
        first_group = sorted(duplicates)[0]
        picks["multi_article_same_event_or_update"] = duplicates[first_group]
    else:
        picks["multi_article_same_event_or_update"] = []
    if not isinstance(picks["multi_article_same_event_or_update"], list):
        picks["multi_article_same_event_or_update"] = [picks["multi_article_same_event_or_update"]]
    missing = [category for category in CATEGORIES if category not in picks or not picks[category]]
    return picks, missing


def build_manifest(evidence_path, generated_at):
    records = read_jsonl(evidence_path)
    config = load_config()
    picks, missing = select(records, config)
    article_ids = sorted({article_id for value in picks.values()
                          for article_id in (value if isinstance(value, list) else [value])
                          if article_id})
    manifest = {
        "generated_at": generated_at,
        "selection_method": ("Categories per Phase 5 handover section 6, matched deterministically "
                             "against title/publisher/access-status metadata only. No gold label, "
                             "event group or evaluator file was read to build this list."),
        "categories": {category: picks.get(category) for category in CATEGORIES},
        "missing_categories": missing,
        "article_ids": article_ids,
        "article_count": len(article_ids),
        "article_ids_sha256": hashlib.sha256(
            dumps_jsonl([{"article_id": a} for a in article_ids]).encode("utf-8")).hexdigest(),
    }
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--generated-at", required=True, help="ISO instant with offset")
    args = parser.parse_args(argv)
    manifest = build_manifest(args.evidence, args.generated_at)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite an already-frozen calibration manifest "
                              f"at {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
