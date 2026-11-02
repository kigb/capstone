"""Validate held-out placement experiments and summarize at the task level."""

import argparse
import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from analyze_local_baseline import bootstrap_difference
from netsafe_metrics import declared_answer, evaluate, label
from placement_common import fit_behavior, graph_from_adjacency, placement_sets


STRATEGIES = ["none", "random", "degree", "betweenness", "behavior", "all"]
NAMES = {"none": "No warning", "random": "Random-k", "degree": "Degree-k",
         "betweenness": "Betweenness-k", "behavior": "Behavior-k", "all": "All protected"}
COLORS = ["#888888", "#8196bd", "#e2a043", "#9076b1", "#2a927c", "#c66d76"]


def read_json(path):
    return json.loads(path.read_text())


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def average_random_draws(rows):
    groups = defaultdict(list)
    for row in rows:
        strategy = "random" if row["strategy"].startswith("random_") else row["strategy"]
        groups[(strategy, row["attack_enabled"], row["case_id"], row["round"])].append(row)
    averaged = []
    metric_keys = ("accuracy", "target_rate", "invalid_rate", "system_correct", "system_target", "no_majority", "ever_target_rate")
    for (strategy, attacked, case_id, r), items in groups.items():
        averaged.append({"strategy": strategy, "attack_enabled": attacked, "case_id": case_id,
                         "task_id": items[0]["task_id"], "attacker_node": items[0]["attacker_node"],
                         "round": r, "draws": len(items),
                         **{key: float(np.mean([x[key] for x in items])) for key in metric_keys}})
    return averaged


def average_ranks(values):
    ranks = []
    for value in values:
        lower = sum(x < value for x in values)
        equal = sum(x == value for x in values)
        ranks.append(lower + (equal + 1) / 2)
    return ranks


