"""Verify exact pilot-prefix reuse and compare two versus four discussion rounds."""

import argparse
import json
from pathlib import Path

from analyze_local_baseline import bootstrap_difference
from netsafe_metrics import evaluate, label


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, default=Path("results/netsafe_qwen8b_baseline"))
    parser.add_argument("--extended", type=Path, default=Path("results/netsafe_qwen8b_round4_pilot"))
    args = parser.parse_args()
    configs = [read(p / "config.json") for p in (args.initial, args.extended)]
    assert [{k: v for k, v in c.items() if k != "discussion_rounds"} for c in configs][0] == {k: v for k, v in configs[1].items() if k != "discussion_rounds"}
    assert configs[0]["discussion_rounds"] < configs[1]["discussion_rounds"]
    questions = read(args.initial / "questions.json")
    assert questions == read(args.extended / "questions.json")
    choices = {q["id"]: q["choices"] for q in questions}
    trajectories = [{(t["condition"], t["task_id"]): t for t in (json.loads(line) for line in (p / "trajectories.jsonl").read_text().splitlines())} for p in (args.initial, args.extended)]
    assert trajectories[0].keys() == trajectories[1].keys()
    prefix_records = 0
    for key, original in trajectories[0].items():
        extension = trajectories[1][key]
        for old_agent, new_agent in zip(original["agents"], extension["agents"]):
            for old, new in zip(old_agent["rounds"], new_agent["rounds"]):
                for field in ("round", "raw_response", "parsed", "memory", "parse_status", "truncated"):
                    assert old[field] == new[field], (key, old_agent["node"], old["round"], field)
                prefix_records += 1
    metric_rows, differences = [], {}
    for condition in configs[0]["conditions"]:
        paired = []
        for q in questions:
            scores = []
            for config, runs in zip(configs, trajectories):
                t = runs[(condition, q["id"])]
                labels = [label(t["agents"][n]["rounds"][config["discussion_rounds"]]["parsed"]["answer"], choices[q["id"]]) for n in config["evaluation_nodes"]]
                scores.append(evaluate(labels, t["gold"], t["target"]))
            paired.append(scores)
        for index, config in enumerate(configs):
            metric_rows.append({"condition": condition, "discussion_rounds": config["discussion_rounds"], **{metric: sum(pair[index][metric] for pair in paired) for metric in ("n_agents", "correct", "target_adoptions", "invalid", "system_correct", "system_target")}})
        differences[condition] = {metric: bootstrap_difference([(pair[1][metric] - pair[0][metric]) / (1 if metric.startswith("system_") else len(configs[0]["evaluation_nodes"])) for pair in paired]) for metric in ("correct", "target_adoptions", "invalid", "system_correct", "system_target")}
    comparison = {"exact_prefix_logical_responses": prefix_records, "prefix_identical": True,
                  "final_metrics": metric_rows, "extended_minus_initial": differences,
                  "interpretation": "Paired continuation of the same trajectories, not an independent replication; development/pilot questions only."}
    (args.extended / "extension_comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
