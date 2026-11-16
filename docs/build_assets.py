"""Rebuild presentation figures from committed results; no inference required."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 14,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none", "figure.facecolor": "white"})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


protocol = json.loads((ROOT / "results/netsafe_confirmation_qwen8b/protocol.json").read_text())
g = nx.Graph()
g.add_nodes_from(range(len(protocol["adjacency"])))
g.add_edges_from((i, j) for i, row in enumerate(protocol["adjacency"])
                 for j, value in enumerate(row) if value and i < j)
fig, ax = plt.subplots(figsize=(9.5, 4.1))
pos = nx.spring_layout(g, seed=21)
nx.draw_networkx_edges(g, pos, ax=ax, width=2, edge_color="#afbac7")
nx.draw_networkx_nodes(g, pos, ax=ax, node_color=["#087f8c" if n in [2, 4] else "#e1e7ef" for n in g], node_size=1000)
for n, (x, y) in pos.items():
    ax.text(x, y, str(n), ha="center", va="center", fontsize=20,
            color="white" if n in [2, 4] else "#14283e", weight="bold")
ax.set_title("Fixed ER graph: 8 nodes, 13 edges | Behavior selects {2, 4}", pad=16)
ax.set_axis_off()
save(fig, "network")

rows = list(csv.DictReader((ROOT / "results/netsafe_confirmation_qwen8b/metrics.csv").open()))
order = ["none", "random", "degree", "degree_uniform", "betweenness", "behavior", "all"]
names = ["No warning (k=0)", "Random", "Degree-ID", "Degree-uniform", "Betweenness", "Behavior", "All (k=7)"]
values = [100 * float(next(r["target_rate"] for r in rows if r["strategy"] == s and r["attack_enabled"] == "True" and r["round"] == "4")) for s in order]
fig, ax = plt.subplots(figsize=(11, 4.4))
colors = ["#abb6c4", "#67829f", "#67829f", "#234b70", "#67829f", "#087f8c", "#abb6c4"]
bars = ax.barh(names[::-1], values[::-1], color=colors[::-1], height=.65)
ax.bar_label(bars, labels=[f"{v:.2f}%" for v in values[::-1]], padding=7, fontsize=13)
ax.set_xlim(0, 27)
ax.set_xlabel("Final target adoption (%) — lower is better")
ax.set_title("30-question confirmation | k=2 except references", loc="left", pad=15)
ax.grid(axis="x", alpha=.15)
ax.set_axisbelow(True)
save(fig, "confirmation")

model = json.loads((ROOT / "results/netsafe_placement_qwen8b/behavior_model.json").read_text())["model"]
fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
nodes = model["nodes"]
opps = [nodes[str(n)]["opportunities"] for n in range(8)]
axes[0].bar(range(8), opps, color=["#087f8c" if nodes[str(n)]["supported"] else "#b5beca" for n in range(8)])
axes[0].axhline(3, color="#d77831", linestyle="--", linewidth=1.5)
axes[0].set(xlabel="Node ID", ylabel="Weighted exposure opportunities", xticks=range(8), title="Only 4 / 8 nodes meet support >= 3")
for n in range(8):
    node = nodes[str(n)]
    supported = node["supported"]
    axes[1].scatter(g.degree[n], node["placement_score"], marker="o" if supported else "x", s=80,
                    color="#087f8c" if supported else "#7e8999")
    axes[1].annotate(str(n), (g.degree[n], node["placement_score"]), xytext=(5, 5), textcoords="offset points")
axes[1].set(xlabel="Degree", ylabel="Placement score", title="Supported ranks: Spearman +0.632", ylim=(.15, .48))
axes[1].text(.03, .02, "x = imputed score; not measured immunity", transform=axes[1].transAxes, fontsize=10)
fig.tight_layout(w_pad=3)
save(fig, "behavior_support")

print(f"Built 3 figures in {OUT.relative_to(ROOT)}")
