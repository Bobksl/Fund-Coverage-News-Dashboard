"""Deterministic Phase 2 baseline: config-driven entity resolution and transparent rules.

This is the comparison floor for the structured pipeline, not a finished classifier. Every
decision here is traceable to a config entry or a rule constant below. Uncertain cases are
preserved for review; they never become silent zero-score rejections.
"""
import re
from pathlib import Path

from tools.records import loads

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"
# ER06 namesake, ER07 NB and ER08 HSBC matches need corroboration before they resolve.
CONDITIONAL_RULES = {"ER06", "ER07", "ER08"}
CREDIT_CONTEXT = ("credit", "lending", "loan", "fund", "asset management", "investment",
                  "portfolio", "borrower", "bdc", "private debt")
TICKER_CONTEXT = ("nyse", "nasdaq", "ticker", "shares", "stock", "listed")
# Transparent event-type phrases. Config carries subtypes but no lexicon by design.
EVENT_PHRASES = (
    ("credit_stress", "non_accrual", ("non-accrual", "nonaccrual", "default", "missed payment",
                                     "covenant breach", "restructuring", "impairment", "writedown",
                                     "write-down", "bankruptcy", "chapter 11")),
    ("regulatory", "enforcement", ("sec charges", "enforcement action", "investigation",
                                   "subpoena", "consent order", "settlement with")),
    ("ratings", "rating_action", ("downgrade", "upgraded", "outlook negative", "placed on watch",
                                  "affirmed rating", "assigned a rating")),
    ("financial_results", "quarterly", ("quarterly results", "fourth quarter", "third quarter",
                                        "net asset value", "net investment income", "earnings")),
    ("structured_finance", "clo", ("clo", "collateralized loan obligation", "securitization",
                                   "rated notes", "abs")),
    ("liquidity_secondaries", "continuation", ("continuation fund", "secondary market",
                                               "gp-led", "tender offer")),
    ("gp_stakes", "minority_stake", ("gp stake", "gp stakes", "minority stake in the manager")),
    ("capital_formation", "final_close", ("final close", "closes", "closed", "closing of",
                                          "raised", "fundraising", "capital raise", "commitments")),
    ("financing", "credit_facility", ("credit facility", "term loan", "refinancing",
                                      "unitranche", "financing package", "revolver")),
    ("corporate_transaction", "acquisition", ("acquire", "acquisition of", "merger", "to buy")),
    ("leadership", "appointment", ("appointed", "named managing director", "joins as",
                                   "steps down", "resigned")),
    ("strategy_platform", "expansion", ("launches", "expands", "new platform", "partnership")),
    ("macro_policy", "policy", ("federal reserve", "rate cut", "rate hike", "regulation proposed")),
    ("market_conditions", "conditions", ("spreads widened", "market conditions", "issuance volume")),
)
ROUTINE_PHRASES = ("award", "recognized as", "best places to work", "sponsorship", "webinar",
                   "conference", "white paper", "ranking")
CRITICAL_TYPES = {"credit_stress", "regulatory"}
MACRO_TYPES = {"macro_policy", "market_conditions"}
AMOUNT = re.compile(r"(?:us)?\$\s?([\d,.]+)\s?(billion|million|bn|mn|m|b)\b", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def load_config(root=CONFIG_ROOT):
    root = Path(root)
    return {path.stem: loads(path.read_text(encoding="utf-8")) for path in sorted(root.glob("*.json"))}


def _phrase_pattern(phrase):
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.I)


def _host(url):
    match = re.match(r"https?://([^/]+)", url or "", re.I)
    return (match.group(1) if match else "").lower().split(":")[0]


def _host_matches(host, domains):
    # ER02: exact host or dot-delimited subdomain only; never a deceptive suffix.
    return any(host == domain or host.endswith("." + domain) for domain in domains or ())


