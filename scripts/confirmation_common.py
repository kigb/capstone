"""Frozen 30-question confirmation design and degree-tie averaging helpers."""

import ast
import gzip
import hashlib
import itertools
import json
import random
import shutil
from pathlib import Path

from placement_common import fit_behavior, graph_from_adjacency, placement_sets


ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / "results/netsafe_placement_qwen8b"
QUESTION_FILES = [
    "results/netsafe_placement_qwen8b/development_questions.json",
    "results/netsafe_placement_qwen8b/evaluation_questions.json",
    "results/netsafe_qwen3b_baseline/questions.json",
    "results/netsafe_qwen3b_pilot/questions.json",
    "results/netsafe_qwen8b_baseline/questions.json",
    "results/netsafe_qwen8b_round4_pilot/questions.json",
]
METRICS = ("accuracy", "target_rate", "invalid_rate", "system_correct",
           "system_target", "no_majority", "ever_target_rate")
STRATEGIES = ["none", "random", "degree", "degree_uniform", "betweenness", "behavior", "all"]


def read_json(path):
    return json.loads(path.read_text())


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_records(path):
    actual = path if path.exists() else path.with_suffix(path.suffix + ".gz")
    opener = gzip.open if actual.suffix == ".gz" else open
    with opener(actual, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def archive_jsonl(path):
    """Preserve exact JSONL bytes in a deterministic gzip, then remove plaintext."""
    target = path.with_suffix(path.suffix + ".gz")
    if not path.exists():
        assert target.exists()
        return target
    temporary = target.with_suffix(target.suffix + ".tmp")
    expected = file_hash(path)
    with path.open("rb") as source, temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as dest:
            shutil.copyfileobj(source, dest)
    with gzip.open(temporary, "rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == expected
    temporary.replace(target)
    path.unlink()
    return target


def restore_jsonl(path):
    compressed = path.with_suffix(path.suffix + ".gz")
    if not path.exists() and compressed.exists():
        temporary = path.with_suffix(path.suffix + ".restore")
        with gzip.open(compressed, "rb") as source, temporary.open("wb") as dest:
            shutil.copyfileobj(source, dest)
        temporary.replace(path)


def degree_tie_sets(protocol, source):
    degree = dict(graph_from_adjacency(protocol["adjacency"]).degree())
    eligible = [n for n in degree if n != source]
    optimum = sum(sorted((degree[n] for n in eligible), reverse=True)[:protocol["budget"]])
    return [list(s) for s in itertools.combinations(eligible, protocol["budget"])
            if sum(degree[n] for n in s) == optimum]


def confirmation_sets(protocol, behavior, source):
    sets = placement_sets(protocol, behavior, source)
    sets.update({f"degree_tie_{i}": subset for i, subset in enumerate(degree_tie_sets(protocol, source))})
    return sets


def strategy_group(name):
    if name.startswith("random_"):
        return "random"
    if name.startswith("degree_tie_"):
        return "degree_uniform"
    return name


def average_within_question(rows):
    groups = {}
    for row in rows:
        key = (strategy_group(row["strategy"]), row["attack_enabled"], row["case_id"], row["round"])
        groups.setdefault(key, []).append(row)
    return [{"strategy": strategy, "attack_enabled": attacked, "case_id": case_id,
             "task_id": items[0]["task_id"], "attacker_node": items[0]["attacker_node"],
             "round": r, "draws": len(items),
             **{name: sum(x[name] for x in items) / len(items) for name in METRICS}}
            for (strategy, attacked, case_id, r), items in groups.items()]


def build_protocol():
    prior = read_json(PRIOR / "protocol.json")
    prior_runtime = read_json(PRIOR / "summary_runtime.json")
    frozen = read_json(PRIOR / "behavior_model.json")
    assert digest(prior) == prior_runtime["protocol_sha256"] == frozen["protocol_sha256"]
    assert file_hash(PRIOR / "behavior_model.json") == prior_runtime["behavior_model_sha256"]
    assert file_hash(PRIOR / "development.jsonl") == frozen["development_sha256"]
    development = read_records(PRIOR / "development.jsonl")
    refitted = fit_behavior(development, read_json(PRIOR / "development_questions.json"),
                            prior["adjacency"], prior["minimum_behavior_opportunities"])
    assert json.loads(json.dumps(refitted)) == frozen["model"]
    used = {q["id"] for filename in QUESTION_FILES for q in read_json(ROOT / filename)}
    dataset = ROOT / "third_party/NetSafe/dataset/csqa.jsonl"
    assert file_hash(dataset) == prior["dataset_sha256"]
    rows = [ast.literal_eval(line) for line in dataset.read_text().splitlines() if line.strip()]
    valid = [q for q in rows if q["answerKey"] in q["choices"]["label"]]
    assert len({q["id"] for q in valid}) == len(valid)
    unseen = [q for q in valid if q["id"] not in used]
    questions = random.Random(20261120).sample(unseen, 30)
    target_rng = random.Random(20261121)
    sources = prior["attacker_positions"]
    artifact_names = QUESTION_FILES + ["results/netsafe_placement_qwen8b/" + n for n in
                                     ("protocol.json", "behavior_model.json", "development.jsonl", "summary_runtime.json")]
    protocol = {**prior,
        "study": "netsafe_placement_confirmation_qwen8b_v2",
        "parent_protocol_sha256": digest(prior),
        "prior_artifact_sha256": {name: file_hash(ROOT / name) for name in artifact_names},
        "excluded_previously_used_ids": sorted(used),
        "dataset_valid_questions": len(valid), "unseen_question_pool_size": len(unseen),
        "evaluation_ids": [q["id"] for q in questions],
        "evaluation_targets": {q["id"]: target_rng.choice([a for a in q["choices"]["label"] if a != q["answerKey"]]) for q in questions},
        "evaluation_source_by_task": {q["id"]: sources[i % len(sources)] for i, q in enumerate(questions)},
        "split_seed": 20261120, "evaluation_target_seed": 20261121,
        "development_design": "Reuse the unchanged prior development trajectories and frozen behavior scores. No new development inference or use of earlier evaluation outcomes in score fitting.",
        "evaluation_design": "30 previously unused questions; one prescribed source each, 10 per source. All original placement strategies plus every degree-optimal size-two subset, paired clean/attack. Duplicate placement aliases share exact cached responses.",
        "degree_tie_rule": "Enumerate all eligible degree-optimal k-subsets. Uniformly average their outcomes WITHIN each question, then equally average questions; never pool unequal numbers of tied subsets across sources.",
        "primary_comparison": {"candidate": "behavior", "reference": "degree_uniform",
                               "attack_enabled": True, "round": 4, "metric": "target_rate", "lower_is_better": True},
        "analysis_rule": "One prespecified primary comparison. 10,000 paired question bootstrap draws, seed 20261120; secondary comparisons descriptive without multiplicity correction. Random and degree-tied subsets averaged within question before bootstrap. Same questions/nodes/rounds/aliases are not independent samples. No optional stopping on outcomes.",
        "bootstrap_replicates": 10000, "bootstrap_seed": 20261120,
        "cache_policy": "Fresh cache for the 30 new questions; identical system/user inputs within this protocol share one greedy generation. Archived JSONL gzip preserves exact bytes.",
    }
    assert len(questions) == 30 and not used.intersection(protocol["evaluation_ids"])
    return protocol, questions, frozen, refitted


def trial_specs(protocol, questions, behavior):
    specs = []
    for q in questions:
        source = protocol["evaluation_source_by_task"][q["id"]]
        for strategy, protected in confirmation_sets(protocol, behavior, source).items():
            for attacked in (False, True):
                specs.append({"phase": "evaluation", "case_id": f"{q['id']}/source{source}",
                    "trial_id": f"evaluation/{q['id']}/source{source}/{strategy}/{'attack' if attacked else 'clean'}",
                    "task_id": q["id"], "gold": q["answerKey"], "target": protocol["evaluation_targets"][q["id"]],
                    "attacker_node": source, "attack_enabled": attacked,
                    "evaluation_nodes": [n for n in range(protocol["num_agents"]) if n != source],
                    "strategy": strategy, "protected_nodes": protected})
    return specs
