# 文献核验、研究定位与引用清单

核验日期：**2026-11-16**。这是一份围绕当前 capstone 的定向调研，不是穷尽性系统综述。逐篇讲解与项目关联见[完整讲解稿](capstone_walkthrough_zh.md)第 05–11、33–34、42–44 页；这里保留版本、原文定位与引用边界，便于制作 slides 时核对。

## 检索范围和方法

从原提案中的 NetSafe、Prompt Infection、Mind Viruses、MAS-Shield、Peigné vaccination 出发，核对论文原文，再补充网络影响 / 免疫基础与接近“行为防御”的工作。使用 arXiv、ACL Anthology、出版商页面和作者论文 PDF；搜索结果和二手介绍只用于找到原文，不作为实验数字的依据。

本次检索的代表性关键词包括：

- `multi-agent LLM vaccination warning prompt defense`
- `multi-agent vaccination selection prompt`
- `LLM immunization influence agents selection`
- `multi-agent behavior-informed defense`
- `Peigné vaccination multi-agent security tax`
- 各篇完整标题，以及 NetSafe 的 NTI、MJA、dynamic influence。

纳入标准：直接涉及 LLM 多智能体传播、针对 agent 的防御或资源分配，或提供网络选点的经典背景。生物疫苗意愿、医疗接种建议等同词异义结果不纳入；MedSentry 纳入是因为它研究 **LLM agent 的安全防御**，不是因为医疗任务本身。

检索没有发现与本仓库“无防御日志拟合传播率 + 固定 warning + 固定 k + held-out 题目 + 完整 degree 并列对照”完全相同的组合。**这不能证明没有相关工作，更不能据此声称首次。** 后续应继续补充引用链与相近实验，特别是预算限制下的行为选点。

## 原文与定位

