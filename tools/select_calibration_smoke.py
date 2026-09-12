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
# Genuine conference/panel/award wording only. "Appoints"/"joins as"/"names " are removed from
# this list after external review (docs/phase-5-review-decisions.md Ticket data point on manifest
# fidelity): those are leadership-appointment or business-mandate wording, not routine marketing,
# and a real investment mandate ("Utmost appoints Aberdeen to manage RE debt") must not be
# miscategorized as a marketing notice merely for containing "appoints".
MARKETING_TERMS = ("conference", "summit", "webinar", "panel", "roundtable", "forum", "symposium")
# "<Entity> at <Named Event> <year>" (e.g. "CIFC at BNY INSITE 2026") reads as a named industry
# event even when it uses none of the words in MARKETING_TERMS. Requiring "at" immediately before
# a capitalized event name and a year excludes an unrelated year appearing elsewhere in a title
# (a filing date, an address, a fund vintage) -- a plain 4-digit-year match is not enough on its
# own, per external review flagging a KKR 8-K filing date as a false positive under that looser rule.
EVENT_YEAR_PATTERN = re.compile(r"\bat\s+[A-Z][\w&.\s]*\b(19|20)\d{2}\b")
FILING_TERMS = ("8-k", "10-q", "10-k", "form 4", "proxy statement", "sec filing")
FINANCING_TERMS = ("credit facility", "term loan", "refinanc", "unitranche", "revolver",
                   "financing", "bridge loan", "debt facility", "senior notes", "private placement")
# A financing headline where the tracked entity is the one supplying capital to someone else
# ("Blue Owl ... Financing For IREN") is not the entity raising financing for itself -- the
# distinguishing signal is whether the title names who the financing is FOR/TO, or who is
# providing/arranging it, versus the entity itself closing/securing/issuing its own instrument.
SELF_RAISE_TERMS = ("closes", "secures", "issues", "raises")
LENDER_OUT_MARKERS = (" for ", " to ", "leads", "provides", "lends")
# Short aliases (ED03/entities.json) that also read as ordinary words or acronyms elsewhere. A
# bare match still needs a human to resolve which entity, if any, the title actually means -- but
# only when nothing in the title already disambiguates it. "KKR & Co. Inc. -- 8-K" and "CIFC at
# BNY INSITE" are the tracked entity's own full/short legal name in an unambiguous filing or event
# context, not a namesake collision, so a disambiguating suffix right after the token is excluded.
# "PAG" was removed after external review round 2: the one corpus hit (PAG/Cordina) is an
# explicit, unambiguous PAG divestment, not a namesake collision -- it is now correctly assigned
# to tracked_manager_wrong_strategy instead (see EQUITY_TRANSACTION_TERMS above). No genuine
# namesake-collision example was found in this corpus for "nb" either; that category is an
# honestly recorded gap, not filled with a borderline match.
SHORT_ALIAS_TOKENS = ("nb",)
DISAMBIGUATING_SUFFIXES = ("& co", "inc", "capital", "l.p.", "partners", "corp", "8-k", "at bny")
CAPITAL_FORMATION_TERMS = ("final close", "closes", "closed", "raised", "raises", "commitments",
                           "fund iii", "fund iv", "fund v")
CRE_TERMS = ("shopping center", "retail center", "office tower", "apartment complex", "multifamily",
            "refi for", "provides", "loan for")
# "Joint venture" is a corporate-structure term, not evidence of an off-strategy activity, so it
# is excluded even though it contains "venture" -- Astra review round 1 flagged "Enbridge and KKR
# Announce New Joint Venture" as a false positive under the previous bare "venture" match.
WRONG_STRATEGY_TERMS = ("venture capital", "buyback", "ipo", "initial public offering",
                        "share repurchase")
WRONG_STRATEGY_EXCLUDE = ("joint venture",)
# Round 2's bounded search (docs/phase-5-review-decisions.md): a tracked manager explicitly
# transacting equity ownership of an operating business, with no debt/credit-sector language
# present, is an off-strategy (equity-portfolio, not private-credit) activity -- the shape Astra
# specified for "tracked_manager_wrong_strategy" after rejecting the v1 "venture" match and the
# v2 "ambiguous identity" assignment of the same PAG/Cordina article.
EQUITY_TRANSACTION_TERMS = ("majority stake", "minority stake", "acquires stake", "sells stake",
                            "stake in", "divests")
CREDIT_CONTEXT_EXCLUDE = ("credit", "debt", "loan", "lending", "financing", "restructuring",
                          "facility")
