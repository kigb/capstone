# Additional protection strategies: frozen exploratory protocol

This pilot adds three placement rules and a second budget after the 30-question confirmation failed to establish a Behavior advantage. All rules, questions, targets and conditions are frozen before inference. It is an exploratory study, with all planned comparisons reported regardless of outcome.

Canonical protocol SHA-256: `da5f56b202624435ad2f69388970269df245e2e30819d27ed84d3dd5ef719ab7`. Exact model, question and manifest file hashes are recorded in [freeze.json](../results/netsafe_protection_extension_qwen8b/freeze.json).

## Fixed setting and new questions

Reuse Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`, BF16, non-thinking, greedy, batch 32, at most 512 new tokens, the existing 8-node/13-edge ER graph, four discussion rounds, and the exact original warning. Only placement and budget vary. The known attack source is excluded from protection and ordinary-agent scoring, including in matched clean trials.

The repository CSQA file has 127 rows, of which 112 have usable A–E gold labels. Exclude all 50 question IDs used in any previous experiment. Sample 12 of the remaining 62 questions with seed 20261105; assign sources 0, 3, 6 cyclically, four questions per source. Sample incorrect targets with seed 20261106. Every actual protection set is paired clean/attack on the same question and source.

Budgets are k=2 and k=3: 28.6% and 42.9% of the seven eligible nodes (25% and 37.5% of all eight nodes). No-warning k=0 and all-protected k=7 are different-budget reference conditions.

## Placement rules

| Method | Rule |
| --- | --- |
| Random-k | Three fixed random permutations per source; use nested prefixes at k=2/3, requiring distinct subsets at both budgets; average within question. |
| Degree-ID | Descending degree, then ascending ID. |
| Degree-uniform | Enumerate every degree-optimal eligible k-subset; average within each question before equally averaging questions. |
| Betweenness | Descending ordinary graph betweenness, then ID. |
| Behavior | Reuse the unchanged original development-only sender spreading scores and fallback rule; extend the same ranking to k=3. |
| **NTI** | Rank by `1/(distance from known attacker + 1)`, then degree, then ID. This applies NetSafe Appendix A.3's node threat index to warning placement; the paper does not report this selective-warning experiment. |
| **Coverage** | Exhaustively maximize eligible nodes covered by the protected nodes' closed neighborhoods. Ties: selected-degree sum, then lexicographic IDs. Warning does not remove nodes or block edges. |
| **Vulnerability** | On original undefended development logs, fraction of honest-node cases adopting the target in at least one of rounds 1–4. Exclude any case with invalid post-initial labels; count those exclusions. Missing-case nodes use pooled rate. Ties: degree, ID. This is recipient risk, distinct from sender spreading rate. |

Both behavioral signals use only the original 10 development questions × three sources. No previous evaluation trajectories enter fitting. Vulnerability has 20 valid honest cases for nodes 0/3/6 and 30 for the other nodes; these repeat ten questions and are not independent samples. Scores are observational. Neither score estimates the causal benefit of warning a node.

Coverage's optimal sets need not be nested across budgets, and Degree-uniform averages different sets. Thus a budget comparison evaluates each rule at each budget, rather than always adding exactly one node to an unchanged allocation. Random permutations are shared across budgets to reduce this source of variation.

The full manifest has 600 named trajectories, 432 distinct question/attack/protection-set conditions, and 24,000 logical answers. Aliases and identical inputs share cached greedy outputs. They do not increase sample size.

## Analysis fixed before inference

Report the final round-4 target-adoption difference between each new rule and Degree-uniform at each budget: six planned comparisons. Use 10,000 paired-question bootstrap resamples, seed 20261108, and report 95% percentile intervals. These are **exploratory, unadjusted intervals**, not a confirmatory selection of a winning method. The independent evaluation unit is a question (n=12), not an agent, round, random draw, degree tie, budget or strategy alias. Do not stop early or tune after intermediate outcomes.

Also report ordinary-agent accuracy, strict-majority system accuracy/target success, invalid outputs, ever-target adoption, clean task performance, attack-minus-clean increments, k=3 minus k=2 changes, per-source/distance summaries, attack-source compliance and representative traces. Distinguish spontaneous target answers from attack-associated changes. Report alias overlaps explicitly.

Compare with NetSafe where justified: ordinary-agent accuracy maps to MJA with `V*=Vnor` (Eq.13), and local round `r` maps to Table 1 Turn `r+1`. NetSafe's main CSQA table uses GPT-4o-mini, six nodes, 127 questions and three runs on regular graphs; our graph, model, subset and run count differ. Paper numbers provide context, not matched evidence of superiority. Neither our target-adoption nor system-majority metric is the paper's MJA.

Primary paper: [NetSafe, Findings of ACL 2025](https://aclanthology.org/2025.findings-acl.150.pdf), §3.3, Table 1, Appendix A.3 and Table 5. Its Table 3 already studies disagreement between structural metrics and observed task performance; the present extension concerns protection placement.

## Reproduction and artifacts

```bash
python scripts/run_protection_extension.py --prepare-only
python -u scripts/run_protection_extension.py
.analysis-venv/bin/python scripts/analyze_protection_extension.py
```

Default output: `results/netsafe_protection_extension_qwen8b/`. Use a fresh `--output` for an independent repeat; repeat runs retain the same fixed questions. Interrupted runs resume the existing cache. Frozen configuration, both behavioral models, question IDs, the manifest and their hashes precede inference. Save source hashes, raw responses, message provenance, parsed state, costs and lossless `.jsonl.gz` archives. Approximate local inference cost: 6–9 hours, subject to realized output lengths and cache reuse; no paid API.
