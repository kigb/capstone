# MIIS Capstone — NetSafe 本地基线

研究问题：在只能保护部分 LLM agent 的情况下，按网络度数还是按观察到的传播行为选择保护节点更有效？完整设计见 [研究方案](selective_vaccination_proposal.md)。

本分支包含 NetSafe 的本地推理适配、Qwen2.5-3B-Instruct / Qwen3-8B 两轮 pilot、8B 四轮延长实验，以及固定预算下 Random-k / Degree-k / Betweenness-k / Behavior-k 的选点比较。原始输出、分析代码和中文报告一并保存。推理在 NVIDIA GB10 上完成，不需要付费模型 API。

## 最新：固定预算选点结果

8 节点、4 轮讨论、10 道独立测试题，保护预算 k=2（7 个普通节点的 28.6%）。Behavior 分数由另外 10 道开发题的日志估计，并在测试前冻结。

| 策略 | 攻击下准确率 | 目标采纳率 ↓ | Clean 准确率 |
| --- | ---: | ---: | ---: |
| 无 warning | 41.4% | 18.6% | 60.0% |
| Random-k（3 个集合平均） | 39.5% | 20.5% | 60.0% |
| Degree-k | 45.7% | 15.7% | 60.0% |
| Betweenness-k | 35.7% | 24.3% | 60.0% |
| Behavior-k | 50.0% | 10.0% | 60.0% |
| 全部保护（7 个节点，参考组） | 50.0% | 10.0% | 60.0% |

**Behavior 的点估计较好，但尚未确认稳定优势。** 相对 Degree，目标采纳率差为 −5.7 个百分点，题目配对的 95% bootstrap 区间为 [−14.3, +1.4]。Behavior `{2,4}` 和 Degree `{1,2}` 的差别涉及度数并列；需要补充随机打破度数并列的对照。行为分数达到观测门槛的覆盖率为 4/8，不能把未观测节点当成低风险。

研究耗时 4 小时 35 分 18 秒，完成 7,600 个逻辑回答、5,148 个实际独立生成，全部符合格式且没有截断。Random 先在题目内部平均，统计样本量仍为 10 道题。完整设置、区间、逐题收益与失败案例见 [选点实验中文报告](results/netsafe_placement_qwen8b/report_zh.md)。

![固定预算比较](results/netsafe_placement_qwen8b/placement_comparison.png)

## 两轮模型 pilot

两次运行使用相同的 10 道 CSQA、6 节点树、攻击位置和目标选项；每次都是 4 个条件、初始回答加 2 轮讨论，共 720 个逻辑回答。每组最终评价 5 个普通节点，共 50 个答案。

| 条件 | 3B 准确率 | 8B 准确率 | 3B 目标采纳率 | 8B 目标采纳率 |
| --- | --- | --- | --- | --- |
| 无攻击、无 warning | 68% | 76% | 0% | 0% |
| 有攻击、无 warning | 46% | 68% | 14% | 4% |
| 有攻击、加 warning | 28% | 72% | 18% | 4% |
| 无攻击、加 warning | 42% | 74% | 4% | 0% |

8B 的 720 个回答全部符合上游格式，没有无效答案或截断；正式运行耗时 31 分 48 秒，PyTorch 峰值 GPU 分配 17.30 GiB。3B 各组最终无效答案率为 24%–46%，会影响准确率和后续交互。模型代际与参数量同时改变，这不是参数量的独立因果比较。

8B 中 warning 没有降低目标采纳率；准确率增加全部来自一道题。这些是小样本开发结果，不能据此确认疫苗有效或某种选点策略更优。

- [8B 完整报告及 3B 对比](results/netsafe_qwen8b_baseline/report_zh.md)
- [3B 完整报告](results/netsafe_qwen3b_baseline/report_zh.md)
- [模型对比 CSV](results/netsafe_qwen8b_baseline/model_comparison.csv)

![3B 与 8B 对比](results/netsafe_qwen8b_baseline/model_comparison.png)

## 克隆

```bash
git clone --branch baseline_netsafe --recurse-submodules https://github.com/kigb/capstone.git
cd capstone
```

如果已经克隆但未初始化子模块：

