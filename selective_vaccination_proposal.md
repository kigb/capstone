# MIIS Capstone — Selective Vaccination in Multi-Agent Networks

## Research motivation

Multi-agent LLM systems exchange information through communication networks. A highly connected agent is not necessarily the most influential: some messages are adopted downstream, while others are simply relayed or ignored. This motivates a practical question: **when only a subset of agents can be protected, should we select them by graph structure or by observed spreading behavior?**

This direction builds on Katia's *Immunity for Agent Networks* proposal and the October 19 discussion of influential agents versus high-degree relays.

## Research question

**Central research question:** When does network topology fail to capture the actual propagation risk in LLM multi-agent systems, and can behavior-informed vaccination address this mismatch?

**RQ1 — Understanding topology–behavior mismatch:** To what extent do structural importance and observed misinformation spreading diverge across agents? When do high-degree agents have limited downstream impact, while lower-degree agents exert stronger influence through their messages?

**RQ2 — Implications for targeted defense:** Does this mismatch affect which agents should be protected under a fixed defense budget? Can observed spreading behavior improve vaccination placement compared with degree-based and random selection?

**Hypothesis:** Because receiving a message does not imply adopting or forwarding it, structural centrality alone may miss behaviorally influential agents. Accounting for observed spread can improve how limited protection resources are allocated.

## Novelty & Research Gap

**Core distinction: Budget-aware vaccination is the problem setting; behavior-informed vaccination placement is the proposed contribution.**

### What is already known?

- **Network topology matters.** NetSafe compares multi-agent graph topologies and reports that attacker distance is predictive of system safety. Simply comparing topologies is not new.
- **Selective security resource allocation exists.** MAS-Shield prioritizes critical nodes for *auditing*, rather than preemptively installing the same vaccine on a limited number of agents.
- **Vaccination / warning prompts exist.** Mind Viruses examines prompt-based protection against contagious agent behavior. We reuse a fixed defense, rather than proposing a new one.
- **Budgeted immunization and influence-aware targeting have long histories** in network epidemiology. Therefore, “protect hubs rather than random nodes” is not itself a novel algorithm.

### What is the specific open empirical question?

**Does a behavior-based estimate of an LLM agent's realized spreading tendency provide useful protection-placement information *beyond structural degree* under the same vaccine and the same budget?**

This matters because an edge indicates the opportunity to communicate, not necessarily that a receiver will adopt or act on a misleading message. Two agents with similar connectivity may have different downstream influence due to message content, task role, credibility, or recipient behavior.

### Proposed contributions

1. **Behavior-aware placement signal:** Calculate an empirical spreading score from undefended development trajectories, without requiring model training or additional causal-ablation rollouts.
2. **Controlled allocation comparison:** Compare random, degree-based, and observed-spreading-based placement while holding vaccine, graph, model, attack, and number of protected agents constant.
3. **Characterize topology–behavior mismatch and its defensive implications:** Measure ranking agreement (Spearman and top-k overlap), examine attack-source distance, and test whether ranking differences translate into meaningful changes in downstream compromise.

**Illustrative distinction:** Agent A has ten outgoing neighbors but usually changes only one recipient's answer; Agent B has three neighbors whose answers are frequently shifted. Degree prioritizes A; observed spreading may prioritize B. The experiment tests whether this distinction translates into lower system-wide attack success after vaccination.

### Novelty assessment

**Our literature review has not identified a paper that performs this exact three-way comparison of fixed-vaccine placement using observed LLM-agent spreading scores on held-out attacks.** The closest work covers topology (NetSafe), selective auditing (MAS-Shield), or the vaccine mechanism (Mind Viruses). A 2026 cross-layer contagion study also considers analytical defense-budget allocation, highlighting that budget optimization alone is not novel.

**Our contribution:** We study the gap between structural connectivity and realized information spread in LLM-agent networks, then use that insight to guide budget-constrained vaccination. This connects a measurable network-level phenomenon—topology–behavior mismatch—to a practical defense decision: which agents should receive protection.

## Related work

| Work | Relevance |
| --- | --- |
| NetSafe (2024) · code | Network topology and multi-agent safety; proposed baseline |
| Prompt Infection (2024) | Propagation of prompt infection |
| Mind Viruses (2026) | Propagation dynamics and warning-prompt defense |
| MAS-Shield (2025 preprint) | Critical-agent selection for auditing |
| Peigné et al. (2025) vaccination, discussed here | Memory/prompt vaccination precedent; locate and verify original paper for final bibliography |

