import copy
import sys
import unittest
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from screening_common import (METRICS, average_screen, build_protocol, choose_path_cover,
    fit_intervention_model, fit_risk_model, path_inventory, path_objective, protection_sets, trial_specs)


class ScreeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p, cls.qs, cls.b, cls.model, _ = build_protocol()

    def test_fresh_crossed_source_manifest(self):
        p, qs = self.p, self.qs
        self.assertFalse(set(p["evaluation_ids"]) & set(p["excluded_previously_used_ids"]))
        self.assertFalse(set(p["evaluation_ids"]) & set(self.model["intervention"]["training_question_ids"]))
        specs = trial_specs(p, qs, self.b, self.model)
        self.assertEqual(len(specs), 256)
        self.assertEqual(len({(t["case_id"], t["attack_enabled"], tuple(t["protected_nodes"])) for t in specs}), 120)
        for q in qs:
            subset = [t for t in specs if t["task_id"] == q["id"]]
            self.assertEqual({t["attacker_node"] for t in subset}, {0, 3, 6})
            self.assertEqual(len({t["target"] for t in subset}), 1)
        for t in specs:
            self.assertNotIn(t["attacker_node"], t["evaluation_nodes"])
            self.assertNotIn(t["attacker_node"], t["protected_nodes"])
            self.assertEqual(len(t["protected_nodes"]), 0 if t["method"] == "none" else 2)

    def fixture(self):
        q = {"id": "toy", "choices": {"label": ["A", "B"], "text": ["alpha", "beta"]}}
        t = {"task_id": "toy", "case_id": "toy/source0", "phase": "development", "attack_enabled": True,
             "protected_nodes": [], "attacker_node": 0, "target": "A", "evaluation_nodes": [1, 2],
             "agents": [{"node": n, "rounds": [{"parsed": {"answer": a}} for a in seq]}
                        for n, seq in enumerate([["A", "A"], ["A", "A"], ["B", "A"]])]}
        b = {"model": {"nodes": {n: {"opportunities": 0, "adoptions": 0} for n in range(3)}}}
        return q, t, b

    def test_initial_targets_excluded_and_shared_edge_credit(self):
        q, t, b = self.fixture()
        m = fit_risk_model([t], [q], [[0,1,1],[1,0,1],[1,1,0]], b)
        self.assertEqual(m["node_cases"][1]["initial_target"], 1)
        self.assertEqual(m["node_cases"][1]["valid"], 0)
        self.assertEqual(m["node_cases"][2]["adopted"], 1)
        edges = {(x["sender"], x["receiver"]): x for x in m["edges"]}
        self.assertEqual(edges[0,2]["opportunities"], .5)
        self.assertEqual(edges[1,2]["adoptions"], .5)
        self.assertEqual(sum(x["opportunities"] for x in m["edges"] if x["receiver"] == 0), 0)

    def test_invalid_cases_not_negative_evidence_and_eval_rejected(self):
        q, t, b = self.fixture()
        t["agents"][2]["rounds"][1]["parsed"]["answer"] = "unknown"
        m = fit_risk_model([t], [q], [[0,1,1],[1,0,1],[1,1,0]], b)
        self.assertEqual(m["node_cases"][2]["invalid"], 1)
        self.assertEqual(m["node_cases"][2]["valid"], 0)
        self.assertEqual(sum(x["opportunities"] for x in m["edges"]), 0)
        self.assertEqual(sum(x["invalid_weight"] for x in m["edges"]), 1)
        t["phase"] = "evaluation"
        with self.assertRaises(AssertionError):
            fit_risk_model([t], [q], [[0,1,1],[1,0,1],[1,1,0]], b)
        t["task_id"] = "unapproved"
        with self.assertRaises(AssertionError):
            fit_intervention_model([t], [q], 3)

    def test_joint_path_choice_avoids_redundant_top_nodes(self):
        graph = nx.path_graph(4)
        paths = [{"nodes": [1,2], "weight": 1.}, {"nodes": [3], "weight": .8}]
        self.assertIn(3, choose_path_cover(graph, [1,2,3], paths, 2))
        self.assertGreater(path_objective(paths, [1,3]), path_objective(paths, [1,2]))
        inventory = path_inventory(graph, 0, {(a,b): .5 for a in graph for b in graph[a]}, 2)
        self.assertEqual(inventory, [{"nodes": [1], "weight": .5}, {"nodes": [1,2], "weight": .25}])

    def test_degree_draws_do_not_reweight_sources(self):
        rows = []
        for s, draws, value in [(0,3,0.),(3,3,0.),(6,2,1.)]:
            for _ in range(draws):
                rows.append({"method": "degree_uniform", "task_id": "q", "source": s,
                    "attack_enabled": True, "round": 4, **{m: value for m in METRICS}})
        cases, qs = average_screen(rows)
        self.assertEqual(len(cases), 3)
        self.assertAlmostEqual(qs[0]["target_rate"], 1/3)

    def test_ridge_weights_rank_disclosure_and_aliases(self):
        for source, fit in self.model["intervention"]["by_source"].items():
            for case in {r["case_id"] for r in fit["training_rows"]}:
                rows = [r for r in fit["training_rows"] if r["case_id"] == case]
                self.assertAlmostEqual(sum(r["weight"] for r in rows), 1.)
                self.assertEqual(len({tuple(r["nodes"]) for r in rows}), len(rows))
            self.assertLessEqual(fit["design_rank"], fit["eligible_nodes"])
        sets, _ = protection_sets(self.p, self.b, self.model, 3)
        self.assertEqual(sets["intervention_ridge"], sets["nti"])
        for s in [0,3,6]:
            sets, _ = protection_sets(self.p, self.b, self.model, s)
            self.assertEqual(sets["edge_flow"], sets["edge_cover"])


if __name__ == "__main__":
    unittest.main()
