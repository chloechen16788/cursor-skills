# 运行工作流（百度竞品同业日报）

本文件描述筛选到翻译的步骤。筛选脚本位于 `scripts/`，需 `openpyxl`。定时运行的最后一步不是 Word，而是上一级 `scripts/publish_daily_report.py`：清空并重写固定飞书文档，再把上海数据日期和 wiki 链接发到固定群。

## 0. 环境准备

```bash
pip install openpyxl
```

## 1. 输入与产物概览

```
delta-bodies.xlsx  ──┐
                     ├─> filter3.py ──> candidates.json
翻译知识库.xlsx  ─────┘
candidates.json + delta-bodies.xlsx ──> curation.py ──> curated.json
curated.json ──> prep_final.py ──> final.json
final.json ──> make_zh_template.py ──> zh_template.json
zh_template.json +（按标题填写 zh.json）+ 翻译知识库.xlsx ──> publish_daily_report.py ──> 飞书文档 + 群链接
```

- 定时运行的原始数据是 `delta-bodies.xlsx`（工作表名 `delta`，字段含 title/source/url/locationCountry/languageCode/keywords/impactScore/excerpt/author/content/publishedAt）。
- 若手头只有 CSV、正文在 `transcript`，先转成同一张表再进入筛选。定时流水线已经有 `content` 列，不要插这一步。

```bash
python scripts/csv_to_delta.py --input delta.csv --out delta.xlsx
```

- 翻译知识库：`翻译知识库.xlsx`，含「媒体名称知识库 / 品牌名称翻译知识库 / 领导人名称翻译知识库」三表（一一对应）。
- 只收录媒体白名单内的媒体。加媒体改知识库，不改导出命令。

## 2. 逐步执行

> 说明：以下命令中的路径请替换为实际文件路径。脚本已参数化，不再写死绝对路径。

**Step 1 — 候选过滤**
```bash
python scripts/filter3.py \
  --input "/path/delta-bodies.xlsx" \
  --kb   "/path/翻译知识库.xlsx" \
  --out  candidates.json
```
输出 `CANDIDATE COUNT` 及各板块命中统计。归属只看标题。媒体已在知识库里的，不因所在国被丢掉。

**Step 2 — 优先级评分 + 唯一归属 + 去重**
```bash
python scripts/curation.py \
  --candidates candidates.json \
  --raw "/path/delta-bodies.xlsx" \
  --out curated.json
```
不设品牌配额。`SELECTED COUNT` 与候选数的差额来自去重，不是限额。`pscore` 只排序，不决定是否收录。终端会打印 `TRANSLATION LIST`。

**Step 3 — URL / 同题去重 + 排序编号**
```bash
python scripts/prep_final.py --input curated.json --out final.json
```
打印 `TRANSLATION LIST (idx | media_kb | section | entity | title)`，**此清单的 idx 顺序即最终报告顺序**。
默认同一家媒体的重复稿会去掉，不同媒体对同一事件的报道都保留。需要收成每个事件一条时再加 `--event-dedup`，并用 `--per-event N` 改保留条数。定时命令不要加这个参数。

**Step 4 — 生成翻译模板**
```bash
python scripts/make_zh_template.py --final final.json --out zh_template.json
```
得到 `zh_template.json`：每项含 `idx / media_kb / section / entity / en / zh(空)`。

**Step 5 — 人工翻译**
将 `zh_template.json` 中每项的 `"zh"` 填为中文标题，另存为 `zh.json`。
- 翻译口径：标题级翻译即可，不必读正文。
- 领导人中文名、媒体中文名**必须**与《翻译知识库》一一对应（发布脚本会套用 KB 标准译名，并替换中文行里的英文全名）。
- `len(zh) == len(final)`，且每个 `idx` 都有译文。
- 如环境允许自动翻译，可批量预填后再人工校对。不要把正文打进日志。
- 条目只是微调时，可按规范化英文标题复用上一期中文，再按新 `idx` 回填。

**Step 6 — 写入飞书文档并发链接**
```bash
python3 .cursor/skills/cision-mentions/scripts/publish_daily_report.py \
  --final final.json \
  --zh zh.json \
  --after "<导出摘要里的 after>" \
  --raw-count <delta_rows>
```
脚本先清空固定 wiki 文档的正文，再写入两行式日报，最后只把数据日期和 wiki 链接发到固定群。不要另存 Word 当作成品。`--after` 与 `--raw-count` 仍必传。

## 3. 收尾自检清单

生成后逐项核对：
- [ ] 英文媒体标签全部为 KB「媒体名称知识库」键（无野媒体残留）。
- [ ] 残留新闻稿（Press Release）为 0。
- [ ] 四个栏目顺序为 国内企业 → 自动驾驶 → 海外企业 → 企业领导人。
- [ ] 超链接数量 == final 条数（每篇报道一个外部链接）。
- [ ] 同一 URL、同一标题、同一媒体的近题重复已去掉。不同媒体的同事件报道默认都在。
- [ ] 无标题粘连条目。
- [ ] 中文行无残留英文领导人全名（如 `Satya Nadella` 已替换为 `萨提亚·纳德拉`）。
- [ ] 领导人板块 H2 为「中文名（英文名｜公司）」格式。
- [ ] 抽查几条：是竞品情报，而不是股评、消费评测或生活杂讯。

## 4. 知识库维护

若需新增/修正媒体、品牌、领导人译名，编辑 `翻译知识库.xlsx` 后，用 `consolidate_kb.py` 重新整理：
```bash
python scripts/consolidate_kb.py --src "/path/待整理知识库.xlsx" --out "/path/翻译知识库.xlsx"
```
脚本会做「一一对应」校验（同一中文译名不得对应多个英文），并拆出独立的领导人表。不要改这个脚本。

加媒体后用一篇已知稿件跑一遍，确认它出现在 `final.json` 里。历史上在库媒体曾被国家闸静默丢掉，见 `pitfalls.md` 第 30 条。