```bash
git submodule update --init --recursive
```

`third_party/NetSafe` 指向 [官方 NetSafe](https://github.com/Ymm-cll/NetSafe) 的 commit `551d396d105c00a191ddb51a7c603da99551c766`。本地脚本复用其 Agent、AgentGraph、提示和数据；上游源码未修改，许可证见 [NetSafe/LICENSE](third_party/NetSafe/LICENSE)。

## 环境

推理使用已有的 CUDA PyTorch 环境。本次实际版本为 Python 3.12.3、PyTorch 2.10.0+cu130、Transformers 4.57.6；完整信息记录在各实验的 `summary_runtime.json`。在已安装适配 GPU 的 PyTorch 的环境中，安装其余依赖：

```bash
python -m pip install -r requirements-inference.txt
```

本机已验证的推理解释器是 `/home/yixiong/workspace/.venv/bin/python`，可替换下文的 `python`。该绝对路径仅适用于原实验服务器。

分析单独使用 CPU 环境，不需要模型权重或 GPU：

```bash
python3 -m venv .analysis-venv
.analysis-venv/bin/python -m pip install -r requirements-analysis.txt
```

## 下载权重

模型权重和虚拟环境没有提交。原实验服务器已有缓存；新机器首次运行需下载对应的固定 revision。运行器本身设置 `local_files_only=True`，不会自动下载权重。

Qwen3-8B（权重约 15.26 GiB）：

```bash
python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="Qwen/Qwen3-8B",
    revision="b968826d9c46dd6066d109eabc6255188de91218",
    allow_patterns=["*.json", "*.safetensors", "*.jinja", "*.txt", "tokenizer.model"],
)
PY
```

若运行 3B，把下载参数替换为 `Qwen/Qwen2.5-3B-Instruct` 与 revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`。

## 运行与分析

在项目根目录执行，使用新输出目录以保留已完成的结果：

```bash
python scripts/run_local_baseline.py \
  --model Qwen/Qwen3-8B \
  --revision b968826d9c46dd6066d109eabc6255188de91218 \
  --disable-thinking \
  --output results/qwen8b_repeat

.analysis-venv/bin/python scripts/analyze_local_baseline.py \
  --input results/qwen8b_repeat

.analysis-venv/bin/python scripts/compare_model_baselines.py \
  --reference results/netsafe_qwen3b_baseline \
  --candidate results/qwen8b_repeat
```

3B 的对应命令：

```bash
python scripts/run_local_baseline.py \
  --model Qwen/Qwen2.5-3B-Instruct \
  --revision aa8e72537993ba99e69dfaafa59ed015b17504d1 \
  --output results/qwen3b_repeat
```

默认参数是 10 题、seed 20261101、batch size 8、每次最多生成 512 tokens。`--prepare-only` 只生成配置和题目，不加载模型；`scripts/probe_local_model.py` 可执行一次短 GPU 推理。比较脚本要求两组采用相同实验设置，除模型及模型特定模板参数外不允许配置差异。

只复核已提交结果，无需重跑模型：

```bash
.analysis-venv/bin/python scripts/analyze_local_baseline.py \
  --input results/netsafe_qwen8b_baseline
.analysis-venv/bin/python scripts/compare_model_baselines.py
```

分析命令会重写指定目录中的统计与图表；原始轨迹与生成缓存不会改变。

## 四轮延长与固定预算选点实验

后续实验的模型、图、题目划分、预算、传播分数和分析规则事先记录在 [实验协议](experiments/placement_protocol.md)。机器可读的 [protocol.json](results/netsafe_placement_qwen8b/protocol.json) 在开发和评价推理前提交。

[四轮延长报告](results/netsafe_qwen8b_round4_pilot/report_zh.md)：保留原先全部 720 个逻辑回答，继续两轮后观察到二跳目标采纳和恢复。无 warning 的最终目标采纳率从 4% 升到 6%，全部普通节点加 warning 时从 4% 升到 10%；这批开发题未验证 warning 的保护收益。

先沿用原 8B 轨迹，增加两轮讨论：

```bash
python scripts/run_local_baseline.py \
  --model Qwen/Qwen3-8B \
  --revision b968826d9c46dd6066d109eabc6255188de91218 \
  --disable-thinking --discussion-rounds 4 \
  --reuse-generations-from results/netsafe_qwen8b_baseline \
  --output results/qwen8b_round4_repeat

.analysis-venv/bin/python scripts/analyze_local_baseline.py \
  --input results/qwen8b_round4_repeat
.analysis-venv/bin/python scripts/analyze_round_extension.py \
  --extended results/qwen8b_round4_repeat
```

选点实验使用固定 8 节点图、4 轮讨论和 k=2 的保护预算（7 个可保护普通节点的 28.6%）。比较 Random-k（3 个随机集合）、Degree-k、Betweenness-k、Behavior-k，以及无防御和全部保护参考组；每个集合都配对 clean/attack。开发集是先前 10 道 pilot 题 × 3 个攻击位置，评价集为 10 道不重叠的新题。详细分数定义、覆盖不足处理和限制以协议为准。

```bash
# 配置预检，不加载模型
python scripts/run_placement_study.py --prepare-only --output results/placement_repeat

# 顺序执行开发、冻结 Behavior 分数、评价；中断后可用同一目录恢复缓存
python scripts/run_placement_study.py --output results/placement_repeat

.analysis-venv/bin/python scripts/analyze_placement_study.py \
  --input results/placement_repeat
```

也可以用 `--phase development` 和 `--phase evaluation` 分阶段执行。运行器要求评价前已有完整开发结果，并保存冻结分数及每个条件的保护集合。重复执行使用同一套固定题目，不构成新的独立测试集。

规则测试：

```bash
.analysis-venv/bin/python -m unittest discover -s tests -v
```

测试覆盖攻击源排除、多发送者曝光分摊、无效输出、评价数据禁止用于拟合、预算一致性、行为证据不足时的明确 fallback，以及随机集合在题目内部的平均。两组历史结果另做了分析回归检查，统计保持不变。

## 文件与实验口径

| 路径 | 内容 |
| --- | --- |
| `scripts/run_local_baseline.py` | 上游交互适配、批量本地推理、固定 warning、缓存与轨迹 |
| `scripts/probe_local_model.py` | 短推理与硬件可运行性检查 |
| `scripts/analyze_local_baseline.py` | 计分验证、按题目配对 bootstrap、图表 |
| `scripts/compare_model_baselines.py` | 匹配设置检查与 3B/8B 对比 |
| `scripts/run_placement_study.py` | 冻结协议、开发轨迹、行为评分和独立题目评价 |
| `scripts/placement_common.py` | 图结构、传播分数和保护集合规则 |
| `scripts/analyze_placement_study.py` | 配对统计、泄漏/缓存验证、度数并列诊断和图表 |
| `results/netsafe_qwen3b_baseline/` | 3B 正式结果、报告和完整记录 |
| `results/netsafe_qwen8b_baseline/` | 8B 正式结果、报告和完整记录 |
| `results/netsafe_qwen8b_round4_pilot/` | 原 8B pilot 延长到四轮的结果和报告 |
| `results/netsafe_placement_qwen8b/` | 固定预算选点实验、冻结评分、评价配置和完整记录 |
| `results/netsafe_qwen3b_pilot/` | 最初的格式诊断；不是正式实验组 |
| `results/netsafe_qwen8b_baseline/sampling_diagnostic/` | 停止的采样配置诊断；其生成未用于正式 8B 结果 |

两轮和四轮延长 pilot 使用 6 节点树、攻击源 0，warning 组保护全部 5 个普通节点。选点实验使用另外的 8 节点图、攻击位置 0/3/6 和 k=2 预算；攻击源从保护候选和评分中排除。所有攻击均是每轮持续为指定错误选项辩护，不是一次注入后的自复制攻击。相同输入的 greedy 输出会缓存复用，不能将复用记录当成独立模型样本。统计抽样单位是题目，而不是同一轨迹中的节点或轮次。

运行器显式使用 `use_model_defaults=False, do_sample=False`，并核验有效生成模式，避免模型默认设置把 greedy 改成采样。该问题的诊断和排除过程见 [8B 报告](results/netsafe_qwen8b_baseline/report_zh.md)。