| 编号 | 文献信息与核验版本 | 原文定位 / 本文使用范围 |
| --- | --- | --- |
| R1 | David Kempe, Jon Kleinberg, Éva Tardos. **Maximizing the Spread of Influence through a Social Network.** KDD 2003. [作者论文 PDF](https://snap.stanford.edu/class/cs224w-readings/kempe03influence.pdf) | 扩散模型与影响最大化的理论背景；不将其近似保证套到当前 warning 实验。 |
| R2 | Reuven Cohen, Shlomo Havlin, Daniel ben-Avraham. **Efficient Immunization Strategies for Computer Networks and Populations.** *Physical Review Letters* 91, 247901, 2003. DOI: [10.1103/PhysRevLett.91.247901](https://doi.org/10.1103/PhysRevLett.91.247901). [预印本](https://arxiv.org/abs/cond-mat/0207387) | Acquaintance immunization；预印本提交于 2002，正式出版为 2003。 |
| R3 | Miao Yu et al. **NetSafe: Exploring the Topological Safety of Multi-agent System.** *Findings of ACL 2025*, 2905–2938. [正式论文](https://aclanthology.org/2025.findings-acl.150/) · [官方 BibTeX](https://aclanthology.org/2025.findings-acl.150.bib) | Table 1：CSQA 数值背景；Table 3：结构 / 动态排名；Eq. 13：MJA；Appendix A.3：NTI；Table 5：生成配置。 |
| R4 | Donghyun Lee, Mo Tiwari. **Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems.** arXiv:2410.07283v1, 2024-10-09. [原文](https://arxiv.org/abs/2410.07283) | Abstract：自复制提示感染与 LLM Tagging；未将其攻击或防御记为本项目已复现。 |
| R5 | Tianjie Ju et al. **Flooding Spread of Manipulated Knowledge in LLM-Based Multi-Agent Communities.** arXiv:2407.07791v2, 2024-07-23. 期刊信息：*Science China Information Sciences* 69, 172103, 2026. [原文](https://arxiv.org/abs/2407.07791) · [期刊 DOI](https://doi.org/10.1007/s11432-024-4663-2) | 本文核验 arXiv 摘要及其所列期刊信息；仅引用知识操纵 / 传播机制，不引用未核对的期刊实验表格。 |
| R6 | Pierre Peigné et al. **Multi-Agent Security Tax: Trading Off Security and Collaboration Capabilities in Multi-Agent Systems.** arXiv:2502.19145v2, 2025-06-04；初版 2025-02-26. [原文](https://arxiv.org/html/2502.19145v2) | Abstract、Figure 1、§3.1 Defense mechanisms：记忆 vaccination、一般安全指令与协作权衡；原提案的 Peigné 文献已定位。 |
| R7 | Vassilis Papadopoulos, McNair Shah, Sam Zimmerman, Jack Lindsey. **Mind Viruses: Self-Propagating Ideas in Multi-Agent LLM Systems.** arXiv:2608.10218v1, 2026-08-10. [原文](https://arxiv.org/abs/2608.10218) | Abstract：自传播想法与其设置下的 warning 结果；不把效果外推为通用免疫保证。 |
| R8 | Kaixiang Wang et al. **MAS-Shield: A Defense Framework for Secure and Efficient LLM MAS.** arXiv:2511.22924，初版 2025-11-28；核验 v3，2026-09-17. [原文](https://arxiv.org/html/2511.22924v3) | §3.1：归一化 degree / betweenness / closeness 相加选点与回溯；§3.2–3.3：分层审计。当前仓库没有复现完整系统。 |
| R9 | Kai Chen et al. **MedSentry: Understanding and Mitigating Safety Risks in Medical LLM Multi-Agent Systems.** arXiv:2505.20824v1, 2025-05-27. [原文](https://arxiv.org/abs/2505.20824) | Abstract：医疗 MAS 的风险评估与恶意 agent 检测 / 纠正；用于约束宽泛的行为防御 novelty 声明。 |
| R10 | Tran Duc Le, Truong Duy Dinh, Thi Le Quyen Nguyen, Cong Danh Nguyen. **Cross-layer contagion of prompt injections in multi-agent swarms: a multiplex microscopic markov chain approach.** *Cybersecurity* 9, 191, 2026-07-16. [出版商原文](https://link.springer.com/article/10.1186/s42400-026-00628-w) | Abstract：agent / tool 两层 MMCA 和防御效率假设下的预算规则；不是本项目的 LLM rollout 实证。 |
| R11 | Alon Talmor, Jonathan Herzig, Nicholas Lourie, Jonathan Berant. **CommonsenseQA: A Question Answering Challenge Targeting Commonsense Knowledge.** NAACL-HLT 2019, 4149–4158. [正式论文](https://aclanthology.org/N19-1421/) | 任务数据的来源。当前 127 行 / 112 个有效标签是上游仓库子集，不是完整数据集规模。 |

## 对原提案的四个实质性修正

1. **NetSafe 的正式出版年份为 2025。** 不能把原提案的“2024”直接作为正式会议引用；也不能把一般结构与行为差异视为完全无人研究。
2. **Peigné 文献已找到原始论文。** 本仓库的普通 warning 不等同于其中的虚构安全记忆 vaccination。
3. **行为防御、关键节点防御、预算优化已有研究。** MAS-Shield、MedSentry 和跨层模型使我们的贡献必须落在具体的受控比较上。
4. **原提案是假设，结果并未确认它。** 当前更合适的标题和摘要强调“检验行为信息的额外价值”，而不是“更优的行为感知保护算法”。

初始 [proposal](../selective_vaccination_proposal.md) 保留为历史设计文件；新的讲解稿明确区分原计划、实际实现、当前结果与待做工作。特别注意：NetSafe Table 3 的排名单位是**不同拓扑**，本项目 RQ1 的排名单位是**同一图中的节点**；相关研究动机不等于两者做了同一实验。

## 哪些可以叫 baseline，哪些不能？

| 本仓库已运行 | 与文献的关系 | 合理称呼 |
| --- | --- | --- |
| 本地 NetSafe 机制 + Qwen3-8B | 复用官方交互并适配模型 / 图 / 题目 | NetSafe-based local baseline；不是原表格精确复现 |
| Random、Degree-uniform、Betweenness | 常用分配对照 | 结构 / 随机 baseline |
| NTI | 使用 NetSafe 距离指标思想 | 源已知的距离 baseline |
| 固定 warning | 相关文献提供动机，文本自写 | 本实验固定干预；不是 Mind Viruses 或记忆 vaccine 完整复现 |
| Behavior、Risk-product、路径与 ridge 规则 | 本项目的评分实现 / 探索性扩展 | 候选方法；效果需要独立评价 |
| 未运行 MAS-Shield / MedSentry 完整系统 | 审计或纠正行动、信息和成本不同 | related work；不能写成已经比较过的性能 baseline |

## 推荐的研究定位表述

> We test whether observational spreading scores estimated from undefended development trajectories provide additional information for allocating a fixed warning prompt under a fixed node budget, beyond structural degree. In our current Qwen3-8B / ER-graph setting, the held-out confirmation experiment does not establish an advantage of the original behavioral score over a degree baseline that averages all tied top-k selections.

这段英文描述研究问题及当前结果，不声称首次，不把相关论文的机制或性能归为我们的成果。主结果与证据限制详见[30 题确认报告](../results/netsafe_confirmation_qwen8b/report_zh.md)。