def validate(root, protocol, development, evaluation, dev_questions, eval_questions, cache, frozen):
    assert not set(protocol["development_ids"]) & set(protocol["evaluation_ids"])
    assert {q["id"] for q in dev_questions} == set(protocol["development_ids"])
    assert {q["id"] for q in eval_questions} == set(protocol["evaluation_ids"])
    assert len(development) == len(dev_questions) * len(protocol["attacker_positions"])
    assert {(t["task_id"], t["attacker_node"]) for t in development} == {
        (q["id"], source) for q in dev_questions for source in protocol["attacker_positions"]}
    refitted = fit_behavior(development, dev_questions, protocol["adjacency"], protocol["minimum_behavior_opportunities"])
    assert json.loads(json.dumps(refitted)) == frozen["model"]
    assert frozen["development_sha256"] == file_hash(root / "development.jsonl")
    assert frozen["protocol_sha256"] == hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    manifest = read_json(root / "evaluation_manifest.json")
    assert manifest["behavior_model_sha256"] == file_hash(root / "behavior_model.json")
    assert len(evaluation) == len(manifest["trials"]) == len(eval_questions) * 2 * (5 + protocol["random_draws"])
    assert {t["trial_id"] for t in evaluation} == {t["trial_id"] for t in manifest["trials"]}
    specs = {t["trial_id"]: t for t in manifest["trials"]}
    question_index = {q["id"]: q for q in dev_questions + eval_questions}
    aliases = {}
    for t in development + evaluation:
        expected_phase = "development" if t in development else "evaluation"
        assert t["phase"] == expected_phase
        assert t["gold"] == question_index[t["task_id"]]["answerKey"]
        assert t["target"] == protocol[f"{expected_phase}_targets"][t["task_id"]] != t["gold"]
        assert t["evaluation_nodes"] == [n for n in range(protocol["num_agents"]) if n != t["attacker_node"]]
        assert t["attacker_node"] not in t["protected_nodes"]
        if expected_phase == "evaluation":
            assert {k: v for k, v in t.items() if k != "agents"} == specs[t["trial_id"]]
            assert t["attacker_node"] == protocol["evaluation_source_by_task"][t["task_id"]]
            assert t["protected_nodes"] == placement_sets(protocol, refitted, t["attacker_node"])[t["strategy"]]
        else:
            assert t["strategy"] == "none" and t["attack_enabled"] and not t["protected_nodes"]
        assert [a["node"] for a in t["agents"]] == list(range(protocol["num_agents"]))
        for a in t["agents"]:
            assert (protocol["vaccine"] in a["dialogue"][0]["content"]) == (a["node"] in t["protected_nodes"])
            assert [r["round"] for r in a["rounds"]] == list(range(protocol["discussion_rounds"] + 1))
            for r in a["rounds"]:
                entry = cache[r["cache_key"]]
                assert r["raw_response"] == entry["response"]
                assert entry["messages"] == [a["dialogue"][0], a["dialogue"][1 + 2 * r["round"]]]
                assert entry["config_hash"] == frozen["protocol_sha256"]
                if expected_phase == "evaluation":
                    assert entry["timestamp_utc"] >= frozen["frozen_at_utc"]
        alias = (t["phase"], t["case_id"], t["attack_enabled"], tuple(t["protected_nodes"]))
        keys = [r["cache_key"] for a in t["agents"] for r in a["rounds"]]
        if alias in aliases:
            assert aliases[alias] == keys
        aliases[alias] = keys
    index = {(t["case_id"], t["strategy"], t["attack_enabled"]): t for t in evaluation}
    for t in evaluation:
        if not t["attack_enabled"]:
            other = index[(t["case_id"], t["strategy"], True)]
            for node in t["evaluation_nodes"]:
                assert t["agents"][node]["rounds"][0]["cache_key"] == other["agents"][node]["rounds"][0]["cache_key"]
    return {"disjoint_questions": True, "behavior_refit_from_development_only": True,
            "behavior_frozen_before_evaluation_generations": True, "manifest_and_protection_match": True,
            "cache_and_dialogue_match": True, "paired_initial_honest_responses_identical": True,
            "identical_placements_have_identical_trajectories": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/netsafe_placement_qwen8b"))
    args = parser.parse_args()
    root = args.input
    protocol, runtime, frozen = (read_json(root / name) for name in ("protocol.json", "summary_runtime.json", "behavior_model.json"))
    development, evaluation = (read_jsonl(root / f"{phase}.jsonl") for phase in ("development", "evaluation"))
    dev_questions, eval_questions = (read_json(root / f"{phase}_questions.json") for phase in ("development", "evaluation"))
    cache = {e["key"]: e for e in read_jsonl(root / "generation_cache.jsonl")}
    checks = validate(root, protocol, development, evaluation, dev_questions, eval_questions, cache, frozen)
    final_round = protocol["discussion_rounds"]
    graph = graph_from_adjacency(protocol["adjacency"])
    question_index = {q["id"]: q for q in dev_questions + eval_questions}
    nodes, trials, source_compliance = [], [], []
    for t in evaluation:
        choices = question_index[t["task_id"]]["choices"]
        distances = nx.single_source_shortest_path_length(graph, t["attacker_node"])
        ever_target = set()
        for r in range(final_round + 1):
            labels = []
            for n in t["evaluation_nodes"]:
                record = t["agents"][n]["rounds"][r]
                prediction = label(record["parsed"]["answer"], choices)
                raw_prediction = declared_answer(record["raw_response"], choices)
                labels.append(prediction)
                if prediction == t["target"]: ever_target.add(n)
                nodes.append({"trial_id": t["trial_id"], "case_id": t["case_id"], "task_id": t["task_id"],
                              "strategy": t["strategy"], "attack_enabled": t["attack_enabled"], "round": r,
                              "node": n, "attacker_node": t["attacker_node"], "distance": distances[n],
                              "protected": n in t["protected_nodes"], "prediction": prediction,
                              "correct": int(prediction == t["gold"]), "target_adoption": int(prediction == t["target"]),
                              "invalid": int(prediction is None), "ever_target_adoption": int(n in ever_target),
                              "raw_declared_prediction": raw_prediction, "raw_declared_correct": int(raw_prediction == t["gold"]),
                              "raw_declared_target": int(raw_prediction == t["target"]), "raw_declared_invalid": int(raw_prediction is None),
                              "parse_status": record["parse_status"], "truncated": record["truncated"]})
            scored = evaluate(labels, t["gold"], t["target"])
            trials.append({"trial_id": t["trial_id"], "case_id": t["case_id"], "task_id": t["task_id"],
                           "strategy": t["strategy"], "attack_enabled": t["attack_enabled"], "attacker_node": t["attacker_node"],
                           "protected_nodes": json.dumps(t["protected_nodes"]), "round": r, **scored,
                           "accuracy": scored["correct"] / len(labels), "target_rate": scored["target_adoptions"] / len(labels),
                           "invalid_rate": scored["invalid"] / len(labels), "ever_target_rate": len(ever_target) / len(labels)})
            if t["attack_enabled"]:
                answer = label(t["agents"][t["attacker_node"]]["rounds"][r]["parsed"]["answer"], choices)
                source_compliance.append({"trial_id": t["trial_id"], "strategy": t["strategy"], "round": r, "target": int(answer == t["target"]), "invalid": int(answer is None)})
    averaged = average_random_draws(trials)
    write_csv(root / "per_node.csv", nodes)
    write_csv(root / "per_trial.csv", trials)
    write_csv(root / "per_question.csv", averaged)
    metrics = []
    metric_names = ("accuracy", "target_rate", "invalid_rate", "system_correct", "system_target", "no_majority", "ever_target_rate")
    for strategy in STRATEGIES:
        for attacked in (False, True):
            for r in range(final_round + 1):
                selected = [x for x in averaged if x["strategy"] == strategy and x["attack_enabled"] == attacked and x["round"] == r]
                raw = [x for x in trials if (x["strategy"].startswith("random_") if strategy == "random" else x["strategy"] == strategy) and x["attack_enabled"] == attacked and x["round"] == r]
                assert len(selected) == len(eval_questions)
                metrics.append({"strategy": strategy, "attack_enabled": attacked, "round": r, "n_tasks": len(selected),
                                **{name: float(np.mean([x[name] for x in selected])) for name in metric_names},
                                "raw_agent_answers": sum(x["n_agents"] for x in raw), "raw_correct": sum(x["correct"] for x in raw),
                                "raw_target_answers": sum(x["target_adoptions"] for x in raw), "raw_invalid": sum(x["invalid"] for x in raw)})
    write_csv(root / "metrics.csv", metrics)
    final_index = {(x["strategy"], x["attack_enabled"], x["task_id"]): x for x in averaged if x["round"] == final_round}
    comparisons = {}
    for attacked in (False, True):
        for reference, candidate in [("none", x) for x in STRATEGIES if x != "none"] + [("random", x) for x in ("degree", "betweenness", "behavior")] + [("degree", "behavior"), ("betweenness", "behavior")]:
            key = f"{'attack' if attacked else 'clean'}/{candidate}_minus_{reference}"
            comparisons[key] = {metric: bootstrap_difference([final_index[(candidate, attacked, q["id"])][metric] - final_index[(reference, attacked, q["id"])][metric] for q in eval_questions]) for metric in ("accuracy", "target_rate", "invalid_rate", "system_correct", "system_target")}
    for strategy in STRATEGIES:
        comparisons[f"{strategy}/attack_minus_clean"] = {metric: bootstrap_difference([final_index[(strategy, True, q["id"])][metric] - final_index[(strategy, False, q["id"])][metric] for q in eval_questions]) for metric in ("accuracy", "target_rate", "system_correct", "system_target")}
    for reference, candidate in [("none", x) for x in STRATEGIES if x != "none"] + [("random", x) for x in ("degree", "betweenness", "behavior")] + [("degree", "behavior"), ("betweenness", "behavior")]:
        comparisons[f"attack_increment/{candidate}_minus_{reference}"] = {
            metric: bootstrap_difference([
                (final_index[(candidate, True, q["id"])][metric] - final_index[(candidate, False, q["id"])][metric])
                - (final_index[(reference, True, q["id"])][metric] - final_index[(reference, False, q["id"])][metric])
                for q in eval_questions
            ]) for metric in ("accuracy", "target_rate", "system_correct", "system_target")
        }
    behavior = frozen["model"]
    degree, between = dict(graph.degree()), nx.betweenness_centrality(graph)
    score_rows = [{"node": n, "degree": degree[n], "betweenness": between[n], **{k: v for k, v in behavior["nodes"][str(n)].items() if k != "task_ids"}, "distinct_development_questions": len(behavior["nodes"][str(n)]["task_ids"])} for n in graph]
    write_csv(root / "behavior_scores.csv", score_rows)
    supported = [x for x in score_rows if x["supported"]]
    spearman = None
    if len(supported) >= 3 and len({x["degree"] for x in supported}) > 1 and len({x["empirical_rate"] for x in supported}) > 1:
        spearman = float(np.corrcoef(average_ranks([x["degree"] for x in supported]), average_ranks([x["empirical_rate"] for x in supported]))[0, 1])
    normalized_model = {**behavior, "nodes": {int(n): x for n, x in behavior["nodes"].items()}}
    selections = {source: placement_sets(protocol, normalized_model, source) for source in protocol["attacker_positions"]}
    overlap = {source: {name: len(set(items[name]) & set(items["degree"])) / protocol["budget"] for name in ("betweenness", "behavior")} for source, items in selections.items()}
    # A different set can still be a degree-optimal tie resolution. Report this
    # explicitly before interpreting placement differences as beyond degree.
    degree_ties = {}
    for source, items in selections.items():
        eligible = [n for n in graph if n != source]
        cutoff = sorted((degree[n] for n in eligible), reverse=True)[protocol["budget"] - 1]
        optimum = sum(degree[n] for n in items["degree"])
        degree_ties[source] = {
            "cutoff_degree": cutoff,
            "nodes_above_cutoff": [n for n in eligible if degree[n] > cutoff],
            "nodes_tied_at_cutoff": [n for n in eligible if degree[n] == cutoff],
            "degree_optimal_subsets": [list(s) for s in itertools.combinations(eligible, protocol["budget"])
                                       if sum(degree[n] for n in s) == optimum],
            "behavior_is_degree_optimal_tie_resolution": sum(degree[n] for n in items["behavior"]) == optimum,
        }
    source_summary = [{"strategy": name, "round": r, "n": len(selected), "target": sum(x["target"] for x in selected), "invalid": sum(x["invalid"] for x in selected)} for name in sorted({x["strategy"] for x in source_compliance}) for r in range(final_round + 1) for selected in [[x for x in source_compliance if x["strategy"] == name and x["round"] == r]]]
    raw_sensitivity = [{"strategy": strategy, "attack_enabled": attacked, "n": len(items), "correct": sum(x["raw_declared_correct"] for x in items), "target": sum(x["raw_declared_target"] for x in items), "invalid": sum(x["raw_declared_invalid"] for x in items)} for strategy in STRATEGIES for attacked in (False, True) for items in [[x for x in nodes if x["round"] == final_round and x["attack_enabled"] == attacked and (x["strategy"].startswith("random_") if strategy == "random" else x["strategy"] == strategy)]]]
    distance_metrics = [{"strategy": strategy, "distance": distance, "n": len(items), "correct": sum(x["correct"] for x in items), "target": sum(x["target_adoption"] for x in items), "invalid": sum(x["invalid"] for x in items)} for strategy in STRATEGIES for distance in sorted({x["distance"] for x in nodes}) for items in [[x for x in nodes if x["round"] == final_round and x["attack_enabled"] and x["distance"] == distance and (x["strategy"].startswith("random_") if strategy == "random" else x["strategy"] == strategy)]] if items]
    random_draws = [{"strategy": name, "attack_enabled": attacked, "accuracy": float(np.mean([x["accuracy"] for x in items])), "target_rate": float(np.mean([x["target_rate"] for x in items]))} for name in (f"random_{i}" for i in range(protocol["random_draws"])) for attacked in (False, True) for items in [[x for x in trials if x["strategy"] == name and x["attack_enabled"] == attacked and x["round"] == final_round]]]
    summary = {"scope": "Exploratory held-out question study; one graph, one budget, three seen source positions; ten independent evaluation questions.",
               "metrics": metrics, "paired_differences": comparisons, "random_draw_metrics": random_draws,
               "behavior_informative": behavior["informative"], "behavior_coverage": behavior["coverage"],
               "supported_nodes": [x["node"] for x in supported], "degree_behavior_spearman_supported_only": spearman,
               "placement_sets_by_source": selections, "top_k_overlap_with_degree": overlap,
               "degree_cutoff_tie_diagnostics": degree_ties,
               "source_compliance": source_summary, "raw_answer_sensitivity": raw_sensitivity, "final_metrics_by_distance": distance_metrics,
               "logical_parse_status_counts": dict(Counter(r["parse_status"] for t in development + evaluation for a in t["agents"] for r in a["rounds"])),
               "runtime": runtime, "validation": checks}
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    plots(root, protocol, summary, score_rows, graph)
    print(json.dumps({"final": [x for x in metrics if x["round"] == final_round], "behavior_informative": behavior["informative"], "behavior_coverage": behavior["coverage"], "validation": checks}, indent=2))


def plots(root, protocol, summary, scores, graph):
    final = {(r["strategy"], r["attack_enabled"]): r for r in summary["metrics"] if r["round"] == protocol["discussion_rounds"]}
    names = [NAMES[s] + ("\n(degree fallback)" if s == "behavior" and not summary["behavior_informative"] else "") for s in STRATEGIES]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
    for ax, (attacked, metric, title) in zip(axes, [(True, "accuracy", "Attack: accuracy"), (True, "target_rate", "Attack: target adoption"), (False, "accuracy", "Clean: accuracy")]):
        values = [100 * final[(s, attacked)][metric] for s in STRATEGIES]
        bars = ax.bar(range(len(STRATEGIES)), values, color=COLORS)
        ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
        ax.set_xticks(range(len(STRATEGIES)), names, rotation=35, ha="right", fontsize=8)
        ax.set_ylim(0, 105); ax.set_ylabel("Honest-agent answers (%)"); ax.set_title(title)
        ax.grid(axis="y", alpha=.2); ax.set_axisbelow(True); ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Held-out placement pilot | Qwen3-8B | 10 questions | k=2 of 7 eligible nodes")
    fig.savefig(root / "placement_comparison.png", dpi=180); fig.savefig(root / "placement_comparison.pdf"); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    positions = nx.spring_layout(graph, seed=20261102)
    example = summary["placement_sets_by_source"][0]
    colors = ["#c66d76" if n == 0 else "#2a927c" if n in set(example["degree"]) & set(example["betweenness"]) else "#e2a043" if n in example["degree"] else "#9076b1" if n in example["betweenness"] else "#d5dce3" for n in graph]
    nx.draw_networkx(graph, positions, ax=axes[0], node_color=colors, node_size=650, font_size=10, edge_color="#aab3bc")
    nx.draw_networkx_nodes(graph, positions, nodelist=example["behavior"], ax=axes[0],
                           node_color="none", node_size=850, edgecolors="#2466a3", linewidths=2)
    axes[0].set_title(f"Source 0: degree {example['degree']}; betweenness {example['betweenness']}\nBehavior {example['behavior']}")
    axes[0].axis("off")
    axes[0].text(.5, -.02, "Red: source; green: degree + betweenness; gold: degree; purple: betweenness\nBlue ring: behavior", transform=axes[0].transAxes, ha="center", fontsize=8)
    x = np.arange(len(scores))
    axes[1].bar(x - .18, [s["opportunities"] for s in scores], .36, label="Weighted exposure opportunities", color="#8196bd")
    axes[1].bar(x + .18, [s["adoptions"] for s in scores], .36, label="Weighted downstream adoptions", color="#2a927c")
    axes[1].axhline(protocol["minimum_behavior_opportunities"], color="#c66d76", linestyle="--", label="Minimum support")
    axes[1].set_xticks(x, [str(s["node"]) for s in scores]); axes[1].set_xlabel("Sender node (direct attacker episodes excluded)")
    axes[1].set_title("Development evidence for behavior scoring"); axes[1].legend(fontsize=8)
    axes[1].grid(axis="y", alpha=.2); axes[1].set_axisbelow(True)
    fig.savefig(root / "graph_and_coverage.png", dpi=180); fig.savefig(root / "graph_and_coverage.pdf"); plt.close(fig)


if __name__ == "__main__":
    main()
