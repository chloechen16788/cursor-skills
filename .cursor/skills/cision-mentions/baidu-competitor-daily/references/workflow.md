# 运行工作流（百度竞品同业日报）

端到端步骤。所有脚本在 `scripts/`，纯 Python，需要 `openpyxl` 与 `python-docx`。

## 0. 环境

```bash
pip install openpyxl python-docx
```

若系统 Python 缺 openpyxl，用工作区自带的 venv：

```bash
~/.workbuddy/binaries/python/envs/default/bin/python -c "import openpyxl, docx; print('ok')"
```

## 1. 输入与产物

```
delta.csv ──csv_to_delta.py──> delta.xlsx (sheet "delta")
delta.xlsx + 翻译知识库.xlsx
  → filter3.py           → candidates.json
  → curation.py          → curated.json
  → prep_final.py        → final.json
  → make_zh_template.py  → zh_template.json
  → [翻译] zh.json
  → build_doc.py         → 报告.docx
```

- **原始数据**：监测导出。CSV 或 XLSX 均可；必需列 `title/source/locationCountry/languageCode/url/
  publishedAt/excerpt/keywords/author/content/impactScore`。CSV 通常没有 `content`，正文在 `transcript`。
- **翻译知识库**：`assets/翻译知识库.xlsx`，三张表「媒体名称知识库 / 品牌名称翻译知识库 / 领导人名称翻译知识库」，一一对应。

> 本技能只收录**媒体白名单内**的媒体。加媒体要改 KB，不是改脚本。

## 2. 逐步执行

下列路径请替换为实际路径。`$PY` 为 Python 解释器，`$SK` 为 `scripts/` 目录。

**Step 0 — CSV 转 XLSX（输入已是 xlsx 可跳过）**
```bash
$PY $SK/csv_to_delta.py --input delta.csv --out delta.xlsx
```
`transcript` 自动映射为 `content`，列集合固定。输出会打印行数与所用正文字段。

**Step 1 — 候选过滤**
```bash
$PY $SK/filter3.py --input delta.xlsx --kb 翻译知识库.xlsx --out candidates.json --drops drops.json
```
打印 `CANDIDATE COUNT` 与各板块命中。期望量级：500 余条原始 → 200 余条候选。
若某板块异常膨胀（如 Microsoft 上百条），检查别名是否过宽或关键词是否污染。

`--drops` 可选但**强烈建议**：把每条被剔稿件、剔除原因、命中品牌与 `cn_tech` 标记写入 json，
并按原因聚合打印。用户问「这条为什么没收录」时先看它，不要靠猜。

启动日志里另有两类 `WARNING`，出现即需处理：
- `SRC_TO_KB 指向不存在的媒体` —— 映射写错，该写法不会生效。
- `知识库里这些品牌没有对应的别名表条目` —— 有译名但收不进来，补 `filter3.py` 别名表
  （`Cruise` / `Robotaxi` / `Cybercab` 属预期跳过）。

**Step 2 — 归属唯一化 + 去重 + 评分**
```bash
$PY $SK/curation.py --candidates candidates.json --raw delta.xlsx --out curated.json
```
不设品牌配额，因此 `SELECTED COUNT` 应接近 `CANDIDATE COUNT`（差额仅为去重所得）。
打印 `TRANSLATION LIST` 供抽查。

**Step 3 — 排序编号（默认不做事件级去重）**
```bash
$PY $SK/prep_final.py --input curated.json --out final.json
```
打印 `TRANSLATION LIST (idx | media_kb | section | entity | title)`；**该 idx 顺序即报告顺序**。

**默认口径：不同媒体对同一事件的报道全部保留**，只剔除「同一篇稿的重复副本」
（URL 相同、标题完全相同、同一媒体改题重发）——这三道在 Step 2 的 `curation` 里已完成。

可选参数：
- `--event-dedup`：启用事件级去重，同一事件只留代表稿（报告更紧凑，会丢弃同一事件的其他媒体角度）。
- `--per-event N`：配合 `--event-dedup`，同一事件保留几条，默认 1。

**Step 4 — 翻译模板**
```bash
$PY $SK/make_zh_template.py --final final.json --out zh_template.json
```
每项含 `idx / media_kb / section / entity / en / zh(空)`。

**Step 5 — 翻译**
把每项 `zh` 填成中文标题，另存 `zh.json`（`{idx: 中文}` 字典亦可）。
- 标题级翻译即可，不读正文。
- **`AI` 不翻译**：一律写 `AI`，不写「人工智能」；`AI agent`→`AI 智能体`、`AI chip`→`AI 芯片`。
  `LLM`/`GPU`/`AGI` 同样保留原文。AI 与中文之间留空格（`AI 智能体`），与既有排版一致。
- **但公司名里的 AI 按知识库译**：`Z.AI`/`Z.ai` → **智谱**、`01.AI` → 零一万物、`Pony.AI` → 小马智行。
  例：`Z.ai launches GLM-5 AI model` → 「智谱发布 GLM-5 AI 模型」。产品名保留原文
  （`GLM-5`、`ChatGLM`、`ChatGPT`、`Claude`、`Apple Intelligence`）。
