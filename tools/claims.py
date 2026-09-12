"""Deterministic claim construction for the analyst-reviewed historical demo (Phase 5 handover
section 5E).

Claims ground `tools.drafting.Drafter` in permitted evidence. This module never asks a model to
invent one: it extracts currency/amount figures that are literally present in a supplied body of
text and ties each to the exact matched substring as `evidence_span`, so a reviewer can search the
source for it. A qualitative (non-numeric) claim is not manufactured here -- a caller may still
build one by hand, following the same `claim_id`/`article_id`/`evidence_span` shape, when the
event's material fact is not a number.

This is deliberately the smallest defensible mechanism ("deterministic/manual-assisted claim
construction is acceptable" for this slice), not a general information-extraction pipeline.
"""
import re

AMOUNT_PATTERN = re.compile(
    r"(?P<currency>USD|EUR|GBP|\$|€|£)\s?(?P<amount>\d[\d,]*\.?\d*)\s*"
    r"(?P<unit>trillion|billion|bn|million|mn|thousand|\bm\b|\bk\b)?", re.IGNORECASE)
CURRENCY_CODES = {"$": "USD", "USD": "USD", "EUR": "EUR", "€": "EUR", "GBP": "GBP", "£": "GBP"}
UNIT_NORMAL = {"trillion": "trillion", "billion": "billion", "bn": "billion", "million": "million",
              "mn": "million", "thousand": "thousand", "m": "million", "k": "thousand"}
REQUIRED_NUMERIC_FIELDS = ("currency", "unit", "basis", "period")


def _currency_code(raw):
    return CURRENCY_CODES.get(raw) or CURRENCY_CODES.get(raw.upper())


def extract_amount_claims(article_id, body, basis, period, start_index=1):
    """Return one claim record per currency amount literally present in `body`.

    `basis` states what the figure represents (e.g. "final close size", "loan amount"); the
    extractor cannot infer intent from a bare number, only its presence, so the caller supplies
    it once per call. `period` is likewise supplied by the caller (e.g. an ISO date or quarter)
    rather than guessed. Every claim satisfies tools.records.validate_article's numeric-claim
    contract: currency, unit, basis and period are all set whenever amount is not None.
    """
    claims = []
    for offset, match in enumerate(AMOUNT_PATTERN.finditer(body or ""), start=start_index):
        currency = _currency_code(match.group("currency"))
        if currency is None:
            continue
        try:
            amount = float(match.group("amount").replace(",", ""))
        except ValueError:
            continue
        unit_raw = match.group("unit")
        unit = UNIT_NORMAL.get(unit_raw.lower()) if unit_raw else "plain"
        span = match.group(0).strip()
        claims.append({
            "claim_id": f"{article_id}-amt{offset}",
            "statement": span,
            "article_id": article_id,
            "evidence_span": span,
            "amount": amount,
            "currency": currency,
            "unit": unit,
            "basis": basis,
            "period": period,
        })
    return claims


def manual_claim(claim_id, article_id, statement, evidence_span, amount=None, currency=None,
                 unit=None, basis=None, period=None):
    """Build one hand-verified claim record with the same contract as an extracted one.

    For a qualitative claim (amount is None), currency/unit/basis/period may stay None -- the
    contract only requires them together for a numeric claim. `evidence_span` must still be a
    verbatim substring of the body the reviewer can find; this function does not check that
    itself, so callers should pass the substring they actually copied from the source.
    """
    claim = {"claim_id": claim_id, "statement": statement, "article_id": article_id,
             "evidence_span": evidence_span, "amount": amount, "currency": currency,
             "unit": unit, "basis": basis, "period": period}
    if amount is not None and not all(claim[field] is not None for field in REQUIRED_NUMERIC_FIELDS):
        raise ValueError("A numeric claim needs currency, unit, basis and period")
    return claim


def claims_for_decision(decision, bodies_by_article_id, basis="as reported"):
    """Build grounded claims for every article behind one shortlisted decision.

    `bodies_by_article_id` supplies the permitted evidence text this decision's articles were
    drawn from (e.g. read from work/phase2/evidence-store/). An article with no body yields no
    claims rather than a guessed one.
    """
    claims, index = [], 1
    for article_id in decision["article_ids"]:
        body = bodies_by_article_id.get(article_id)
        if not body:
            continue
        period = decision["event_identity"].get("period") or decision["event_identity"].get("event_date")
        extracted = extract_amount_claims(article_id, body, basis, period, start_index=index)
        claims.extend(extracted)
        index += len(extracted)
    return claims


__all__ = ["claims_for_decision", "extract_amount_claims", "manual_claim"]