def match_entities(text, url, entities):
    """Resolve entity mentions with ER01-ER08 safeguards. Ambiguous matches stay ambiguous."""
    host = _host(url)
    sentences = SENTENCE.split(text or "")
    matches = []
    for entity in entities:
        names = list(entity.get("aliases") or []) + list(entity.get("legacy_names") or [])
        conditional = bool(CONDITIONAL_RULES & set(entity.get("ambiguity_rules") or []))
        official = _host_matches(host, entity.get("official_domains"))
        # Config exclusions are matched literally. Descriptive entries ("property/street names")
        # therefore do not fire; an unmatched exclusion sends the case to review, never a
        # silent drop. This is a stated baseline limit, not an entity-resolution claim.
        excluded = [phrase for phrase in entity.get("excluded_contexts") or []
                    if _phrase_pattern(phrase).search(text or "")]
        best = None
        for name in sorted(names, key=lambda value: -len(value.split())):
            pattern = _phrase_pattern(name)
            found = pattern.search(text or "")
            if not found:
                continue
            sentence = next((s for s in sentences if pattern.search(s)), text or "")
            qualified = len(name.split()) > 1
            corroborated = official or qualified or any(
                term in sentence.lower() for term in CREDIT_CONTEXT)
            status = "resolved" if (not conditional or corroborated) else "ambiguous"
            best = {"canonical_id": entity["canonical_id"], "matched_text": found.group(0),
                    "span": [found.start(), found.end()], "status": status,
                    "rule": "ER06/ER07/ER08" if conditional else "ER01",
                    "official_host": official,
                    "relationship_path": [entity["canonical_id"]] if not entity.get("parent")
                    else [entity["canonical_id"], entity["parent"]]}
            break
        ticker = entity.get("ticker") or {}
        if not best and ticker.get("symbol"):
            symbol = re.compile(r"(?<!\w)" + re.escape(ticker["symbol"]) + r"(?!\w)")
            found = symbol.search(text or "")
            if found:
                sentence = next((s for s in sentences if symbol.search(s)), "")
                # ER04: a bare symbol never resolves an issuer.
                qualifies = ticker.get("exchange", "").lower() in sentence.lower() or any(
                    term in sentence.lower() for term in TICKER_CONTEXT)
                best = {"canonical_id": entity["canonical_id"], "matched_text": found.group(0),
                        "span": [found.start(), found.end()],
                        "status": "resolved" if qualifies else "ambiguous", "rule": "ER04",
                        "official_host": official, "relationship_path": [entity["canonical_id"]]}
        if best:
            if excluded:
                best["status"] = "excluded"
                best["excluded_context"] = excluded
            matches.append(best)
    return _apply_vehicle_precedence(matches)


def _apply_vehicle_precedence(matches):
    """ER05: the longest full name wins; a shorter name inside it is not a second subject.

    The nested match is kept as suppressed evidence so the parent tag stays visible without
    claiming the parent is the article's subject.
    """
    for match in matches:
        start, end = match["span"]
        covering = next((other for other in matches if other is not match
                         and other["span"][0] <= start and end <= other["span"][1]
                         and other["span"][1] - other["span"][0] > end - start), None)
        if covering:
            match["status"] = "suppressed_by_longer_name"
            match["suppressed_by"] = covering["canonical_id"]
    return matches


def _event_type(text):
    # Whole-token matching only: a substring test reads "CLO" inside "closes".
    for event_type, subtype, phrases in EVENT_PHRASES:
        if any(_phrase_pattern(phrase).search(text or "") for phrase in phrases):
            return event_type, subtype
    return "other", None


def _largest_amount(text):
    best = 0.0
    for number, unit in AMOUNT.findall(text or ""):
        try:
            value = float(number.replace(",", ""))
        except ValueError:
            continue
        best = max(best, value * (1000 if unit.lower() in {"billion", "bn", "b"} else 1))
    return best


def _tagged_sectors(config, text):
    lowered = (text or "").lower()
    hits = []
    for sector in config["sectors"]["sectors"]:
        terms = list(sector.get("synonyms") or []) + list(sector.get("related_terminology") or [])
        if any(term.lower() in lowered for term in terms if len(term) > 3):
            hits.append(sector["canonical_id"])
    return hits


def linkable_themes(config, sectors):
    """Themes whose linked sectors were tagged. Candidates for review, not an assignment.

    Theme trigger conditions are prose the baseline cannot evaluate, and one tagged sector links
    many themes, so assigning them all would be noise dressed as analysis. The baseline therefore
    assigns no theme and records the candidates instead. Earning these tags is work for the
    structured pipeline.
    """
    return sorted({theme["canonical_id"] for theme in config["themes"]["themes"]
                   if set(theme.get("linked_sectors") or []) & set(sectors)})


