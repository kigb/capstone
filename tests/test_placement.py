"""Checks for leakage, exposure attribution, and matched protection budgets."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from netsafe_metrics import evaluate, label
from placement_common import fit_behavior, graph_from_adjacency, placement_sets, select_graph
from analyze_placement_study import average_random_draws, average_ranks


QUESTION = {"id": "fixture", "choices": {"label": ["A", "B", "C"], "text": ["gold", "target", "other"]}}


def trajectory(answers, source=0, phase="development"):
    return {"phase": phase, "task_id": "fixture", "case_id": "fixture/source0", "target": "B",
            "attacker_node": source, "attack_enabled": True, "protected_nodes": [],
            "evaluation_nodes": [n for n in range(len(answers)) if n != source],
            "agents": [{"node": node, "rounds": [{"parsed": {"answer": answer}} for answer in rounds]}
                       for node, rounds in enumerate(answers)]}


class PlacementTests(unittest.TestCase):
    def test_shared_exposure_and_attacker_exclusion(self):
        # Both source 0 and naturally affected node 1 send B to node 2.
        adjacency = [[0, 0, 1], [0, 0, 1], [1, 1, 0]]
        data = trajectory([["B", "B"], ["B", "B"], ["A", "B"]])
        model = fit_behavior([data], [QUESTION], adjacency, minimum_opportunities=.5)
        self.assertEqual(model["nodes"][0]["opportunities"], 0)
        self.assertEqual(model["nodes"][1]["opportunities"], .5)
        self.assertEqual(model["nodes"][1]["adoptions"], .5)
        self.assertEqual(model["events"][0]["all_target_senders"], [0, 1])

    def test_invalid_states_are_not_negative_adoption_evidence(self):
        adjacency = [[0, 0, 0], [0, 0, 1], [0, 1, 0]]
        for previous, current, invalid_weight in [(None, "B", 0), ("A", None, 1), ("B", "B", 0)]:
            model = fit_behavior([trajectory([["B", "B"], ["B", "B"], [previous, current]])], [QUESTION], adjacency)
            self.assertEqual(model["nodes"][1]["opportunities"], 0)
            self.assertEqual(model["nodes"][1]["invalid_weight"], invalid_weight)

    def test_evaluation_data_rejected_for_fitting(self):
        with self.assertRaises(AssertionError):
            fit_behavior([trajectory([["B", "B"], ["A", "B"]], phase="evaluation")], [QUESTION], [[0, 1], [1, 0]])

    def test_graph_and_budget_controls(self):
        graph = select_graph()
        self.assertEqual(graph["selected_seed"], 20261107)
        self.assertEqual(len(graph_from_adjacency(graph["adjacency"])), 8)
        protocol = {"num_agents": 8, "adjacency": graph["adjacency"], "budget": 2,
                    "random_draws": 3, "random_placement_seed": 20261105}
        insufficient = {"informative": False}
        for source in [0, 3, 6]:
            sets = placement_sets(protocol, insufficient, source)
            self.assertEqual(sets["behavior"], sets["degree"])
            self.assertNotEqual(sets["degree"], sets["betweenness"])
            self.assertEqual(sets["none"], [])
            self.assertEqual(len(sets["all"]), 7)
            for name, nodes in sets.items():
                self.assertNotIn(source, nodes)
                if name not in {"none", "all"}: self.assertEqual(len(set(nodes)), 2)
            self.assertEqual(len({tuple(sets[f"random_{i}"]) for i in range(3)}), 3)
            self.assertEqual(sets, placement_sets(protocol, insufficient, source))

    def test_rate_ranking_uses_supported_behavior(self):
        graph = select_graph()
        protocol = {"num_agents": 8, "adjacency": graph["adjacency"], "budget": 2,
                    "random_draws": 3, "random_placement_seed": 20261105}
        behavior = {"informative": True, "nodes": {n: {"placement_score": .1} for n in range(8)}}
        behavior["nodes"][3]["placement_score"] = .9
        behavior["nodes"][7]["placement_score"] = .8
        self.assertEqual(placement_sets(protocol, behavior, 0)["behavior"], [3, 7])

    def test_scoring_and_strict_majority(self):
        self.assertIsNone(label("An answer"))
        self.assertEqual(label("target", QUESTION["choices"]), "B")
        score = evaluate(["B", "B", "B", "A", "A", "A", None], "A", "B")
        self.assertEqual(score["invalid"], 1)
        self.assertIsNone(score["majority"])
        self.assertEqual(score["system_target"], 0)

    def test_random_draws_average_within_task(self):
        rows = []
        for task, values in [("one", [0, 0, 1]), ("two", [1, 1, 1])]:
            for draw, value in enumerate(values):
                rows.append({"strategy": f"random_{draw}", "attack_enabled": True,
                             "case_id": task, "task_id": task, "round": 4, "attacker_node": 0,
                             **{key: value for key in ["accuracy", "target_rate", "invalid_rate", "system_correct", "system_target", "no_majority", "ever_target_rate"]}})
        result = average_random_draws(rows)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]["accuracy"], 1 / 3)
        self.assertEqual(result[0]["draws"], 3)
        self.assertAlmostEqual(sum(r["accuracy"] for r in result) / 2, 2 / 3)
        self.assertEqual(average_ranks([1, 1, 3]), [1.5, 1.5, 3])


if __name__ == "__main__":
    unittest.main()
