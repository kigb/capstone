# Four-question method screen (2026-11-10)

This is a small exploratory method screen, not a confirmation experiment. Rules,
questions, targets, sets and contrasts are frozen before inference. Report every
method; do not tune or stop based on the screening outcomes.

## Scope

Reuse Qwen3-8B, fixed revision, BF16 non-thinking greedy, the eight-node ER graph,
four discussion rounds, the identical warning, and budget k=2. Attacker nodes are
excluded from protection and scoring in both matched clean and attack conditions.
No-warning, Degree-uniform, NTI and the original Behavior remain controls. This
compact screen omits extra budgets, random draws and all-protected conditions.

Exclude all 62 previously used question IDs. From 50 remaining valid-label CSQA
questions, sample four using seed 20261110. Each question is crossed with sources
0, 3 and 6. One fixed incorrect target per question (seed 20261111) is shared
across sources and methods. The independent question count is **four, not twelve**.
These questions become screening data and cannot later be called fresh confirmation
data for a method chosen using their outcomes.

## Methods

| Method | Fixed rule |
| --- | --- |
| Risk-product | Source-conditioned frequency of newly adopting the target, excluding initial target and invalid cases, multiplied by shrunk sender transition rate and degree. |
| Edge-flow | Sum the weights of simple source paths visiting each node; select the top two. Path weight is the product of fitted directed-edge transition rates, over paths of length 1–4. |
| Edge-cover | Jointly select two nodes maximizing `sum_path weight * (1 - 0.5^number_of_protected_nodes_on_path)`. Exhaustively search all eligible pairs. |
| Uniform-cover | Same joint objective, replacing each edge rate by the pooled edge rate. Controls for the value of edge-specific behavioral information. |
| Intervention-ridge | Fit a source-specific additive ridge surrogate for how a two-node warning set changes attack-minus-clean target adoption relative to no warning; select the pair with lowest predicted change. |

Risk-product and path methods use only the original ten undefended development
questions × three sources. Fractional edge credit is divided over all simultaneous
target senders, including the attacker; invalid recipient next states are excluded.
Node sender rates continue to exclude attackers. A fixed pseudo-count of three
shrinks rates toward their pooled values. These are descriptive scores, not
independent Bayesian observations or causal transmission probabilities.

Intervention-ridge alone repurposes the earlier **30-question confirmation data
as training data**. Only k=0/2 conditions enter; repeated method aliases are removed.
Each question contributes total weight one regardless of its number of distinct
sets. Fit no-intercept weighted ridge with fixed lambda=1 per source. Historical
question IDs, unique training rows, coefficients and matrix ranks are saved.
Rank deficiency and limited assignment coverage prevent causal interpretation of
individual coefficients. No hyperparameter selection occurs on the new four questions.
Earlier evaluation results are not held-out evidence for this newly fitted method.

The assumed path residual 0.5 is an uncalibrated placement heuristic, **not a measured
warning efficacy**. Path sums are not normalized infection probabilities. Warnings
never remove nodes or edges. Ties use degree then ID; intervention ties use source
distance, degree then ID. Numerical selection ties are rounded to 12 decimals.

## Pre-inference overlap audit

The frozen rules produce 256 named trajectories but only 120 distinct
question/source/attack/protected-set conditions: 10,240 logical answers. Identical
messages share greedy outputs, and identical placements are explicitly reported.
In this graph Edge-flow and Edge-cover select the same pair for every source;
they are equivalent policies in this screen, not independent corroboration.
Most new rules overlap Behavior at sources 3/6; source 0 provides more separation.
This structural limitation is disclosed before model inference, without changing
rules to force favorable results.

## Analysis

Final r4 target adoption and ordinary-agent accuracy are primary descriptions.
Also report attack-minus-clean target changes, clean accuracy, strict-majority
target success, ever-target states, invalid labels and attack-source compliance.

Average degree ties **within question/source**; then average sources **within
question**; finally average the four questions equally. Report all four per-question
effects and all source-specific results. Do not treat nodes, sources, aliases or
rounds as independent test samples. With n=4, report no formal confidence intervals
or winning-method claims. Prespecified contrasts: all five added method names
minus Degree-uniform, plus Edge-cover minus Uniform-cover. Include failed cases.

Keep the full NetSafe message/update mechanics and original parser; audit raw
labels, cache/dialogue alignment, neighbor-message provenance, clean/attack initial
agreement, aliases, fitting provenance and frozen hashes. Preserve lossless raw
`.jsonl.gz` archives and code hashes. The models and data are local; no paid API.

```bash
python scripts/run_method_screen.py --prepare-only --output results/screen_repeat
python -u scripts/run_method_screen.py --output results/screen_repeat
.analysis-venv/bin/python scripts/analyze_method_screen.py --input results/screen_repeat
```

Default artifacts: `results/netsafe_method_screen_qwen8b/`. Use a fresh directory
for an independent rerun; repeated fixed questions do not add independent evidence.
