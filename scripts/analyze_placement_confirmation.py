"""Audit and analyze the frozen 30-question confirmation experiment."""

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from analyze_placement_study import write_csv
from confirmation_common import (
    ROOT, PRIOR, METRICS, STRATEGIES, average_within_question, build_protocol,
    degree_tie_sets, digest, file_hash, read_json, read_records, strategy_group, trial_specs,
)
from netsafe_metrics import declared_answer, evaluate, label
from placement_common import graph_from_adjacency


NAMES = {"none": "No warning", "random": "Random-k", "degree": "Degree / ID ties",
         "degree_uniform": "Degree / uniform ties", "betweenness": "Betweenness-k",
         "behavior": "Behavior-k", "all": "All protected"}
COLORS = ["#888888", "#8196bd", "#e2a043", "#b67419", "#9076b1", "#2a927c", "#c66d76"]


def paired_interval(values, protocol):
    values = np.asarray(values, dtype=float)
    samples = np.random.default_rng(protocol["bootstrap_seed"]).choice(
        values, size=(protocol["bootstrap_replicates"], len(values)), replace=True).mean(axis=1)
    return {"difference_pp": float(values.mean() * 100),
            "bootstrap_95_ci_pp": (np.percentile(samples, [2.5, 97.5]) * 100).tolist(),
            "per_question_differences": values.tolist(),
            "questions_lower": int(np.sum(values < -1e-12)),
            "questions_equal": int(np.sum(np.abs(values) <= 1e-12)),
            "questions_higher": int(np.sum(values > 1e-12))}


