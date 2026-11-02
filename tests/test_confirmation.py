"""Checks for the new split, exact degree ties, and task-level weighting."""

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from confirmation_common import (
    METRICS, archive_jsonl, average_within_question, build_protocol,
    confirmation_sets, degree_tie_sets, read_records, restore_jsonl, trial_specs,
)


class ConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.questions, cls.frozen, cls.behavior = build_protocol()

    def test_new_questions_exclude_every_previous_split(self):
        p = self.protocol
        self.assertEqual(len(set(p["evaluation_ids"])), 30)
        self.assertFalse(set(p["evaluation_ids"]) & set(p["excluded_previously_used_ids"]))
        self.assertEqual(Counter(p["evaluation_source_by_task"].values()), {0: 10, 3: 10, 6: 10})
        for q in self.questions:
            self.assertNotEqual(p["evaluation_targets"][q["id"]], q["answerKey"])
        self.assertEqual(p, build_protocol()[0])

    def test_all_optimal_ties_and_aliases_are_present(self):
        for source, expected in [(0, [[1, 2], [2, 4], [2, 6]]),
                                 (3, [[1, 2], [2, 4], [2, 6]]),
                                 (6, [[1, 2], [2, 4]])]:
            self.assertEqual(degree_tie_sets(self.protocol, source), expected)
            selections = confirmation_sets(self.protocol, self.behavior, source)
            self.assertEqual(selections["degree"], selections["degree_tie_0"])
            self.assertEqual(selections["behavior"], selections["degree_tie_1"])
            for name, nodes in selections.items():
                self.assertNotIn(source, nodes)
                if name not in {"none", "all"}:
                    self.assertEqual(len(set(nodes)), 2)

    def test_different_numbers_of_ties_do_not_reweight_questions(self):
        rows = []
        for task, values in [("three_ties", [0, 0, 1]), ("two_ties", [1, 1])]:
            for i, value in enumerate(values):
                rows.append({"strategy": f"degree_tie_{i}", "case_id": task, "task_id": task,
                             "attack_enabled": True, "round": 4, "attacker_node": 0,
                             **{metric: value for metric in METRICS}})
        averaged = average_within_question(rows)
        self.assertEqual({r["strategy"] for r in averaged}, {"degree_uniform"})
        self.assertEqual([r["draws"] for r in averaged], [3, 2])
        self.assertAlmostEqual(sum(r["target_rate"] for r in averaged) / 2, 2 / 3)
        self.assertNotAlmostEqual(sum(r["target_rate"] for r in averaged) / 2, 3 / 5)

    def test_manifest_counts_and_clean_attack_pairs(self):
        specs = trial_specs(self.protocol, self.questions, self.behavior)
        self.assertEqual(len(specs), 640)
        self.assertEqual(len({t["trial_id"] for t in specs}), 640)
        self.assertEqual(len({(t["case_id"], t["attack_enabled"], tuple(t["protected_nodes"])) for t in specs}), 480)
        pairs = Counter((t["case_id"], t["strategy"]) for t in specs)
        self.assertEqual(set(pairs.values()), {2})

    def test_archiving_preserves_raw_bytes_and_can_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.jsonl"
            raw = (json.dumps({"example": "中文"}, ensure_ascii=False) + "\n").encode()
            path.write_bytes(raw)
            archive = archive_jsonl(path)
            self.assertFalse(path.exists())
            self.assertEqual(read_records(path), [{"example": "中文"}])
            first = archive.read_bytes()
            restore_jsonl(path)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(archive_jsonl(path).read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