- 品牌名一律用《翻译知识库》中文名，中文行不残留 `Google`/`Huawei`/`Zhipu` 这类英文写法。
  KB 中文名本身就是英文的（OpenAI、Anthropic、Meta、IBM、TikTok、MiniMax）与品类词 `Robotaxi` 例外。
- 媒体名、领导人名必须与《翻译知识库》一致；`build_doc` 会自动套用 KB 标准译名，
  并替换中文行里残留的英文全名。
- 若条目顺序有微调，可用「规范化英文标题 → 旧中文」映射复用旧译文，再按新 `idx` 回填。
  务必确认每个 `idx` 都有值再生成文档。

**Step 5b — 译文规范校验（必跑）**
```bash
$PY $SK/check_zh.py --zh zh.json --template zh_template.json --kb 翻译知识库.xlsx
```
`error` 必须为 0，否则改完再跑。它会拦三类问题：
「人工智能」（应写 `AI`）、中文行残留英文品牌名（含 `Z.AI` 应译「智谱」）、`AI` 与中文之间缺空格。
复核历史稿件时加 `--soft`，只报告不阻断。

**Step 6 — 生成 Word**
```bash
$PY $SK/build_doc.py \
  --final final.json --zh zh.json --kb 翻译知识库.xlsx \
  --raw-count 540 \
  --out "百度海外舆情日报_竞品与领导人.docx"
```
`--raw-count` 仅用于副标题「原始记录 N 条」。

## 3. 收尾自检

脚本能保证结构，内容质量仍需人工判断：

- [ ] 每条英文行有 **3 个 `<w:hyperlink>`**（媒体名 / 冒号 / 标题），全部英文行合计 = final 条数 × 3。
      `word/_rels/document.xml.rels` 的 `http` 条目数 ≈ final 条数（同一 URL 复用同一 rId）。
- [ ] 英文行冒号为半角 `: `，中文行为全角 `：`。
- [ ] 条目文字全部加粗（英文行三段 + 中文行两段），文档大标题亦为粗体。
- [ ] 三个一级标题齐全，顺序为 国内竞品 → 自动驾驶竞品 → 海外竞品（每节均「含领导人」）。
- [ ] 领导人条目已归入其所属品牌（不再单列「企业领导人」板块）。
- [ ] 英文媒体标签全部是 KB 媒体名，无野生媒体。
- [ ] 媒体中文名已本地化（如 Reuters→路透社、BNN Bloomberg→BNN彭博社），不是英文。
- [ ] 中文行无残留英文领导人全名（如 `Sam Altman` 应已是「萨姆·奥尔特曼」）。
- [ ] `check_zh.py` 通过（error 0）：无「人工智能」、无残留英文品牌名、`AI` 与中文间有空格。
- [ ] 领导人板块 H2 为「中文名（英文名｜公司）」。
- [ ] 新闻稿残留为 0。
- [ ] 促销/折扣稿（`$X off`、Black Friday、Prime Day）为 0。
- [ ] Apple TV+ 剧集/电影稿为 0。
- [ ] 纯股价涨跌快讯为 0（含 memory/margin 等实质议题的股价稿应保留）。
- [ ] 含 moonshot 的条目已核：公司（大写 M）保留，「登月计划」已剔。
- [ ] 同一品牌下同一事件的报道相邻（学校政策/财报/Robotaxi/债券发行各自成段）。
- [ ] 同一事件的多家报道均保留（除非本次明确启用了 `--event-dedup`）。
- [ ] 无标题粘连/乱码条目。
- [ ] 抽查 5–10 条：确为竞品情报，而非股评、消费评测、生活杂讯。

## 4. 知识库维护

新增/修正媒体、品牌、领导人译名，编辑 `assets/翻译知识库.xlsx`，再用 `consolidate_kb.py` 整理：

```bash
$PY $SK/consolidate_kb.py --src 待整理.xlsx --out 翻译知识库.xlsx
```

脚本做「一一对应」校验（同一中文不得对应多个英文），并拆出独立领导人表。

**加媒体后必须回归验证**：即使名字进了 KB，也可能被其他闸门挡掉（历史上被「重点市场」静默丢弃的
案例见 `pitfalls.md` #30）。用一篇已知稿件跑一遍，确认它真的出现在 `final.json` 里。

## 5. 定时运行

`cision-mentions` 的定时流水线最后一步仍是上一级 `scripts/publish_daily_report.py`，不要停在 `build_doc.py`。它只用副本应用清空并重写 `https://jcn5bws14c2g.feishu.cn/wiki/DoXTwxbK1iX60yk282AcEN5Mn0e`，不写 `https://prnewswire.feishu.cn/wiki/PP88weeBdi1Pcgkmpxbc48lSn5e`。`--after` 和 `--raw-count` 仍必传。群消息带上海数据日期和副本链接，Word 由本目录 `build_doc.py` 生成后发到同一群。定时导出已经有 `content` 列，不要插入 `csv_to_delta.py`。`check_zh.py` 在发布前跑，error 必须为 0。没有条目的栏目不印标题。