def propose(article_input, config, body=None):
    """Return one engine-neutral proposal for a single article. No grouping, scoring or ranking."""
    text = " ".join(filter(None, [article_input.get("title"), body or article_input.get("body")]))
    matches = match_entities(text, article_input.get("canonical_url"), config["entities"]["entities"])
    resolved = [m for m in matches if m["status"] == "resolved"]
    ambiguous = [m for m in matches if m["status"] == "ambiguous"]
    event_type, subtype = _event_type(text)
    sectors = _tagged_sectors(config, text)
    theme_candidates = linkable_themes(config, sectors)
    routine = any(phrase in text.lower() for phrase in ROUTINE_PHRASES)
    amount = _largest_amount(text)

    if resolved:
        relevance, fit, reason = "A", 30, "Resolved tracked entity as article subject"
    elif sectors:
        relevance, fit, reason = "B", 25, "Monitored sector without a tracked entity subject"
    elif event_type in MACRO_TYPES:
        relevance, fit, reason = "C", 20, "Macro path proposed; baseline cannot verify a specific channel"
    else:
        relevance, fit, reason = None, 0, "No qualifying connection"

    if routine or event_type == "other":
        materiality, actionability = 5, 3
    elif event_type in CRITICAL_TYPES or amount >= 1000:
        materiality, actionability = 20, 8
    elif amount > 0 or event_type in {"financial_results", "structured_finance", "capital_formation"}:
        materiality, actionability = 15, 6
    else:
        materiality, actionability = 5, 3

    if relevance == "A" and event_type != "other" and not routine:
        transmission_points = 15
    elif relevance == "B" and sectors and event_type != "other":
        transmission_points = 10
    elif relevance:
        # Generic macro keeps a low anchor and fails the Level C threshold by design.
        transmission_points = 5
    else:
        transmission_points = 0

    credibility = {"filing": 10, "regulatory_record": 10, "issuer_release": 7,
                   "independent_reporting": 7, "ratings_analysis": 7,
                   "discovery_only": 4, "other": 4}.get(article_input.get("source_kind"), 4)
    if article_input.get("access_status") == "unavailable" or article_input.get("evidence_scope") == "metadata_only":
        credibility = min(credibility, 4)
    novelty = 2 if re.search(r"\bupdate[ds]?\b|\brevised\b|\bcorrection\b", text, re.I) else 5

    identity_gate = "review_required" if (ambiguous and not resolved) else (
        "pass" if resolved or relevance else "fail")
    relevance_gate = "pass" if relevance else "fail"
    return {
        "article_id": article_input["article_id"],
        "engine": "deterministic_baseline",
        "entity_matches": matches,
        "direct_entity_ids": [m["canonical_id"] for m in resolved],
        "propagated_entity_ids": sorted({parent for m in resolved
                                         for parent in m["relationship_path"][1:]}
                                        | {m["canonical_id"] for m in matches
                                           if m["status"] == "suppressed_by_longer_name"}),
        "event_identity": {
            # No publisher fallback: an unnamed subject is not a party, and two unresolved
            # articles from the same wire must not merge into one invented event.
            "parties": sorted({m["matched_text"] for m in resolved}),
            "action": event_type, "vehicle": None, "period": None,
            "event_date": article_input.get("event_date"),
        },
        "primary_event_type": event_type, "subtype": subtype, "secondary_event_types": [],
        "sector_ids": sectors, "theme_ids": [],
        "theme_candidates": theme_candidates,
        "asset_classes": ["private_credit"] if "private_credit" in sectors else [],
        "countries": [], "primary_region": "Unknown",
        "region_basis": "Baseline does not infer region from publisher or headquarters",
        "relevance_level": relevance, "eligibility_reason": reason,
        "transmission": {"trigger": event_type, "mechanism": reason,
                         "outcome": "monitored strategy exposure", "uncertainty": "baseline rule only"},
        "components": {
            "portfolio_fit": {"points": fit, "reason": reason, "evidence_refs": []},
            "materiality": {"points": materiality, "reason": f"amount basis {amount or 'none'}; routine={routine}", "evidence_refs": []},
            "investment_transmission": {"points": transmission_points, "reason": reason, "evidence_refs": []},
            "actionability": {"points": actionability, "reason": f"event type {event_type}", "evidence_refs": []},
            "source_credibility": {"points": credibility, "reason": f"source_kind {article_input.get('source_kind')}", "evidence_refs": []},
            "novelty": {"points": novelty, "reason": "update wording detected" if novelty == 2 else "treated as new event", "evidence_refs": []},
        },
        "gates": {"identity": identity_gate, "relevance": relevance_gate},
        "critical_candidate": event_type in CRITICAL_TYPES and bool(resolved),
        "flags": [m["canonical_id"] for m in ambiguous],
        "raw_output_ref": None,
    }