HIGH_MATERIALITY_TERMS = ("sec charges", "fraud", "bankruptcy", "chapter 11", "indictment",
                          "enforcement action")
# A sector-only Level B candidate needs a signal shape a read-through could plausibly attach to
# (a credit-quality, distress or growth metric on an untracked company/segment) -- not simply
# "the first untracked article with no other match," which the prior fallback amounted to.
SECTOR_SIGNAL_TERMS = ("distress", "downgrade", "delinquenc", "default", "non-accrual",
                       "credit quality", "revenue growth", "spread widen", "underwriting",
                       "write-down", "impairment", "npl")


def _entity_aliases(config):
    aliases = {}
    for entity in config["entities"]["entities"]:
        for alias in [entity["display_name"], *entity.get("aliases", [])]:
            aliases[alias.lower()] = entity["canonical_id"]
    return aliases


def _entity_types(config):
    return {entity["canonical_id"]: entity["entity_type"] for entity in config["entities"]["entities"]}


def _matched_entities(title, aliases):
    lowered = title.lower()
    return sorted({entity_id for alias, entity_id in aliases.items()
                  if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered)})


def _most_specific_entity(title, aliases):
    """The entity whose matched alias is the longest substring, so "Blue Owl Technology Finance
    Corp." (the vehicle OTF's own name, which happens to start with its manager's name "Blue Owl")
    resolves to OTF, not to Blue Owl the manager -- a shorter alias being a substring of a longer,
    more specific one matched in the same title is not the same fact as the title being about that
    shorter entity (external review round 2: this shadowing made OTF's own notes issuance
    miscount as manager-level financing)."""
    lowered = title.lower()
    best = None
    for alias, entity_id in aliases.items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered):
            if best is None or len(alias) > len(best[0]):
                best = (alias, entity_id)
    return best[1] if best else None


def _has_any(text, terms):
    lowered = text.lower()
    return any(term in lowered for term in terms)


def categorize(record, aliases, entity_types=None):
    entity_types = entity_types or {}
    title = record["title"]
    lowered = title.lower()
    tracked = _matched_entities(title, aliases)
    most_specific = _most_specific_entity(title, aliases)
    reasons = []
    if tracked and _has_any(title, CAPITAL_FORMATION_TERMS):
        reasons.append("direct_tracked_vehicle_event")
    if (tracked and _has_any(title, EQUITY_TRANSACTION_TERMS)
            and not _has_any(title, CREDIT_CONTEXT_EXCLUDE)
            and not _has_any(title, WRONG_STRATEGY_EXCLUDE)):
        reasons.append("tracked_manager_wrong_strategy")
    elif tracked and _has_any(title, WRONG_STRATEGY_TERMS) and not _has_any(title, WRONG_STRATEGY_EXCLUDE):
        reasons.append("tracked_manager_wrong_strategy")
    # Only a manager-typed entity (not a fund/vehicle/business_platform sharing an overlapping
    # alias) raising its own instrument counts as manager-level financing.
    if (entity_types.get(most_specific) == "manager" and _has_any(title, FINANCING_TERMS)
            and _has_any(title, SELF_RAISE_TERMS) and not _has_any(title, LENDER_OUT_MARKERS)):
        reasons.append("manager_level_financing")
    if not tracked and _has_any(title, MACRO_TERMS):
        reasons.append("macro_context_level_c_event")
    if _has_any(title, MARKETING_TERMS) or (tracked and EVENT_YEAR_PATTERN.search(title)
                                            and not _has_any(title, FILING_TERMS +
                                                             FINANCING_TERMS +
                                                             CAPITAL_FORMATION_TERMS +
                                                             WRONG_STRATEGY_TERMS)):
        reasons.append("routine_marketing_or_conference_notice")
    if not tracked and _has_any(title, HIGH_MATERIALITY_TERMS):
        reasons.append("high_materiality_outside_scope_negative")
    if not tracked and record["publisher"] == "Commercial Observer" and _has_any(title, CRE_TERMS):
        reasons.append("routine_single_asset_cre_transaction")
    if not tracked and record["publisher"] == "Alternative Credit Investor" and \
            _has_any(title, CAPITAL_FORMATION_TERMS):
        reasons.append("strong_private_credit_capital_formation")
    if (not tracked and _has_any(title, SECTOR_SIGNAL_TERMS)
            and record.get("evidence_scope") != "metadata_only"):
        reasons.append("sector_only_level_b_event")
    if record.get("access_status") == "partial" or record.get("evidence_scope") == "metadata_only":
        reasons.append("inaccessible_or_partial_evidence")
    for token in SHORT_ALIAS_TOKENS:
        for match in re.finditer(rf"(?<!\w){token}(?!\w)", lowered):
            tail = lowered[match.end():match.end() + 10]
            if not any(tail.startswith(suffix) or lowered[:match.start()].rstrip().endswith(suffix)
                      for suffix in DISAMBIGUATING_SUFFIXES):
                reasons.append("ambiguous_or_namesake_identity")
                break
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
    entity_types = _entity_types(config)
    picks = {}
    for record in evidence_records:
        for category in categorize(record, aliases, entity_types):
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