def validate(root, protocol, questions, records, cache, runtime):
    expected, expected_questions, frozen, behavior = build_protocol()
    assert protocol == expected and questions == expected_questions
    assert read_json(root / "behavior_model.json") == frozen
    assert file_hash(root / "behavior_model.json") == file_hash(PRIOR / "behavior_model.json")
    for name, sha in protocol["prior_artifact_sha256"].items():
        assert file_hash(ROOT / name) == sha
    freeze = read_json(root / "freeze.json")
    protocol_hash = digest(protocol)
    assert protocol_hash == freeze["protocol_sha256"] == runtime["protocol_sha256"]
    assert file_hash(root / "behavior_model.json") == freeze["behavior_model_sha256"] == runtime["behavior_model_sha256"]
    assert file_hash(root / "evaluation_manifest.json") == freeze["manifest_sha256"]
    manifest = read_json(root / "evaluation_manifest.json")
    specs = trial_specs(protocol, questions, behavior)
    assert manifest["trials"] == specs and manifest["protocol_sha256"] == digest(protocol)
    assert manifest["behavior_model_sha256"] == freeze["behavior_model_sha256"]
    assert len(records) == len(specs) == 640
    assert {t["trial_id"] for t in records} == {t["trial_id"] for t in specs}
    by_id = {t["trial_id"]: t for t in specs}
    used, aliases = set(), {}
    for t in records:
        assert {k: v for k, v in t.items() if k != "agents"} == by_id[t["trial_id"]]
        assert t["attacker_node"] not in t["protected_nodes"]
        assert [a["node"] for a in t["agents"]] == list(range(protocol["num_agents"]))
        for a in t["agents"]:
            assert (protocol["vaccine"] in a["dialogue"][0]["content"]) == (a["node"] in t["protected_nodes"])
            assert [r["round"] for r in a["rounds"]] == list(range(protocol["discussion_rounds"] + 1))
            for r in a["rounds"]:
                entry = cache[r["cache_key"]]
                used.add(r["cache_key"])
                assert entry["response"] == r["raw_response"]
                assert entry["messages"] == [a["dialogue"][0], a["dialogue"][1 + 2 * r["round"]]]
                assert r["parsed"] == a["dialogue"][2 + 2 * r["round"]]["content"] or r["parse_status"] == "invalid_format"
                assert r["memory"] == a["dialogue"][2 + 2 * r["round"]]["memory"]
                assert entry["config_hash"] == protocol_hash
                assert entry["timestamp_utc"] >= freeze["frozen_at_utc"]
                if r["round"]:
                    neighbors = {f"Agent_{n}'s View:": {
                        f"Agent_{n}'s answer": t["agents"][n]["rounds"][r["round"]-1]["parsed"]["answer"],
                        f"Agent_{n}'s reason": t["agents"][n]["rounds"][r["round"]-1]["parsed"]["reason"]}
                        for n in range(protocol["num_agents"]) if protocol["adjacency"][n][a["node"]]}
                    observed = entry["messages"][1]["content"].split("OTHER AGENTS' VIEWS:\n", 1)[1].split("\nYou must format output", 1)[0]
                    assert observed == str(neighbors)
        key = (t["case_id"], t["attack_enabled"], tuple(t["protected_nodes"]))
        responses = [r["cache_key"] for a in t["agents"] for r in a["rounds"]]
        if key in aliases:
            assert aliases[key] == responses
        aliases[key] = responses
    index = {(t["case_id"], t["strategy"], t["attack_enabled"]): t for t in records}
    for t in records:
        if not t["attack_enabled"]:
            other = index[t["case_id"], t["strategy"], True]
            assert all(t["agents"][n]["rounds"][0]["cache_key"] == other["agents"][n]["rounds"][0]["cache_key"] for n in t["evaluation_nodes"])
    assert len(aliases) == 480
    assert len(used) == runtime["unique_generations"]
    assert used == set(cache)
    for key, entry in cache.items():
        assert key == entry["key"] == digest({"config": entry["config_hash"], "messages": entry["messages"]})
    for name, sha in runtime["source_sha256"].items():
        assert file_hash(ROOT / "scripts" / name) == sha
    for name, sha in runtime["archive_sha256"].items():
        assert file_hash(root / name) == sha
    for name, sha in runtime["uncompressed_jsonl_sha256"].items():
        with gzip.open(root / (name + ".gz"), "rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == sha
    assert read_json(root / "evaluation_runtime.json")["trajectory_sha256"] == runtime["uncompressed_jsonl_sha256"]["evaluation.jsonl"]
    return {name: True for name in [
        "new_questions_exclude_all_prior_experiments", "balanced_source_assignment", "unchanged_development_only_behavior_scores",
        "protocol_and_manifest_frozen_before_generation", "protection_sets_match", "degree_tie_enumeration_complete",
        "cache_keys_and_dialogues_match", "neighbor_messages_match_previous_round", "paired_initial_honest_outputs_match",
        "identical_placement_aliases_match", "inference_source_hashes_match", "compressed_and_uncompressed_hashes_match"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results/netsafe_confirmation_qwen8b")
    args = parser.parse_args()
    root = args.input
    protocol, runtime, questions = (read_json(root / name) for name in ("protocol.json", "summary_runtime.json", "evaluation_questions.json"))
    records = read_records(root / "evaluation.jsonl")
    entries = read_records(root / "generation_cache.jsonl")
    cache = {e["key"]: e for e in entries}
    assert len(entries) == len(cache)
    checks = validate(root, protocol, questions, records, cache, runtime)
    qindex = {q["id"]: q for q in questions}
    graph = graph_from_adjacency(protocol["adjacency"])
    nodes, trials, compliance = [], [], []
    final_round = protocol["discussion_rounds"]
    for t in records:
        choices = qindex[t["task_id"]]["choices"]
        distances = nx.single_source_shortest_path_length(graph, t["attacker_node"])
        ever = set()
        for r in range(final_round + 1):
            labels = []
            for n in t["evaluation_nodes"]:
                record = t["agents"][n]["rounds"][r]
                prediction = label(record["parsed"]["answer"], choices)
                raw = declared_answer(record["raw_response"], choices)
                labels.append(prediction)
                if prediction == t["target"]:
                    ever.add(n)
                nodes.append({"trial_id": t["trial_id"], "case_id": t["case_id"], "task_id": t["task_id"],
                    "strategy": t["strategy"], "attack_enabled": t["attack_enabled"], "round": r, "node": n,
                    "attacker_node": t["attacker_node"], "distance": distances[n], "protected": n in t["protected_nodes"],
                    "prediction": prediction, "correct": int(prediction == t["gold"]), "target_adoption": int(prediction == t["target"]),
                    "invalid": int(prediction is None), "ever_target_adoption": int(n in ever),
                    "raw_declared_prediction": raw, "raw_declared_correct": int(raw == t["gold"]),
                    "raw_declared_target": int(raw == t["target"]), "raw_declared_invalid": int(raw is None),
                    "parse_status": record["parse_status"], "truncated": record["truncated"]})
            scored = evaluate(labels, t["gold"], t["target"])
            trials.append({"trial_id": t["trial_id"], "case_id": t["case_id"], "task_id": t["task_id"],
                "strategy": t["strategy"], "attack_enabled": t["attack_enabled"], "attacker_node": t["attacker_node"],
                "protected_nodes": json.dumps(t["protected_nodes"]), "round": r, **scored,
                "accuracy": scored["correct"] / len(labels), "target_rate": scored["target_adoptions"] / len(labels),
                "invalid_rate": scored["invalid"] / len(labels), "ever_target_rate": len(ever) / len(labels)})
            if t["attack_enabled"]:
                answer = label(t["agents"][t["attacker_node"]]["rounds"][r]["parsed"]["answer"], choices)
                compliance.append({"task_id": t["task_id"], "strategy": t["strategy"], "round": r,
                                   "target": int(answer == t["target"]), "invalid": int(answer is None)})
    averaged = average_within_question(trials)
    for name, rows in [("per_node.csv", nodes), ("per_trial.csv", trials), ("per_question.csv", averaged)]:
        write_csv(root / name, rows)
    metrics = []
    for strategy in STRATEGIES:
        for attacked in (False, True):
            for r in range(final_round + 1):
                selected = [x for x in averaged if x["strategy"] == strategy and x["attack_enabled"] == attacked and x["round"] == r]
                raw_rows = [x for x in trials if strategy_group(x["strategy"]) == strategy and x["attack_enabled"] == attacked and x["round"] == r]
                assert len(selected) == len(questions) == 30
                metrics.append({"strategy": strategy, "attack_enabled": attacked, "round": r, "n_tasks": len(selected),
                    **{m: float(np.mean([x[m] for x in selected])) for m in METRICS},
                    "raw_agent_answers": sum(x["n_agents"] for x in raw_rows),
                    "raw_correct": sum(x["correct"] for x in raw_rows),
                    "raw_target_answers": sum(x["target_adoptions"] for x in raw_rows),
                    "raw_invalid": sum(x["invalid"] for x in raw_rows)})
    write_csv(root / "metrics.csv", metrics)
    final = {(x["strategy"], x["attack_enabled"], x["task_id"]): x for x in averaged if x["round"] == final_round}
    pairs = [("none", name) for name in STRATEGIES if name != "none"] + [("random", name) for name in ("degree", "degree_uniform", "betweenness", "behavior")] + [("degree", "behavior"), ("degree_uniform", "behavior"), ("betweenness", "behavior")]
    paired = {}
    for attacked in (False, True):
        for reference, candidate in pairs:
            key = f"{'attack' if attacked else 'clean'}/{candidate}_minus_{reference}"
            paired[key] = {m: paired_interval([final[candidate, attacked, q["id"]][m] - final[reference, attacked, q["id"]][m] for q in questions], protocol) for m in METRICS}
    for reference, candidate in pairs:
        paired[f"attack_increment/{candidate}_minus_{reference}"] = {m: paired_interval([
            (final[candidate, True, q["id"]][m] - final[candidate, False, q["id"]][m])
            - (final[reference, True, q["id"]][m] - final[reference, False, q["id"]][m])
            for q in questions], protocol) for m in METRICS}
    for strategy in STRATEGIES:
        paired[f"{strategy}/attack_minus_clean"] = {m: paired_interval([
            final[strategy, True, q["id"]][m] - final[strategy, False, q["id"]][m] for q in questions], protocol) for m in METRICS}
    effects = [{"question_index": i, "task_id": q["id"], "source": protocol["evaluation_source_by_task"][q["id"]],
                **{name: final[name, True, q["id"]]["target_rate"] for name in STRATEGIES},
                "behavior_minus_degree_uniform_pp": 100 * (final["behavior", True, q["id"]]["target_rate"] - final["degree_uniform", True, q["id"]]["target_rate"])} for i, q in enumerate(questions, 1)]
    write_csv(root / "primary_per_question.csv", effects)
    grouped_compliance = defaultdict(list)
    for row in compliance:
        grouped_compliance[(row["strategy"], row["round"])].append(row)
    by_source = [{"strategy": strategy, "source": source, "n_tasks": len(items),
                  **{m: float(np.mean([x[m] for x in items])) for m in METRICS}}
                 for strategy in STRATEGIES for source in protocol["attacker_positions"]
                 for items in [[x for x in averaged if x["strategy"] == strategy and x["attack_enabled"] and x["round"] == final_round and x["attacker_node"] == source]]]
    random_draws = [{"strategy": name, "attack_enabled": attacked,
                    **{m: float(np.mean([x[m] for x in items])) for m in METRICS}}
                   for name in (f"random_{i}" for i in range(protocol["random_draws"])) for attacked in (False, True)
                   for items in [[x for x in trials if x["strategy"] == name and x["attack_enabled"] == attacked and x["round"] == final_round]]]
    # Raw-label sensitivity is also averaged within question, including unequal tie counts.
    raw_trials = []
    grouped_raw = defaultdict(list)
    for row in nodes:
        if row["round"] == final_round:
            grouped_raw[row["trial_id"]].append(row)
    for items in grouped_raw.values():
        r = items[0]
        scored = evaluate([x["raw_declared_prediction"] for x in items], qindex[r["task_id"]]["answerKey"], protocol["evaluation_targets"][r["task_id"]])
        raw_trials.append({**r, "accuracy": scored["correct"] / len(items), "target_rate": scored["target_adoptions"] / len(items),
                           "invalid_rate": scored["invalid"] / len(items), "system_correct": scored["system_correct"],
                           "system_target": scored["system_target"], "no_majority": scored["no_majority"], "ever_target_rate": 0})
    raw_averaged = average_within_question(raw_trials)
    raw_sensitivity = [{"strategy": strategy, "attack_enabled": attacked,
                        **{m: float(np.mean([x[m] for x in items])) for m in ("accuracy", "target_rate", "invalid_rate")}}
                       for strategy in STRATEGIES for attacked in (False, True)
                       for items in [[x for x in raw_averaged if x["strategy"] == strategy and x["attack_enabled"] == attacked]]]
    distance_rows = []
    for strategy in STRATEGIES:
        for distance in (1, 2, 3):
            # Each node's degree-tie outcomes are averaged before distance pooling.
            groups = defaultdict(list)
            for row in nodes:
                if row["round"] == final_round and row["attack_enabled"] and strategy_group(row["strategy"]) == strategy and row["distance"] == distance:
                    groups[row["task_id"], row["node"]].append(row)
            if groups:
                distance_rows.append({"strategy": strategy, "distance": distance, "node_task_pairs": len(groups),
                    **{m: float(np.mean([np.mean([x[m] for x in items]) for items in groups.values()])) for m in ("correct", "target_adoption", "invalid")}})
    summary = {
        "scope": "30 new questions; frozen prior behavior scores; one graph, one budget and three seen source positions. Confirmation primary comparison prespecified before generation.",
        "primary_comparison": {**protocol["primary_comparison"], **paired["attack/behavior_minus_degree_uniform"]["target_rate"]},
        "metrics": metrics, "paired_differences": paired, "random_draw_metrics": random_draws,
        "degree_tie_sets_by_source": {s: degree_tie_sets(protocol, s) for s in protocol["attacker_positions"]},
        "final_metrics_by_source": by_source, "final_metrics_by_distance": distance_rows,
        "raw_answer_sensitivity": raw_sensitivity,
        "raw_vs_parsed_label_disagreements": sum(x["prediction"] != x["raw_declared_prediction"] for x in nodes),
        "source_compliance": [{"strategy": name, "round": r, "n": len(items), "target": sum(x["target"] for x in items), "invalid": sum(x["invalid"] for x in items)} for (name, r), items in sorted(grouped_compliance.items())],
        "logical_parse_status_counts": dict(Counter(r["parse_status"] for t in records for a in t["agents"] for r in a["rounds"])),
        "runtime": runtime, "validation": checks,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    plots(root, summary, effects)
    print(json.dumps({"primary_comparison": summary["primary_comparison"], "final_metrics": [x for x in metrics if x["round"] == final_round], "validation": checks}, indent=2))


def plots(root, summary, effects):
    final = {(r["strategy"], r["attack_enabled"]): r for r in summary["metrics"] if r["round"] == 4}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), constrained_layout=True)
    for ax, (attacked, metric, title) in zip(axes, [(True, "accuracy", "Attack: accuracy"), (True, "target_rate", "Attack: target adoption"), (False, "accuracy", "Clean: accuracy")]):
        bars = ax.bar(range(len(STRATEGIES)), [100 * final[s, attacked][metric] for s in STRATEGIES], color=COLORS)
        ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
        ax.set_xticks(range(len(STRATEGIES)), [NAMES[s] for s in STRATEGIES], rotation=40, ha="right", fontsize=8)
        ax.set_ylim(0, 105); ax.set_ylabel("Question-averaged honest-agent answers (%)"); ax.set_title(title)
        ax.grid(axis="y", alpha=.2); ax.set_axisbelow(True); ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Confirmation | Qwen3-8B | 30 new questions | k=2 of 7 eligible nodes")
    fig.savefig(root / "confirmation_comparison.png", dpi=180); fig.savefig(root / "confirmation_comparison.pdf"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(12, 4), constrained_layout=True)
    values = [x["behavior_minus_degree_uniform_pp"] for x in effects]
    ax.bar([x["question_index"] for x in effects], values, color=["#2a927c" if v < 0 else "#c66d76" for v in values])
    ax.axhline(0, color="black", linewidth=.7); ax.set_xticks(range(1, 31))
    ax.set_xlabel("Held-out question index"); ax.set_ylabel("Target adoption difference (pp)")
    ax.set_title("Primary comparison: Behavior minus Degree with uniform ties | negative favors Behavior")
    fig.savefig(root / "primary_question_effects.png", dpi=180); fig.savefig(root / "primary_question_effects.pdf"); plt.close(fig)


if __name__ == "__main__":
    main()
