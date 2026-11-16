"""Export the slide content and HTML speaker notes as readable Markdown."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / "capstone_slides_zh.md").read_text()
body = re.sub(r"\A---\n.*?\n---\n", "", source, count=1, flags=re.S)
slides = re.split(r"\n---\s*\n", body)
output = [
    "# MIIS Capstone：完整讲解稿\n",
    "本文件从 [分页 Markdown](capstone_slides_zh.md) 自动生成，包含全部投影片内容和讲解备注，适合在 GitHub 上阅读。",
    "编辑分页源文件后运行 `python docs/build_reading_version.py` 更新；转换 PPT / PDF 的说明见 [使用指南](README.md)。\n",
    "## 内容索引\n",
]
for index, slide in enumerate(slides, 1):
    title = re.search(r"^# (.+)$", slide, re.M)
    assert title, "Every slide must have a title"
    output.append(f"- [{title.group(1)}](#page-{index:02d})")
output.append("\n---\n")
for index, slide in enumerate(slides, 1):
    comments = re.findall(r"<!--(.*?)-->", slide, re.S)
    notes = [s.strip() for s in comments if not re.match(r"\s*_?\w+\s*:", s)]
    # Chinese '讲解：' uses a full-width colon and is retained as speaker notes.
    assert len(notes) == 1, "Each slide must have one speaker-note block"
    content = re.sub(r"<!--.*?-->\s*", "", slide, flags=re.S).strip()
    content = re.sub(r"^(#{1,5}) ", r"\1# ", content, flags=re.M)
    content = re.sub(r"!\[w:[^\]]*\]", "![讲解图]", content)
    output.extend([f'<a id="page-{index:02d}"></a>', content, "\n### 讲解备注\n", notes[0], "\n---\n"])
(HERE / "capstone_walkthrough_zh.md").write_text("\n\n".join(output).rstrip() + "\n")
print(f"Exported {len(slides)} slides with speaker notes")
