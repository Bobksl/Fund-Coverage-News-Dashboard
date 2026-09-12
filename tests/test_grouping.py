import unittest

from tools import grouping


def candidate(article_id, event_type="capital_formation", parties=("blue_owl",), vehicle=None,
              period=None, event_date="2026-09-01"):
    return {"article_id": article_id, "primary_event_type": event_type,
            "direct_entity_ids": list(parties),
            "event_identity": {"parties": list(parties), "action": event_type, "vehicle": vehicle,
                               "period": period, "event_date": event_date}}


def ids(clusters):
    return sorted(cluster["article_ids"] for cluster in clusters)


class RelationshipTests(unittest.TestCase):
    def test_identical_canonical_url_is_provenance_duplicate(self):
        evidence = {"a": {"canonical_url": "https://x.example/1"},
                    "b": {"canonical_url": "https://x.example/1"}}
        self.assertEqual(grouping.relationship(candidate("a"), candidate("b"), evidence), "duplicate")

    def test_same_named_vehicle_merges(self):
        first = candidate("a", vehicle="Example Credit Fund II")
        second = candidate("b", vehicle="example credit fund ii.")
        self.assertEqual(grouping.relationship(first, second), "same_event")

    def test_two_named_vehicles_never_merge_on_a_shared_manager(self):
        first = candidate("a", vehicle="Example Credit Fund II")
        second = candidate("b", vehicle="Example Credit Fund III")
        self.assertEqual(grouping.relationship(first, second), "distinct")

    def test_different_event_types_stay_distinct(self):
        self.assertEqual(grouping.relationship(candidate("a"), candidate("b", "credit_stress")),
                         "distinct")

    def test_no_shared_party_stays_distinct(self):
        self.assertEqual(grouping.relationship(candidate("a"), candidate("b", parties=("cifc",))),
                         "distinct")

    def test_shared_party_and_action_without_identifier_is_ambiguous(self):
        first = candidate("a", event_date="2026-09-01")
        second = candidate("b", event_date="2026-09-04")
        self.assertEqual(grouping.relationship(first, second), "ambiguous")

    def test_correction_links_to_the_article_it_supersedes(self):
        evidence = {"b": {"supersedes_article_id": "a"}}
        first = candidate("a", event_date="2026-09-01")
        second = candidate("b", event_type="credit_stress", parties=("cifc",), event_date="2026-09-09")
        self.assertEqual(grouping.relationship(first, second, evidence), "same_event")


class GroupingTests(unittest.TestCase):
    def test_clusters_are_deterministic_and_independent_of_input_order(self):
        proposals = [candidate("a", vehicle="Fund II"), candidate("b", vehicle="Fund II"),
                     candidate("c", parties=("cifc",), event_type="ratings")]
        forward = grouping.group(proposals)
        backward = grouping.group(list(reversed(proposals)))
        self.assertEqual(ids(forward), [["a", "b"], ["c"]])
        self.assertEqual([c["cluster_id"] for c in forward], [c["cluster_id"] for c in backward])

    def test_ambiguous_pair_stays_split_and_is_flagged_for_review(self):
        clusters = grouping.group([candidate("a", event_date="2026-09-01"),
                                   candidate("b", event_date="2026-09-04")])
        self.assertEqual(ids(clusters), [["a"], ["b"]])
        self.assertTrue(all(cluster["ambiguous_with"] for cluster in clusters))

    def test_duplicate_articles_share_one_event_and_keep_both_ids(self):
        evidence = {"a": {"canonical_url": "https://x.example/1"},
                    "b": {"canonical_url": "https://x.example/1"}}
        clusters = grouping.group([candidate("a"), candidate("b")], evidence)
        self.assertEqual(ids(clusters), [["a", "b"]])
        self.assertEqual(clusters[0]["duplicate_article_ids"], ["b"])

    def test_cluster_id_does_not_encode_analyst_information(self):
        cluster = grouping.group([candidate("a")])[0]
        self.assertTrue(cluster["cluster_id"].startswith("pe-"))
        self.assertNotIn("blue_owl", cluster["cluster_id"])

    def test_transitive_merge_joins_a_three_article_event(self):
        proposals = [candidate("a", vehicle="Fund II"), candidate("b", vehicle="Fund II"),
                     candidate("c", vehicle="Fund II")]
        self.assertEqual(ids(grouping.group(proposals)), [["a", "b", "c"]])


if __name__ == "__main__":
    unittest.main()
