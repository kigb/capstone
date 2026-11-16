# 研究讲解文档与 slides 素材

这套材料以 **2026-11-16** 为文献核验日，以实验 commit [`8c44942`](https://github.com/kigb/capstone/commit/8c44942543df41467af45f37291b7a93491a60b3) 为结果依据。本次新增文档、解释与图表，没有新增 GPU 实验。

## 从哪里开始看

| 文件 | 用途 |
| --- | --- |
| **[完整中文讲解稿](capstone_walkthrough_zh.md)** | 推荐先读。包含每页要点和详细讲解备注，可在 GitHub 直接阅读。 |
| **[可转 PPT 的分页 Markdown](capstone_slides_zh.md)** | Marp 格式，共 44 页；用 `---` 分页，HTML 注释存放演讲备注。 |
| **[PDF 排版预览](capstone_slides_zh.pdf)** | 查看页面、公式、表格和图的实际样式。 |
| **[文献核验清单](literature_review_zh.md)** | 11 篇文献的原文、版本、定位、检索范围与贡献边界。 |
| [图表目录](assets/) | 从已有协议和结果生成的网络图、评分覆盖图、30 题结果图。 |

内容覆盖研究动机、威胁模型、文献调研、Behavior 计算、degree 并列、全部已跑阶段、新增五种规则、与 NetSafe 的比较、局限和下一步。所有页都有讲解备注。分页文件里的备注在 GitHub 默认隐藏，因此另生成了可读讲解稿。

**当前结论**：已经实现自己的 Behavior 方法和扩展，但 30 题确认实验未证实它优于 Degree-uniform；四题筛选中的多个 0% 也未确认新方法更好。文档保留所有关键负向结果及不确定性，避免 slides 误写成“我们的方法最好”。

## 如何缩成实际汇报

44 页是详细素材库，可以按讲述时间删减，正文不必全部使用。

**15 分钟 / 18 页建议顺序：**01、03、04、05、07、11、13、14、17、19、21、24、25、27、29、33、36、37。

大致时间分配：研究问题 2 分钟、文献与定位 2 分钟、方法与设计 4 分钟、主结果与探索 4 分钟、论文比较 / 局限 / 下一步 3 分钟。其他页保留作备答，尤其 18 的评分覆盖、32 的统计规则、38–40 的方法细节和 42–44 的参考文献。

**导师讨论 / 30–40 分钟版本：**使用 01–37，按兴趣补充方法附录。讲结果时先讲 30 题主比较，再谈 12 题和 4 题探索，不把跨批次百分比画成连续进步曲线。

## 编辑与转换

主要编辑 [capstone_slides_zh.md](capstone_slides_zh.md)。首部 YAML 定义 16:9 画幅与样式；`---` 是分页符；每页末尾 `<!-- ... -->` 为讲解备注。公式采用 KaTeX，图片用相对路径链接 `assets/`。

编辑后从仓库根目录同步可读版：

```bash
python docs/build_reading_version.py
```

可用 VS Code 的 Marp 扩展预览，或使用 CLI。下面固定为本次使用的 **Marp CLI 4.2.3 / Marp Core 4.4.0**，本次运行环境为 Node.js 18.19.1。PDF / PPTX 导出需要本机安装受支持的浏览器；普通 HTML 转换不需要浏览器。功能依据 [Marp CLI 官方文档](https://github.com/marp-team/marp-cli/blob/main/README.md)。

从仓库根目录运行：

```bash
# HTML 预览：与 Markdown 放在同一目录，保持相对图片路径有效。
npx --yes @marp-team/marp-cli@4.2.3 docs/capstone_slides_zh.md \
  -o docs/capstone_slides_zh.html

# PDF；本地图片来自本仓库。
npx --yes @marp-team/marp-cli@4.2.3 docs/capstone_slides_zh.md \
  --pdf --allow-local-files -o docs/capstone_slides_zh.pdf

# PPTX。
npx --yes @marp-team/marp-cli@4.2.3 docs/capstone_slides_zh.md \
  --pptx --allow-local-files -o docs/capstone_slides_zh.pptx

# 单独导出演讲备注。
npx --yes @marp-team/marp-cli@4.2.3 docs/capstone_slides_zh.md \
  --notes -o docs/capstone_notes.txt
```

**PPTX 编辑方式**：默认导出每页为图片，适合直接展示；要改文字和布局，建议改 Markdown 后重新导出。本机有 LibreOffice Impress 时可尝试 `--pptx --pptx-editable`，但它是实验功能，版式可能变化且不保留演讲备注；本文没有验证该编辑模式。见[官方可编辑 PPTX 说明](https://github.com/marp-team/marp-cli/blob/main/README.md#experimental-generate-editable-pptx---pptx-editable)。

如果你准备在 PowerPoint 中重新设计，使用完整讲解稿复制每页要点，图片从 `assets/` 单独插入，会更方便。正文中的相对仓库链接在 GitHub 上可直接跳转；离线导出文件若单独移动，源码 / 报告相对链接仍需原仓库目录结构，或在最终 slides 中改为 GitHub URL。

本服务器使用 Snap Firefox，默认 `/tmp` 中的浏览器 profile 不可见。实际导出 PDF 时使用了可见的任务临时目录和 `--browser firefox`：

```bash
mkdir -p /home/yixiong/school/capstone-render-tmp
TMPDIR=/home/yixiong/school/capstone-render-tmp \
  npx --yes @marp-team/marp-cli@4.2.3 docs/capstone_slides_zh.md \
  --pdf --allow-local-files --browser firefox \
  -o docs/capstone_slides_zh.pdf
```

这条服务器专用命令无需设置模型 API key；字体采用系统已有的 Noto Sans CJK SC。其他机器可直接用上面的通用命令。

## 图表与结果追溯

重建三个演示图，仅需 CPU 分析环境中的 matplotlib / networkx：

```bash
.analysis-venv/bin/python docs/build_assets.py
```

| 图 | 来源 |
| --- | --- |
| `assets/network.png` | `results/netsafe_confirmation_qwen8b/protocol.json` 的实际邻接矩阵 |
| `assets/behavior_support.png` | `results/netsafe_placement_qwen8b/behavior_model.json` 的曝光、支持标记与选点分数 |
| `assets/confirmation.png` | `results/netsafe_confirmation_qwen8b/metrics.csv` 的 r4、attack、题目等权目标率 |

各阶段的表格与统计推断，以对应中文报告、CSV 和原始记录为准：

- [早期 10 题选点](../results/netsafe_placement_qwen8b/report_zh.md)
- [30 题确认](../results/netsafe_confirmation_qwen8b/report_zh.md)
- [12 题、两档预算扩展](../results/netsafe_protection_extension_qwen8b/report_zh.md)
- [4 题方法筛选](../results/netsafe_method_screen_qwen8b/report_zh.md)
- [NetSafe 原论文数值核验](../experiments/netsafe_paper_reference.json)

本次验证包括 Markdown 转换、44 页浏览器布局与图片加载检查、PDF 页面检查，以及关键数值与已提交结果的核对。没有重新运行模型、改写历史结果或将探索数据合并为确认样本。
