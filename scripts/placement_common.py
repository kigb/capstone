"""Graph selection and observational placement rules, without model inference."""

import itertools
import random

import networkx as nx

from netsafe_metrics import label


def graph_from_adjacency(adjacency):
    graph = nx.Graph()
    graph.add_nodes_from(range(len(adjacency)))
    for i, row in enumerate(adjacency):
        for j, value in enumerate(row):
            if value:
                graph.add_edge(i, j)
    return graph


def rank_nodes(scores, candidates):
    return sorted(candidates, key=lambda node: (-scores[node], node))


def select_graph(nodes=8, probability=.32, first_seed=20261102, sources=(0, 3, 6), budget=2):
    """Select using graph structure only, before any model outcomes are observed."""
    for seed in range(first_seed, first_seed + 10000):
        graph = nx.gnp_random_graph(nodes, probability, seed=seed)
        if not nx.is_connected(graph):
            continue
        degree = dict(graph.degree())
        betweenness = nx.betweenness_centrality(graph)
        differences = sum(
            set(rank_nodes(degree, [n for n in graph if n != source])[:budget])
            != set(rank_nodes(betweenness, [n for n in graph if n != source])[:budget])
            for source in sources
        )
        if differences >= 2:
            return {
                "generator": "networkx.gnp_random_graph", "nodes": nodes,
                "edge_probability": probability, "first_candidate_seed": first_seed,
                "selected_seed": seed, "selection_criterion": "First connected graph with degree/betweenness top-k sets differing for at least two of the three prescribed source positions; no model outputs used.",
                "edges": [list(edge) for edge in sorted(graph.edges())],
                "adjacency": [[int(graph.has_edge(i, j)) for j in graph] for i in graph],
                "degree": degree, "betweenness": betweenness,
                "networkx_version": nx.__version__,
            }
    raise RuntimeError("No graph satisfies the prespecified structural criterion")


def random_placements(candidates, budget, draws, seed):
    subsets = list(itertools.combinations(sorted(candidates), budget))
    if draws > len(subsets):
        raise ValueError("More random draws requested than distinct subsets")
    random.Random(seed).shuffle(subsets)
    return [list(nodes) for nodes in subsets[:draws]]


def fit_behavior(trajectories, questions, adjacency, minimum_opportunities=3):
    """Observed transition rate from naturally affected, non-attacker senders.

    Exposure requires a sender's explicit target answer and a recipient's
    previous valid, non-target answer. If several neighbors supply the target,
    allocate 1/m exposure and adoption credit to each (including attackers in m).
    Direct attackers never contribute to the fitted sender statistics. Invalid
    next answers are recorded, and excluded from rate estimation.
    """
    question_index = {q["id"]: q for q in questions}
    counts = {node: {"opportunities": 0., "adoptions": 0., "invalid_weight": 0.,
                     "exposed_receiver_rounds": 0, "task_ids": set()}
              for node in range(len(adjacency))}
    events = []
    for trajectory in trajectories:
        assert trajectory["phase"] == "development"
        assert trajectory["attack_enabled"] and not trajectory["protected_nodes"]
        q = question_index[trajectory["task_id"]]
        by_node = {a["node"]: a for a in trajectory["agents"]}
        source, target = trajectory["attacker_node"], trajectory["target"]
        for r in range(1, len(by_node[0]["rounds"])):
            previous = {n: label(a["rounds"][r-1]["parsed"]["answer"], q["choices"]) for n, a in by_node.items()}
            current = {n: label(a["rounds"][r]["parsed"]["answer"], q["choices"]) for n, a in by_node.items()}
            for receiver in trajectory["evaluation_nodes"]:
                if previous[receiver] is None or previous[receiver] == target:
                    continue
                senders = [n for n in by_node if adjacency[n][receiver] and previous[n] == target]
                if not senders:
                    continue
                for sender in senders:
                    if sender == source:
                        continue
                    weight = 1 / len(senders)
                    event = {"case_id": trajectory["case_id"], "task_id": q["id"], "source": source,
                             "round": r, "sender": sender, "receiver": receiver,
                             "all_target_senders": senders, "weight": weight,
                             "adopted": current[receiver] == target, "invalid": current[receiver] is None}
                    events.append(event)
                    node = counts[sender]
                    node["exposed_receiver_rounds"] += 1
                    node["task_ids"].add(q["id"])
                    if current[receiver] is None:
                        node["invalid_weight"] += weight
                    else:
                        node["opportunities"] += weight
                        node["adoptions"] += weight * event["adopted"]
    for node in counts.values():
        node["task_ids"] = sorted(node["task_ids"])
        node["supported"] = node["opportunities"] >= minimum_opportunities
        node["empirical_rate"] = node["adoptions"] / node["opportunities"] if node["opportunities"] else None
    supported = [x for x in counts.values() if x["supported"]]
    pooled = sum(x["adoptions"] for x in supported) / sum(x["opportunities"] for x in supported) if supported else None
    distinct = len({round(x["empirical_rate"], 12) for x in supported})
    informative = len(supported) >= 2 and distinct >= 2
    for node in counts.values():
        node["placement_score"] = node["empirical_rate"] if node["supported"] else pooled
    return {
        "minimum_opportunities": minimum_opportunities, "nodes": counts,
        "pooled_supported_rate": pooled, "informative": informative,
        "coverage": len(supported) / len(counts), "events": events,
        "inference": "Observational association, not causal attribution. Direct attacker behavior excluded.",
        "fallback_rule": "If fewer than two supported nodes or all supported rates equal, use degree placement. Otherwise impute insufficiently observed nodes with pooled supported rate; rank by rate, then degree, then node ID. Report imputation and coverage.",
    }


def placement_sets(protocol, behavior, source):
    nodes = protocol["num_agents"]
    eligible = [n for n in range(nodes) if n != source]
    graph = graph_from_adjacency(protocol["adjacency"])
    degree, between = dict(graph.degree()), nx.betweenness_centrality(graph)
    budget = protocol["budget"]
    selections = {"none": [], "all": eligible,
                  "degree": rank_nodes(degree, eligible)[:budget],
                  "betweenness": rank_nodes(between, eligible)[:budget]}
    if behavior["informative"]:
        ranked = sorted(eligible, key=lambda n: (-behavior["nodes"][n]["placement_score"], -degree[n], n))
        selections["behavior"] = ranked[:budget]
    else:
        selections["behavior"] = selections["degree"].copy()
    for index, subset in enumerate(random_placements(eligible, budget, protocol["random_draws"], protocol["random_placement_seed"] + source)):
        selections[f"random_{index}"] = subset
    return {name: sorted(selection) for name, selection in selections.items()}
