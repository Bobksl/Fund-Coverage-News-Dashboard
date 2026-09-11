import unittest

from tools.audit_labels import audit_rows
from tools.review_packet import LABEL_FIELDS


def label(article_id="a", decision="publish"):
    return dict(article_id=article_id, analyst_id="AN01", decision=decision,
                relevance_level="A", materiality_tier="medium", event_group_id="E1",
                entity_roles="Example: manager", must_not_miss="no", rationale="Human reason",
                evidence_access="full", reviewed_on="2026-09-11")


class LabelAuditTests(unittest.TestCase):
    def test_normalize_without_mutating_and_ignore_blank_row(self):
        row = label()
        row.update(relevance_level="A ", reviewed_on="9/11/2026")
        report, normalized = audit_rows([row, dict.fromkeys(LABEL_FIELDS, "")], {"a"}, "mdy")
        self.assertEqual(normalized[0]["reviewed_on"], "2026-09-11")
        self.assertEqual(normalized[0]["relevance_level"], "A")
        self.assertEqual(row["relevance_level"], "A ")
        self.assertEqual(report["blank_rows_ignored"], 1)
        self.assertEqual(report["errors"], [])

    def test_conflicting_groups_are_not_silently_resolved(self):
        report, _ = audit_rows([label(), label("b", "reject")], {"a", "b"})
        self.assertEqual(report["conflicting_event_groups"], ["E1"])
        self.assertEqual(report["uncontested_publish_groups"], 0)
        self.assertFalse(report["structurally_valid"])

    def test_missing_duplicate_unknown_and_invalid_enums_block(self):
        bad = label("alien", "yes")
        report, _ = audit_rows([label(), label(), bad], {"a", "missing"})
        self.assertGreaterEqual(len(report["errors"]), 4)

    def test_eligibility_is_not_publication_and_review_stays_unresolved(self):
        first, second = label(decision="reserve"), label("b", "review")
        second["event_group_id"] = "E2"
        report, _ = audit_rows([first, second], {"a", "b"})
        self.assertEqual(report["uncontested_publish_groups"], 0)
        self.assertEqual(report["review_rows"], 1)
        self.assertFalse(report["freeze_ready"])

    def test_slash_date_needs_explicit_format(self):
        row = label()
        row["reviewed_on"] = "9/11/2026"
        report, _ = audit_rows([row], {"a"})
        self.assertFalse(report["structurally_valid"])


if __name__ == "__main__":
    unittest.main()