MANIFEST_VERSION = "v3"
# Per external review round 2: "describe B/C as candidate challenges where metadata cannot
# establish eligibility" -- title/publisher/access-status metadata can *credibly establish* some
# category shapes (a duplicate canonical_url really is the same event; a partial access_status
# really is inaccessible evidence) but can only *present a plausible testing shape* for others (a
# revenue-growth headline might or might not turn out to be a real B read-through; that is exactly
# what the calibration run is for). Reporting both as equally "verified positive coverage" would
# overclaim what metadata alone can show.
CATEGORY_CONFIDENCE = {
    "direct_tracked_vehicle_event": "established",
    "tracked_manager_wrong_strategy": "established",
    "sector_only_level_b_event": "candidate_shape_only",
    "macro_context_level_c_event": "candidate_shape_only",
    "manager_level_financing": "gap",
    "routine_marketing_or_conference_notice": "established",
    "ambiguous_or_namesake_identity": "gap",
    "multi_article_same_event_or_update": "established",
    "routine_single_asset_cre_transaction": "established",
    "strong_private_credit_capital_formation": "established",
    "inaccessible_or_partial_evidence": "established",
    "high_materiality_outside_scope_negative": "gap",
}


def build_manifest(evidence_path, generated_at, supersedes=None):
    """`supersedes` names a prior manifest version this one replaces (e.g. "v1"), and why -- per
    external review, category assignments must be fixed with tighter metadata-only criteria, not
    silently overwritten. The prior manifest is never deleted; freeze() below refuses to overwrite
    an existing file at all, so a superseding manifest must be written to a new path.
    """
    records = read_jsonl(evidence_path)
    config = load_config()
    picks, missing = select(records, config)
    article_ids = sorted({article_id for value in picks.values()
                          for article_id in (value if isinstance(value, list) else [value])
                          if article_id})
    confidence = {category: ("gap" if category in missing else CATEGORY_CONFIDENCE.get(category))
                 for category in CATEGORIES}
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "supersedes": supersedes,
        "generated_at": generated_at,
        "selection_method": ("Categories per Phase 5 handover section 6, matched deterministically "
                             "against title/publisher/access-status metadata only. No gold label, "
                             "event group or evaluator file was read to build this list. v3 acts on "
                             "an external review round 2 (docs/phase-5-review-decisions.md): "
                             "distinguishes ESTABLISHED categories (metadata alone credibly "
                             "supports the assignment, e.g. a duplicate canonical_url or a "
                             "partial access_status) from CANDIDATE_SHAPE_ONLY ones (a plausible "
                             "testing shape whose actual eligibility only the calibration run can "
                             "establish, e.g. a sector-growth headline that may or may not be a "
                             "real B read-through); reassigned the PAG/Cordina article from "
                             "ambiguous_identity to wrong_strategy (an explicit equity divestment, "
                             "not a namesake collision) via a bounded metadata-only search; and "
                             "fixed manager_level_financing to require the matched entity actually "
                             "be manager-typed (OTF's own notes issuance is vehicle financing, not "
                             "manager financing) -- which currently leaves that category, and "
                             "ambiguous_or_namesake_identity, without a credible candidate. "
                             "See docs/phase-5-review-decisions.md for the full external review."),
        "categories": {category: picks.get(category) for category in CATEGORIES},
        "category_confidence": confidence,
        "missing_categories": missing,
        "missing_category_disposition": ("No credible candidate was found in the natural-feed "
                                         "corpus under metadata-only criteria for these categories; "
                                         "the gap is recorded rather than filled with a forced or "
                                         "borderline match.") if missing else None,
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
    parser.add_argument("--supersedes", default=None,
                        help="Prior manifest version this replaces, e.g. v1")
    args = parser.parse_args(argv)
    manifest = build_manifest(args.evidence, args.generated_at, supersedes=args.supersedes)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite an already-frozen calibration manifest "
                              f"at {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
