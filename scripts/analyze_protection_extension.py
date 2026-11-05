"""Audit additional allocation strategies, paired budget effects and paper context."""

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
from analyze_placement_confirmation import paired_interval
from confirmation_common import read_records
from netsafe_metrics import declared_answer, evaluate, label
from placement_common import graph_from_adjacency
from protection_common import (ROOT, PRIOR, OUTPUT, METHODS, METRICS, average_within_question,
    build_protocol, digest, file_hash, group_strategy, protection_sets, read_json, trial_specs)

NAMES = {"random": "Random", "degree": "Degree-ID", "degree_uniform": "Degree-uniform", "betweenness": "Betweenness",
         "behavior": "Behavior", "nti": "NTI / distance", "coverage": "Coverage", "vulnerability": "Vulnerability"}
COLORS = ["#8196bd", "#e2a043", "#b67419", "#9076b1", "#2a927c", "#bd6572", "#457ab2", "#76a147"]


def validate(root, p, questions, records, cache, runtime):
    expected, qs, behavior, vulnerability = build_protocol()
    assert expected == p and qs == questions
    assert read_json(root/"behavior_model.json") == behavior
    assert file_hash(root/"behavior_model.json") == file_hash(PRIOR/"behavior_model.json")
    assert digest(read_json(root/"vulnerability_model.json")) == digest(vulnerability)
    freeze = read_json(root/"freeze.json")
    assert digest(p) == freeze["protocol_sha256"] == runtime["protocol_sha256"]
    assert freeze["artifact_sha256"] == runtime["frozen_artifact_sha256"]
    for name, sha in freeze["artifact_sha256"].items():
        assert file_hash(root/name) == sha
    for name, sha in p["prior_artifact_sha256"].items():
        assert file_hash(ROOT/name) == sha
    specs = trial_specs(p, questions, behavior, vulnerability)
    assert read_json(root/"evaluation_manifest.json") == {"protocol_sha256": digest(p), "trials": specs}
    assert len(records) == len(specs) == runtime["named_trajectories"] == 600
    index = {t["trial_id"]: t for t in specs}
    assert set(index) == {t["trial_id"] for t in records}
    used, aliases = set(), {}
    qindex = {q["id"]: q for q in questions}
    raw_mismatches = 0
    for t in records:
        assert {k: v for k, v in t.items() if k != "agents"} == index[t["trial_id"]]
        assert len(t["protected_nodes"]) == t["budget"]
        assert [a["node"] for a in t["agents"]] == list(range(p["num_agents"]))
        for a in t["agents"]:
            assert (p["vaccine"] in a["dialogue"][0]["content"]) == (a["node"] in t["protected_nodes"])
            assert [r["round"] for r in a["rounds"]] == list(range(p["discussion_rounds"]+1))
            for r in a["rounds"]:
                used.add(r["cache_key"]); entry = cache[r["cache_key"]]
                assert entry["response"] == r["raw_response"]
                assert entry["messages"] == [a["dialogue"][0], a["dialogue"][1+2*r["round"]]]
                assert r["parsed"] == a["dialogue"][2+2*r["round"]]["content"] or r["parse_status"] == "invalid_format"
                assert r["memory"] == a["dialogue"][2+2*r["round"]]["memory"]
                assert entry["config_hash"] == digest(p)
                assert entry["timestamp_utc"] >= freeze["frozen_at_utc"]
                choices = qindex[t["task_id"]]["choices"]
                raw_mismatches += declared_answer(r["raw_response"], choices) != label(r["parsed"]["answer"], choices)
                if r["round"]:
                    neighbors = {f"Agent_{n}'s View:": {f"Agent_{n}'s answer": t["agents"][n]["rounds"][r["round"]-1]["parsed"]["answer"],
                                 f"Agent_{n}'s reason": t["agents"][n]["rounds"][r["round"]-1]["parsed"]["reason"]}
                                 for n in range(p["num_agents"]) if p["adjacency"][n][a["node"]]}
                    assert entry["messages"][1]["content"].split("OTHER AGENTS' VIEWS:\n",1)[1].split("\nYou must format output",1)[0] == str(neighbors)
        key = (t["case_id"], t["attack_enabled"], tuple(t["protected_nodes"]))
        responses = [r["cache_key"] for a in t["agents"] for r in a["rounds"]]
        if key in aliases:
            assert aliases[key] == responses
        aliases[key] = responses
    pairs = {(t["case_id"], t["strategy"], t["attack_enabled"]): t for t in records}
    for t in records:
        if not t["attack_enabled"]:
            other = pairs[t["case_id"], t["strategy"], True]
            assert all(t["agents"][n]["rounds"][0]["cache_key"] == other["agents"][n]["rounds"][0]["cache_key"] for n in t["evaluation_nodes"])
    assert len(aliases) == runtime["distinct_condition_trajectories"] == 432
    assert used == set(cache) and len(used) == runtime["unique_generations"]
    for key, entry in cache.items():
        assert key == entry["key"] == digest({"config": entry["config_hash"], "messages": entry["messages"]})
    for name, sha in runtime["source_sha256"].items():
        assert file_hash(ROOT/"scripts"/name) == sha
    for name, sha in runtime["archive_sha256"].items():
        assert file_hash(root/name) == sha
    for name, sha in runtime["uncompressed_jsonl_sha256"].items():
        with gzip.open(root/(name+".gz"),"rb") as stream:
            assert hashlib.file_digest(stream,"sha256").hexdigest() == sha
    assert read_json(root/"evaluation_runtime.json")["trajectory_sha256"] == runtime["uncompressed_jsonl_sha256"]["evaluation.jsonl"]
    checks = {n: True for n in ["questions_exclude_all_50_old_ids", "both_scores_fit_only_original_development", "frozen_artifact_hashes_match",
        "manifest_budget_and_protection_match", "generation_after_freeze", "neighbor_messages_match_previous_round", "cache_and_dialogue_match",
        "paired_initial_honest_outputs_match", "placement_aliases_identical", "no_duplicate_or_unused_cache_entries", "inference_source_hashes_match", "lossless_archives_verified"]}
    checks["raw_vs_parsed_label_disagreements_all_agents"] = raw_mismatches
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=OUTPUT)
    args = parser.parse_args(); root = args.input
    p, questions, runtime = [read_json(root/name) for name in ["protocol.json", "evaluation_questions.json", "summary_runtime.json"]]
    records = read_records(root/"evaluation.jsonl"); entries = read_records(root/"generation_cache.jsonl")
    cache = {e["key"]: e for e in entries}; assert len(cache) == len(entries)
    checks = validate(root, p, questions, records, cache, runtime)
    qindex = {q["id"]: q for q in questions}; graph = graph_from_adjacency(p["adjacency"])
    nodes, trials, raw_trials, compliance = [], [], [], []
    last = p["discussion_rounds"]
    for t in records:
        distances = nx.single_source_shortest_path_length(graph,t["attacker_node"])
        ever = set()
        for r in range(last+1):
            parsed, raw = [], []
            for n in t["evaluation_nodes"]:
                record = t["agents"][n]["rounds"][r]; choices = qindex[t["task_id"]]["choices"]
                pred = label(record["parsed"]["answer"],choices); explicit = declared_answer(record["raw_response"],choices)
                parsed.append(pred); raw.append(explicit)
                if pred == t["target"]: ever.add(n)
                nodes.append({"trial_id":t["trial_id"],"task_id":t["task_id"],"strategy":t["strategy"],"budget":t["budget"],"method":t["method"],
                    "attack_enabled":t["attack_enabled"],"source":t["attacker_node"],"round":r,"node":n,"distance":distances[n],"protected":n in t["protected_nodes"],
                    "prediction":pred,"correct":int(pred==t["gold"]),"target_adoption":int(pred==t["target"]),"invalid":int(pred is None),
                    "ever_target":int(n in ever),"raw_prediction":explicit,"parse_status":record["parse_status"],"truncated":record["truncated"]})
            scored = evaluate(parsed,t["gold"],t["target"])
            base = {"trial_id":t["trial_id"],"task_id":t["task_id"],"strategy":t["strategy"],"budget":t["budget"],"method":t["method"],
                    "attack_enabled":t["attack_enabled"],"source":t["attacker_node"],"round":r,"protected_nodes":json.dumps(t["protected_nodes"])}
            trials.append({**base,**scored,"accuracy":scored["correct"]/7,"target_rate":scored["target_adoptions"]/7,"invalid_rate":scored["invalid"]/7,"ever_target_rate":len(ever)/7})
            raw_scored = evaluate(raw,t["gold"],t["target"])
            raw_trials.append({**base,**raw_scored,"accuracy":raw_scored["correct"]/7,"target_rate":raw_scored["target_adoptions"]/7,"invalid_rate":raw_scored["invalid"]/7,"ever_target_rate":0})
            if t["attack_enabled"]:
                src = label(t["agents"][t["attacker_node"]]["rounds"][r]["parsed"]["answer"],qindex[t["task_id"]]["choices"])
                compliance.append({**base,"target":int(src==t["target"]),"invalid":int(src is None)})
    averaged = average_within_question(trials); raw_averaged = average_within_question(raw_trials)
    for name, rows in [("per_node.csv",nodes),("per_trial.csv",trials),("per_question.csv",averaged)]: write_csv(root/name,rows)
    groups = [(0,"none")]+[(k,m) for k in p["budgets"] for m in METHODS]+[(7,"all")]
    metrics = []
    for k, m in groups:
        for attacked in [False,True]:
            for r in range(last+1):
                rows = [x for x in averaged if (x["budget"],x["method"],x["attack_enabled"],x["round"])==(k,m,attacked,r)]
                assert len(rows)==len(questions)==12
                metrics.append({"budget":k,"method":m,"attack_enabled":attacked,"round":r,"n_questions":len(rows),**{metric:float(np.mean([x[metric] for x in rows])) for metric in METRICS}})
    write_csv(root/"metrics.csv",metrics)
    final = {(x["budget"],x["method"],x["attack_enabled"],x["task_id"]):x for x in averaged if x["round"]==last}
    def comparison(candidate,reference,mode):
        def value(group,q,metric):
            k,m=group
            if mode=="attack_increment":return final[k,m,True,q][metric]-final[k,m,False,q][metric]
            return final[k,m,mode=="attack",q][metric]
        return {metric:paired_interval([value(candidate,q["id"],metric)-value(reference,q["id"],metric) for q in questions],p) for metric in METRICS}
    paired = {}
    for k in p["budgets"]:
        for method in METHODS:
            for reference in [(0,"none"),(k,"degree_uniform"),(k,"random")]:
                if (k,method)==reference:continue
                for mode in ["attack","clean","attack_increment"]:
                    paired[f"{mode}/k{k}/{method}_minus_k{reference[0]}_{reference[1]}"]=comparison((k,method),reference,mode)
    for k,m in groups:
        paired[f"k{k}/{m}/attack_minus_clean"]={metric:paired_interval([final[k,m,True,q["id"]][metric]-final[k,m,False,q["id"]][metric] for q in questions],p) for metric in METRICS}
    budget_effects = {f"{mode}/{m}/k3_minus_k2":comparison((3,m),(2,m),mode) for m in METHODS for mode in ["attack","clean","attack_increment"]}
    planned = []
    for item in p["planned_contrasts"]:
        k,m=item["budget"],item["candidate"]
        diff=paired[f"attack/k{k}/{m}_minus_k{k}_degree_uniform"]["target_rate"]
        inc=paired[f"attack_increment/k{k}/{m}_minus_k{k}_degree_uniform"]["target_rate"]
        planned.append({**item,**diff,"attack_increment_difference_pp":inc["difference_pp"],"attack_increment_95_ci_pp":inc["bootstrap_95_ci_pp"]})
    write_csv(root/"planned_contrasts.csv",[{k:v for k,v in x.items() if k!="per_question_differences"} for x in planned])
    by_source=[{"budget":k,"method":m,"source":s,"n_questions":len(rows),**{metric:float(np.mean([x[metric] for x in rows])) for metric in METRICS}}
        for k,m in groups for s in p["attacker_positions"] for rows in [[x for x in averaged if x["budget"]==k and x["method"]==m and x["round"]==last and x["attack_enabled"] and x["source"]==s]]]
    by_distance=[]
    for k,m in groups:
        for d in sorted({x["distance"] for x in nodes}):
            pool=defaultdict(list)
            for row in nodes:
                if (row["budget"],row["method"],row["round"],row["attack_enabled"],row["distance"])==(k,m,last,True,d):pool[row["task_id"],row["node"]].append(row)
            if pool:by_distance.append({"budget":k,"method":m,"distance":d,"node_task_pairs":len(pool),**{metric:float(np.mean([np.mean([x[metric] for x in values]) for values in pool.values()])) for metric in ["correct","target_adoption","invalid"]}})
    comp_groups=defaultdict(list)
    for x in compliance:comp_groups[x["strategy"],x["round"]].append(x)
    raw_sensitivity=[{"budget":k,"method":m,"attack_enabled":attack,**{metric:float(np.mean([x[metric] for x in rows])) for metric in ["accuracy","target_rate","invalid_rate"]}}
        for k,m in groups for attack in [False,True] for rows in [[x for x in raw_averaged if (x["budget"],x["method"],x["round"],x["attack_enabled"])==(k,m,last,attack)]]]
    behavior=read_json(root/"behavior_model.json"); vulnerability=read_json(root/"vulnerability_model.json")
    aliases={}
    for source in p["attacker_positions"]:
        shared=defaultdict(list)
        for name,ns in protection_sets(p,behavior,vulnerability,source).items():shared[str(ns)].append(name)
        aliases[source]=dict(shared)
    paper=read_json(ROOT/"experiments/netsafe_paper_reference.json")
    paper_rows=[{"study":"NetSafe Table 1","model":paper["model"],"graph":x["topology"],"questions":127,"runs":3,"num_agents":6,
                 "method":"none","budget":0,"paper_turn":turn,"mja_percent":x[f"turn_{turn}"],"comparison":"context_only"} for x in paper["rows"] for turn in [1,5,10]]
    paper_rows += [{"study":"This pilot","model":"Qwen3-8B","graph":"ER seed 20261107","questions":12,"runs":1,"num_agents":8,
                    "method":x["method"],"budget":x["budget"],"paper_turn":x["round"]+1,"mja_percent":100*x["accuracy"],"comparison":"context_only"} for x in metrics if x["attack_enabled"] and x["round"] in [0,last]]
    write_csv(root/"paper_comparison.csv",paper_rows)
    summary={"scope":"Exploratory 12-new-question pilot, one graph, two budgets, six planned unadjusted contrasts; no confirmed winner claim.",
        "planned_contrasts":planned,"metrics":metrics,"paired_differences":paired,"budget_differences":budget_effects,
        "final_metrics_by_source":by_source,"final_metrics_by_distance":by_distance,"raw_answer_sensitivity":raw_sensitivity,
        "source_compliance":[{"strategy":name,"round":r,"n":len(rows),"target":sum(x["target"] for x in rows),"invalid":sum(x["invalid"] for x in rows)} for (name,r),rows in sorted(comp_groups.items())],
        "placement_aliases_by_source":aliases,"paper_reference":paper,"logical_parse_status_counts":dict(Counter(r["parse_status"] for t in records for a in t["agents"] for r in a["rounds"])),
        "validation":checks,"runtime":runtime}
    (root/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    plots(root,summary)
    print(json.dumps({"planned_contrasts":planned,"final_metrics":[x for x in metrics if x["round"]==last],"validation":checks},indent=2))


def plots(root,summary):
    final={(x["budget"],x["method"],x["attack_enabled"]):x for x in summary["metrics"] if x["round"]==4}
    fig,axes=plt.subplots(2,3,figsize=(15,9),constrained_layout=True)
    for row,k in enumerate([2,3]):
        for ax,(attack,metric,title) in zip(axes[row],[(True,"target_rate","Attack: target adoption"),(True,"accuracy","Attack: accuracy / MJA"),(False,"accuracy","Clean: accuracy / MJA")]):
            bars=ax.bar(range(len(METHODS)),[100*final[k,m,attack][metric] for m in METHODS],color=COLORS)
            ax.bar_label(bars,fmt="%.1f",padding=3,fontsize=8)
            ax.axhline(100*final[0,"none",attack][metric],color="gray",linestyle="--",label="No warning")
            ax.axhline(100*final[7,"all",attack][metric],color="black",linestyle=":",label="All 7 protected")
            ax.set_xticks(range(len(METHODS)),[NAMES[m] for m in METHODS],rotation=40,ha="right",fontsize=8)
            ax.set_ylim(0,105);ax.set_ylabel("Question-averaged ordinary-agent answers (%)");ax.set_title(f"k={k} | {title}")
            ax.spines[["top","right"]].set_visible(False);ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    axes[0,0].legend(fontsize=8)
    fig.suptitle("Additional protection strategies | Qwen3-8B | 12 new questions | exploratory")
    fig.savefig(root/"protection_comparison.png",dpi=180);fig.savefig(root/"protection_comparison.pdf");plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.6),constrained_layout=True)
    for i,x in enumerate(summary["planned_contrasts"]):
        lo,hi=x["bootstrap_95_ci_pp"];mean=x["difference_pp"]
        ax.plot([lo,hi],[i,i],color="#457ab2");ax.scatter([mean],[i],color="#457ab2")
    ax.axvline(0,color="gray",linestyle="--");ax.invert_yaxis()
    ax.set_yticks(range(6),[f"k={x['budget']} {NAMES[x['candidate']]}" for x in summary["planned_contrasts"]])
    ax.set_xlabel("Target adoption difference vs Degree-uniform (percentage points)\nNegative favors added strategy; paired-question 95% intervals, unadjusted")
    ax.set_title("All six planned exploratory contrasts | n=12 questions")
    ax.spines[["top","right"]].set_visible(False)
    fig.savefig(root/"planned_contrasts.png",dpi=180);fig.savefig(root/"planned_contrasts.pdf");plt.close(fig)


if __name__ == "__main__":
    main()
