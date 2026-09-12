"""Predicted event grouping from pipeline output only.

Analyst event-group IDs never enter this module. Exact URL/content duplicates are provenance, not
semantic clustering. Where identity is genuinely ambiguous the candidates stay separate and are
flagged for review rather than merged, so a false merge cannot be credited as a success.
"""
import hashlib
import re

PUNCTUATION = re.compile(r"[^\w\s]+")
WHITESPACE = re.compile(r"\s+")
DATE_WINDOW_DAYS = 0  # Without a vehicle or deal identifier, only an identical date may merge.


def normalize(value):
    if not value:
        return ""
    return WHITESPACE.sub(" ", PUNCTUATION.sub(" ", str(value).lower())).strip()


def _parties(proposal):
    direct = {normalize(value) for value in proposal.get("direct_entity_ids") or []}
    named = {normalize(value) for value in (proposal.get("event_identity") or {}).get("parties") or []}
    return {value for value in direct | named if value}


def _vehicle(proposal):
    return normalize((proposal.get("event_identity") or {}).get("vehicle"))


def _period(proposal):
    return normalize((proposal.get("event_identity") or {}).get("period"))


def _event_date(proposal):
    return (proposal.get("event_identity") or {}).get("event_date")


def relationship(first, second, evidence=None):
    """Return duplicate, same_event, ambiguous or distinct for one candidate pair."""
    evidence = evidence or {}
    left = evidence.get(first["article_id"], {})
    right = evidence.get(second["article_id"], {})
    if left.get("canonical_url") and left["canonical_url"] == right.get("canonical_url"):
        return "duplicate"
    if left.get("evidence_hash") and left["evidence_hash"] == right.get("evidence_hash"):
        return "duplicate"
    if right.get("supersedes_article_id") == first["article_id"] or \
            left.get("supersedes_article_id") == second["article_id"]:
        return "same_event"
    if first["primary_event_type"] != second["primary_event_type"]:
        return "distinct"
    if not _parties(first) & _parties(second):
        return "distinct"
    vehicles = (_vehicle(first), _vehicle(second))
    if all(vehicles):
        # Two named vehicles that differ are two deals, however similar the headlines look.
        return "same_event" if vehicles[0] == vehicles[1] else "distinct"
    if _period(first) and _period(first) == _period(second):
        return "same_event"
    dates = (_event_date(first), _event_date(second))
    if all(dates) and dates[0] == dates[1]:
        return "same_event"
    # Shared party and action but no distinguishing identifier: unresolved, never silently merged.
    return "ambiguous"


def cluster_id(article_ids):
    digest = hashlib.sha256("|".join(sorted(article_ids)).encode("utf-8")).hexdigest()[:12]
    return f"pe-{digest}"


def group(proposals, evidence=None):
    """Return deterministic predicted clusters plus the ambiguous pairs that need review."""
    parent = {proposal["article_id"]: proposal["article_id"] for proposal in proposals}

    def find(article_id):
        while parent[article_id] != article_id:
            parent[article_id] = parent[parent[article_id]]
            article_id = parent[article_id]
        return article_id

    duplicates, ambiguous = [], []
    ordered = sorted(proposals, key=lambda proposal: proposal["article_id"])
    for index, first in enumerate(ordered):
        for second in ordered[index + 1:]:
            verdict = relationship(first, second, evidence)
            if verdict in {"duplicate", "same_event"}:
                parent[find(second["article_id"])] = find(first["article_id"])
                if verdict == "duplicate":
                    duplicates.append([first["article_id"], second["article_id"]])
            elif verdict == "ambiguous":
                ambiguous.append([first["article_id"], second["article_id"]])

    members = {}
    for proposal in ordered:
        members.setdefault(find(proposal["article_id"]), []).append(proposal)
    clusters = []
    for group_members in members.values():
        article_ids = sorted(member["article_id"] for member in group_members)
        unresolved = sorted({pair[0] for pair in ambiguous if pair[1] in article_ids}
                            | {pair[1] for pair in ambiguous if pair[0] in article_ids})
        clusters.append({
            "cluster_id": cluster_id(article_ids),
            "article_ids": article_ids,
            "members": sorted(group_members, key=lambda member: member["article_id"]),
            "duplicate_article_ids": sorted({article for pair in duplicates
                                             for article in pair if article in article_ids[1:]}),
            "ambiguous_with": [article for article in unresolved if article not in article_ids],
        })
    return sorted(clusters, key=lambda cluster: cluster["cluster_id"])