**Our focus:** First characterize when graph-based importance disagrees with observed spreading behavior (RQ1), then test whether those differences matter for allocating a fixed vaccine budget (RQ2). The two analyses reuse the same baseline trajectories and experiment framework.

## Proposed approach

**Framework:** NetSafe, with one supported attack setting and one random or scale-free network. We will use a fixed lightweight warning/prompt vaccine for protected agents, varying only which agents receive it.

**Selection strategies**

1. **Random:** sample k agents uniformly, repeating random draws.
2. **Degree-based:** choose k high-degree agents (out-degree for a directed communication graph when applicable).
3. **Empirical spreading score:** estimate from undefended development runs how often downstream neighbors become affected after an agent's exposure, normalized by observation opportunities; select top-k.

The empirical score is an observational measure, not a causal attribution. We will use message provenance when available.

**Experiment design**

- **Graph:** one nontrivial random or scale-free topology (avoid trivial star networks).
- **Attack:** one existing NetSafe attack scenario, across several attacker injection positions.
- **Outcome:** define the attacked/affected state based on NetSafe's actual interaction mechanics; if agents are repeatedly sent malicious content, measure adoption of attacker-targeted incorrect answers rather than assuming self-replication.
- **Budget:** 0%, 20%, and 40% of nodes protected, adjusted for the graph size and pilot.
- **Split:** compute spreading rankings using development runs and evaluate vaccination on held-out attack seeds or locations.
- **Metrics:** affected-agent fraction / attack-target adoption, attack success rate, clean task accuracy, and variation across runs.
- **Analysis:** correlate degree and spreading rankings (Spearman and top-k overlap); examine whether distance to the attacker explains the observed spread.

## Expected outcomes

Two connected sets of findings: **(RQ1)** a characterization of when degree and observed spreading behavior diverge, using rank correlation, top-k overlap, and representative traces; and **(RQ2)** a controlled comparison of vaccination placements under matched budgets, including downstream attack impact and clean-task performance. Both analyses build on a reproduced NetSafe baseline.

Our goal is a focused empirical study and initial results for the early-December MIIS capstone presentation.

## Five-week timeline

| Week | Milestone |
| --- | --- |
| **1 — Baseline + pilot** | Run NetSafe, inspect messages and outcome labels, test a fixed vaccine, collect logs, and estimate API cost. Check degree/spreading-score rank correlation and top-k overlap. |
| **2 — Methods** | Implement random and degree placement, then compute spreading scores from undefended development logs. |
| **3 — Evaluation** | Evaluate all three strategies on held-out attack positions/seeds and fixed budgets. |
| **4 — Analysis** | Repeat manageable seeds, check budget sensitivity, analyze representative traces and clean-task impact. |
| **5 — Presentation** | Final figures, findings, and presentation. |

**Implementation considerations:** Use the Week 1 pilot to pick a network where the two rankings can meaningfully differ, confirm vaccination has a measurable effect, and estimate total calls across budgets × attack locations × seeds × random draws. Keep the experiment matrix compact.

## Questions for Katia

1. Does selective vaccination under a fixed budget seem like a promising focus?
2. Is NetSafe a good starting point, or would another benchmark be preferable?
3. Do the two linked questions—characterizing topology–behavior mismatch and testing its effect on selective vaccination—capture the right research focus for our capstone?
4. Which attack setting or downstream outcome would you prioritize?

## Next steps

- [ ] Discuss and confirm the direction with Katia.
- [ ] Confirm team participants and responsibilities.
- [ ] Reproduce one NetSafe attack configuration and inspect its logs.
- [ ] Define the vaccine, outcome metric, development/evaluation split, and budget.
- [ ] Run a pilot and finalize the experiment matrix.

---

## 中文解读与 baseline 建议（2026-11-01）

> 上方保留原始 proposal；以下是补充解读、代码核查和实验建议，不代表已经完成实验或验证假设。

### 1. 这个项目在设计什么？

这是一个关于 **LLM 多智能体网络中的防御资源分配** 的实证研究。设多个 agent 沿固定网络交流，一个攻击者持续输出误导信息。你只能给其中 k 个可保护 agent 加上同一段防御提示，研究问题就是：**应该保护谁，才能让整个系统少受影响？**

这里的 vaccine 是预先放入 agent 系统提示或记忆中的固定防御文本，不涉及训练模型。实验中的主要自变量是被保护的节点集合；模型、图、任务、攻击目标、交互轮数、疫苗文本和保护人数应保持一致。

