"""Compare completed 3B and 8B pilots with matched tasks and interventions."""

import argparse
import csv
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_json(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=Path("results/netsafe_qwen3b_baseline"))
    parser.add_argument("--candidate", type=Path, default=Path("results/netsafe_qwen8b_baseline"))
    args = parser.parse_args()
    paths = [args.reference, args.candidate]
    configs = [read_json(p / "config.json") for p in paths]
    summaries = [read_json(p / "summary.json") for p in paths]
    varying = {"model", "requested_model_revision", "chat_template_kwargs"}
    stable = [{k: v for k, v in c.items() if k not in varying} for c in configs]
    assert stable[0] == stable[1], "The experiment settings do not match."
    spec = importlib.util.spec_from_file_location("analysis", Path(__file__).with_name("analyze_local_baseline.py"))
    analysis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analysis)
    metrics = [{r["condition"]: r for r in s["metrics"] if r["round"] == 2} for s in summaries]
    question_metrics = []
    for path in paths:
        with (path / "per_question.csv").open() as stream:
            question_metrics.append({(r["condition"], r["task_id"]): r for r in csv.DictReader(stream) if r["round"] == "2"})
    assert set(question_metrics[0]) == set(question_metrics[1])
    differences = {}
    for condition in configs[0]["conditions"]:
        differences[condition] = {}
        for metric in ("correct", "target_adoptions", "invalid", "system_correct", "system_target"):
            denominator = 1 if metric.startswith("system_") else len(configs[0]["evaluation_nodes"])
            values = [
                (int(question_metrics[1][(condition, task)][metric]) - int(question_metrics[0][(condition, task)][metric])) / denominator
                for task in configs[0]["sampled_ids"]
            ]
            differences[condition][metric] = analysis.bootstrap_difference(values)
    rows = []
    for config, model_metrics in zip(configs, metrics):
        for condition in config["conditions"]:
            rows.append({"model": config["model"], **model_metrics[condition]})
    with (args.candidate / "model_comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    comparison = {
        "reference": str(args.reference), "candidate": str(args.candidate),
        "models": [c["model"] for c in configs],
        "design_matched_except_model_and_model_specific_template": True,
        "scope": "Qwen2.5-3B versus Qwen3-8B; model family/generation changes as well as size. This does not isolate parameter count.",
        "final_metrics": rows,
        "candidate_minus_reference_paired_differences": differences,
        "raw_answer_sensitivity": {c["model"]: s["raw_answer_sensitivity"] for c, s in zip(configs, summaries)},
    }
    (args.candidate / "model_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n")
    conditions = configs[0]["conditions"]
    labels = ["Clean\nNo warning", "Attack\nNo warning", "Attack\nWarning", "Clean\nWarning"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), constrained_layout=True)
    x = np.arange(len(conditions))
    for index, (config, values) in enumerate(zip(configs, metrics)):
        for ax, metric in zip(axes, ("accuracy", "target_adoption_rate", "invalid")):
            y = [100 * values[c][metric] / (values[c]["n_agents"] if metric == "invalid" else 1) for c in conditions]
            bars = ax.bar(x + (index - .5) * .36, y, width=.36,
                          label=config["model"].split("/")[-1],
                          color=("#6987b5", "#278b74")[index])
            ax.bar_label(bars, fmt="%.0f", padding=2, fontsize=8)
    for ax, title in zip(axes, ("Pipeline accuracy", "Target-answer adoption", "Invalid answers")):
        ax.set_xticks(x, labels, fontsize=8)
        ax.set_title(title)
        ax.set_ylabel("Final honest-agent answers (%)")
        ax.set_ylim(0, 110)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Matched NetSafe pilot: 10 questions, one graph, 5 evaluated agents", fontsize=12)
    fig.savefig(args.candidate / "model_comparison.png", dpi=180)
    fig.savefig(args.candidate / "model_comparison.pdf")
    plt.close(fig)
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
