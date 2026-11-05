"""Data separation, recipient scores, allocation and budget comparison rules."""

import copy
import sys
import unittest
from collections import Counter
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from protection_common import (METRICS, average_within_question, build_protocol, coverage_subset,
    degree_subsets, fit_vulnerability, nested_random_sets, protection_sets, trial_specs)
from placement_common import graph_from_adjacency


class ProtectionExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.questions, cls.behavior, cls.vulnerability = build_protocol()

    def test_fresh_questions_and_balanced_sources(self):
        p = self.protocol
        self.assertEqual(len(p["evaluation_ids"]), 12)
        self.assertEqual(len(set(p["evaluation_ids"])), 12)
        self.assertEqual(len(p["excluded_previously_used_ids"]), 50)
        self.assertFalse(set(p["evaluation_ids"]) & set(p["excluded_previously_used_ids"]))
        self.assertEqual(Counter(p["evaluation_source_by_task"].values()), {0: 4, 3: 4, 6: 4})
        self.assertEqual(p, build_protocol()[0])

    def test_vulnerability_counts_only_valid_honest_post_initial_cases(self):
        q = {"id": "q", "choices": {"label": ["A", "B", "C"], "text": ["a", "b", "c"]}}
        t = {"phase": "development", "task_id": "q", "attack_enabled": True, "protected_nodes": [],
             "attacker_node": 0, "target": "C", "agents": [
                 {"node": n, "rounds": [{"parsed": {"answer": a}} for a in answers]}
                 for n, answers in enumerate([["C", "C", "C"], ["A", "C", "A"], ["A", "invalid", "C"], ["C", "A", "A"]])]}
        fitted = fit_vulnerability([t], [q], 4)["nodes"]
        self.assertEqual(fitted[0]["valid_cases"], 0)
        self.assertEqual(fitted[1]["affected_cases"], 1)
        self.assertEqual(fitted[2]["invalid_cases"], 1)
        self.assertEqual(fitted[2]["valid_cases"], 0)
        self.assertEqual(fitted[3]["score"], 0)
        invalid = copy.deepcopy(t); invalid["phase"] = "evaluation"
        with self.assertRaises(AssertionError):
            fit_vulnerability([invalid], [q], 4)

    def test_source_aware_and_coverage_controls(self):
        graph = nx.path_graph(4)
        self.assertEqual(coverage_subset(graph, [1, 2, 3], 1), [2])
        self.assertEqual(coverage_subset(graph, [1, 2, 3], 2), [1, 2])
        p = self.protocol
        selections = protection_sets(p, self.behavior, self.vulnerability, 0)
        self.assertEqual(selections["k2/nti"], [4, 6])
        self.assertEqual(selections["k3/nti"], [4, 6, 7])
        for source in p["attacker_positions"]:
            sets = protection_sets(p, self.behavior, self.vulnerability, source)
            for name, nodes in sets.items():
                self.assertNotIn(source, nodes)
                if name.startswith("k"):
                    self.assertEqual(len(set(nodes)), int(name[1]))
            g = graph_from_adjacency(p["adjacency"])
            for k in p["budgets"]:
                expected = degree_subsets(g, [n for n in g if n != source], k)
                actual = [v for n, v in sets.items() if n.startswith(f"k{k}/degree_tie_")]
                self.assertEqual(actual, expected)

    def test_random_budget_prefixes_are_nested_and_distinct(self):
        sampled = nested_random_sets(list(range(7)), [2, 3], 3, 20261107)
        for small, large in zip(sampled[2], sampled[3]):
            self.assertLess(set(small), set(large))
        for k in [2, 3]:
            self.assertEqual(len({tuple(x) for x in sampled[k]}), 3)
        self.assertEqual(sampled, nested_random_sets(list(range(7)), [2, 3], 3, 20261107))

    def test_averaging_keeps_budgets_and_questions_separate(self):
        rows = []
        for k, task, values in [(2, "a", [0, 0, 1]), (2, "b", [1, 1]), (3, "a", [0])]:
            for i, value in enumerate(values):
                rows.append({"strategy": f"k{k}/degree_tie_{i}", "task_id": task, "attack_enabled": True,
                             "source": 0, "round": 4, **{m: value for m in METRICS}})
        result = average_within_question(rows)
        k2 = [r for r in result if r["budget"] == 2]
        self.assertEqual(len(k2), 2)
        self.assertAlmostEqual(sum(r["target_rate"] for r in k2)/2, 2/3)
        self.assertEqual([r["target_rate"] for r in result if r["budget"] == 3], [0])

    def test_complete_manifest_and_alias_count(self):
        specs = trial_specs(self.protocol, self.questions, self.behavior, self.vulnerability)
        self.assertEqual(len(specs), 600)
        self.assertEqual(len({t["trial_id"] for t in specs}), 600)
        self.assertEqual(len({(t["case_id"], t["attack_enabled"], tuple(t["protected_nodes"])) for t in specs}), 432)
        self.assertEqual(set(Counter((t["case_id"], t["strategy"]) for t in specs).values()), {2})


if __name__ == "__main__":
    unittest.main()