例如，10 个可保护 agent 中只能保护 2 个：random 随机选 2 个，degree 选连接最多的 2 个，behavior 选开发集日志中最容易伴随下游错误采纳的 2 个。然后在未用于排序的新题目、攻击位置或随机条件上比较结果。10 个可保护节点之外是否另设攻击源，必须在威胁模型中说明。

两个研究问题依次回答：

1. **RQ1：连接多和实际传播多是否一致？** 比较 degree 排名与 spreading score 排名，报告 Spearman、top-k overlap 和代表性对话。
2. **RQ2：这种差异有没有防御价值？** 看 behavior 选点是否在相同预算下减少攻击目标采纳，同时保住正常任务准确率。

RQ1 的排名不同本身不能证明 RQ2 成立；传播活跃的节点也未必是加入该疫苗后最能改善全局结果的节点。这个联系需要实际防御实验检验。没有提升、或者只在特定条件下提升，也可以是研究结果。

### 2. 最值得先跑的实验框架：NetSafe + CSQA

**建议从 NetSafe 的 CSQA 多选题误导攻击开始。** 这是基于代码结构和评价便利性给出的建议，尚未实测。每题有正确选项，代码另外随机选择一个错误选项交给攻击者，方便区分“答错”与“采纳攻击者指定答案”。入口是 [run_csqa.py](https://github.com/Ymm-cll/NetSafe/blob/main/run_csqa.py)。

核查到的运行特点：

- 攻击者在初始化及后续讨论中持续接收辩护错误选项的任务；普通 agent 每轮读取邻居上一轮的答案与理由。因此该设置适合研究**持续误导源下的错误答案传播/采纳**，不能直接描述成一次注入后的攻击自复制。
- 仓库保存各 agent 的对话，输入中保留发送者编号，可用于重建一轮到下一轮的曝光与答案变化。正式实验还应显式保存图、攻击目标选项、攻击者编号、保护集合和全部随机种子。
- `sample_id` 主要用于输出路径，不能当成已经控制了随机种子。代码有全局 `random.seed(42)`，但多线程下题目与随机目标选项的对应仍需明确固定。
- 原始输出路径区分攻击者数量，但没有充分区分攻击位置与防御策略；新增实验时应使用独立运行 ID，避免结果混入同一文件。

以上依据：[CSQA 实现](https://github.com/Ymm-cll/NetSafe/blob/main/run_csqa.py)。

拓扑方面，[methods.py](https://github.com/Ymm-cll/NetSafe/blob/main/methods.py) 提供 `complete`、`tree`、`chain`、`star`、`circle`，目前没有 random 或 scale-free 图生成器。其 `star` 实现还连接外围节点，实际带有外围环，不能默认当成纯星形图。先用内置 `tree` 跑通流程，再添加固定 seed 的随机图或 Barabási–Albert 图；小规模 BA 图应称为该生成机制下的图，不据此声称验证了幂律性质。

### 3. 应该比较哪些 baseline？

以下是建议在同一个 NetSafe 实验框架内实现的实验组；原仓库没有提供完整的选择性 vaccination 比较。

| 实验组 | 设置 | 用途 | 优先级 |
| --- | --- | --- | --- |
| Clean / no defense | 无攻击、无疫苗 | 测正常任务能力 | 必跑 |
| Attacked / no defense | 有攻击、k=0 | 测攻击是否有效，也是开发集传播分数的数据来源 | 必跑 |
| Random-k | 同一疫苗，随机保护 k 个节点，多次抽样 | 最基本的选点 baseline | 必跑 |
| Degree-k | 同一疫苗，保护 degree 最大的 k 个节点 | 核心结构 baseline；有向图明确用 out-degree | 必跑 |
| Behavior-k | 同一疫苗，保护开发集传播分数最高的 k 个节点 | 你们提出的方法 | 必跑 |
| All-protected | 所有可保护节点都加同一疫苗 | 检查疫苗在当前任务中是否有效；不属于相同预算比较，也不是理论上界 | pilot 必跑 |
| Betweenness-k | 同一疫苗，保护最常位于最短路径上的 k 个节点 | 检查提升是否只是 degree 太简单 | 建议至少补一个更强结构 baseline |
| MAS-Shield-inspired structural score | 用归一化 degree、betweenness、closeness 的组合选 k 个节点，再加同一疫苗 | 与已有关键节点选择思想对齐 | 可选，作为结构 baseline 的替代/补充 |

MAS-Shield 的节点重要性分数确实组合了三种中心性，但其完整方法还包括审计和回溯。如果仅复用选点分数，应标为 **MAS-Shield-inspired placement**，不能称为复现完整 MAS-Shield。参见[论文方法与附录 E](https://arxiv.org/html/2511.22924v3)。

Random、Degree、Behavior 以及选定的额外结构策略，都应补相同保护集合下的无攻击实验，用于测 clean accuracy 的变化。100% 保护只需作为参考组，不必对每种策略重复运行。

### 4. 第一轮怎么跑，以及需要改哪些地方？

建议按以下顺序执行，先限制规模，再扩大矩阵：

1. **最小运行：** 从 CSQA 取 5–10 道题，使用内置 tree、约 6 个 agent、初始化后 2 轮交流，分别跑无攻击与 1 个攻击者。此阶段只验证运行、输出与标签，不用于得出统计结论。
2. **验证疫苗：** 在相同任务上跑所有可保护节点加疫苗，确认有可测的保护作用，并观察无攻击准确率是否下降。若疫苗在此任务中没有效果，应先处理这个问题。
3. **补正式实验接口：** 支持自定义邻接矩阵、`protected_nodes`、固定疫苗、独立随机种子、预先生成的错误目标选项、显式攻击者集合和结构化日志。
4. **开发集：** 在预先规定的图与若干攻击位置上采集无防御轨迹，计算并冻结 behavior 排名、疫苗和所有超参数。
5. **测试集：** 对相同的测试题、图、目标答案、攻击位置和轮数，配对比较各选点策略在 20% 与 40% 预算下的结果。k=0 是共享对照。至少保留未参与开发的题目；攻击位置是否也留出，取决于要声称哪一种泛化。

仓库级准备命令如下，仅供后续复现；本次没有安装依赖或调用模型：

```bash
git clone https://github.com/Ymm-cll/NetSafe.git
cd NetSafe
python3 -m venv .venv
source .venv/bin/activate
python -m pip install openai numpy tqdm networkx
```

这些依赖根据所读运行与评价文件的 imports 汇总，尚未做兼容性测试。[当前 methods.py](https://github.com/Ymm-cll/NetSafe/blob/main/methods.py) 从环境变量 `OPENAI_API_KEY` 读取 key；[README](https://github.com/Ymm-cll/NetSafe/blob/main/README.md) 中要求改源码写 key 的说明与当前实现不同。模型名称需选账户可用的型号，并在各组固定；源码默认名称不等于已经验证当前账户可调用。

运行前，在 `run_csqa.py` 的 `run_dataset` 中将数据限制为少量题目，并在底部配置 `graph_type="tree"`、`p=1`、`reg_turn=2`、`num_agents=6`、`attacker_nums=[0, 1]`，再执行：

```bash
python run_csqa.py
```

`p=1` 降低的是题目并发；每题内部仍会并发请求各 agent。不要直接把默认运行规模当成小样本 pilot。统一入口 [run.py](https://github.com/Ymm-cll/NetSafe/blob/main/run.py) 的当前默认设置是 bias 数据、多个图与节点数、0 个攻击者，也不是本方案建议的起点。

评价代码也需要改：[evaluate.py](https://github.com/Ymm-cll/NetSafe/blob/main/evaluate.py) 的 CSQA `MJA` 分支按记录顺序跳过前若干 agent，这依赖攻击者恰好排在前面。换攻击位置后必须按显式攻击者 ID 排除；它计算的逐轮正确率也不能直接替代指定错误选项的采纳率。答案解析失败应单独计数并报告，不应默认为未受攻击影响。

粗略调用量可以先按下式估计，再用 pilot 的真实 token 用量计算费用：

```text
单个配置的请求数 ≈ 题目数 × 总 agent 数 × (1 + 交流轮数)
总请求数 ≈ 单配置请求数 × 实际配置数量
```

总 agent 数包含攻击者；配置数量包含预算、保护集合、攻击位置和重复运行，另外计算开发集、clean 对照与重试。Random 的多个保护集合会增加配置数。

### 5. 传播分数和评价还需要明确什么？

**一个可实现的初始定义（建议，尚未验证）：** 对 i→j 的每次实际消息投递，要求 i 的答案支持攻击目标、j 投递前未采纳该目标；观察 j 下一轮是否改成目标答案。用“出现这种转变的次数 / 合格曝光机会数”作为 i 的观测传播率。发送者只是收到过错误信息但未在消息中支持它，不宜直接算成传播机会。

这个分数衡量的是每次曝光的转变率，不能等同于节点带来的总影响。应同时报告分子、分母、总下游转变数；预先规定最少样本数、零曝光节点处理、平滑和并列排名规则，避免 1 次成功 / 1 次曝光排在充分观测的节点之前。`degree × 传播率` 可作为后续消融，但不能在看过测试结果后临时选分数。

同一接收者可能同时读到多个发送者的答案，无法仅凭日志判定谁导致转变。可以预先约定对 m 个支持目标答案的发送者各记 1/m 份转变，并做敏感性检查；这依旧是观察性归因。来源标注、时间先后和更细日志都不会自动建立因果关系。

建议预先固定以下结果口径：

- **Agent-level target adoption：** 最终一轮诚实 agent 中，回答攻击目标选项的比例；另报告逐轮轨迹或首次采纳。
- **System-level ASR：** 例如，预先定义由诚实 agent 多数投票得到系统答案，系统选择目标错误选项的题目比例；并列票与无效答案必须有固定处理规则。这是建议新增的口径，不是已确认的 NetSafe 默认聚合规则。
- **Clean accuracy：** 同样保护集合、同样任务、无攻击时的准确率。攻击下的正常答题准确率也应另报。
- **不确定性：** 报告配对差值及适当的区间；同一条轨迹内的节点和轮次不是独立样本，不能把它们当作大量独立重复。

另外有四个设计边界：

1. **预算与候选集合。** 明确预算分母是总节点还是可保护的诚实节点；完全由攻击者控制的源节点是否允许被保护。若按当前攻击位置排除节点，这可能透露攻击源信息，需说明威胁模型，且所有策略使用相同信息。
2. **距离混杂。** 高传播分数可能只是在识别靠近攻击源的节点。应分层分析距离，或补距离 baseline；如果真实部署不知道源位置，使用真实测试源位置的 baseline 必须标为 oracle 诊断。
3. **不要按测试收益挑图。** Pilot 可以用于开发，但图生成与选择规则须在测试前固定；若刻意选择排名差异大的图，结论仅适用于这个筛选条件。可保留一个低差异图作为对照。
4. **结论范围。** 只打败 degree，只支持“优于 degree”；若要讨论更广泛的拓扑局限，建议加一个更强的结构 baseline。小图上的 ties、样本噪声也会影响 Spearman 与 top-k overlap，必须报告。

### 6. 其他论文和代码应怎样使用？

| 工作 | 已核查来源 | 在本项目中的建议用途 |
| --- | --- | --- |
| NetSafe | [Findings of ACL 2025 正式版](https://aclanthology.org/2025.findings-acl.150/)；[官方代码](https://github.com/Ymm-cll/NetSafe) | 首选运行框架。2024 是预印本年份，正式文献表可引用 2025 版本 |
| Mind Viruses | [论文](https://arxiv.org/abs/2608.10218)；[Virus Chain 代码](https://github.com/frotaur/mindvirus-viruschain)；[Coding agent 代码](https://github.com/BucketofJava/mind-virus-code-agent) | 研究自传播或借鉴 warning defense。Virus Chain 的 README 要求 uv、Docker 与模型 API，且提醒多轮多跳成本；迁移到固定图选点实验需要额外工程 |
| MAS-Shield | [论文及版本记录](https://arxiv.org/abs/2511.22924) | 可参考结构选点分数。完整审计机制改变了防御本身，不能直接替代固定疫苗的公平选点比较；本次未核实可运行官方仓库 |
| Peigné et al., Multi-Agent Security Tax | [原始论文](https://arxiv.org/abs/2502.19145) | 已找到原文：研究虚构安全处理经历的记忆疫苗与安全指令，以及防御对协作能力的影响。可补全原 proposal 中待查引用；不应把记忆疫苗与简单 warning 混为同一个实现 |
| Prompt Infection | [原始论文](https://arxiv.org/abs/2410.07283) | 自复制 prompt injection 与 LLM Tagging 的相关工作。切换到其攻击/防御会改变实验机制，本次未核实可直接运行的官方仓库 |

原 proposal 的“尚未发现精确三方比较”应保留为有范围的文献检索结论，不能当成已经证明的新颖性。本次核查也不是穷尽检索；其中未具名的 “2026 cross-layer contagion study” 仍需补作者、标题和链接。

**当前完成状态：** 已保存 proposal、核查上述论文与关键代码入口，并给出可执行的实验路线；尚未复现实验、实现 placement 或获得效果数据。
