# 运行工作流（百度竞品同业日报）

本文件只描述筛选到填中文标题。脚本在 `scripts/`，需要 `openpyxl`。做到 `final.json` 和 `zh.json` 即停止，交给 cision-mentions 的 `publish_daily_report.py`。

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
final.json ──> make_zh_template.py ──> zh_template.json ──> 按标题填 zh.json
```

- 原始数据：`delta-bodies.xlsx`（工作表名 `delta`，字段含 title/source/url/locationCountry/languageCode/keywords/impactScore/excerpt/author/content/publishedAt）。
- 翻译知识库：`翻译知识库.xlsx`，含「媒体名称知识库 / 品牌名称翻译知识库 / 领导人名称翻译知识库」三表（一一对应）。

## 2. 逐步执行

> 说明：以下命令中的路径请替换为实际文件路径。脚本已参数化，不再写死绝对路径。

**Step 1 — 候选过滤**
```bash
python scripts/filter3.py \
  --input "/path/delta-bodies.xlsx" \
  --kb   "/path/翻译知识库.xlsx" \
  --out  candidates.json
```
输出 `CANDIDATE COUNT` 及各板块命中统计。检查 `海外企业` 是否异常膨胀（如 Microsoft 59 条），确认剔除规则生效。

**Step 2 — 优先级评分 + 唯一归属 + 限额**
```bash
python scripts/curation.py \
  --candidates candidates.json \
  --raw "/path/delta-bodies.xlsx" \
  --out curated.json
```
终端会打印 `TRANSLATION LIST`（待翻译清单）。确认各板块数量符合上限（海外企业 ≤5/品牌、领导人 ≤8/人）。

**Step 3 — 标题定归属 + URL 去重 + 排序编号**
```bash
python scripts/prep_final.py --input curated.json --out final.json
```
打印 `TRANSLATION LIST (idx | media_kb | section | entity | title)`，**此清单的 idx 顺序即最终报告顺序**。

**Step 4 — 生成翻译模板**
```bash
python scripts/make_zh_template.py --final final.json --out zh_template.json
```
得到 `zh_template.json`：每项含 `idx / media_kb / section / entity / en / zh(空)`。

**Step 5 — 按标题填中文**
将 `zh_template.json` 中每项的 `"zh"` 填为中文标题，另存为 `zh.json`。
- 只译标题，不读正文。
- 领导人中文名、媒体中文名必须与《翻译知识库》一一对应。
- `len(zh) == len(final)`，顺序跟 `idx`。
- 如环境允许自动翻译，可批量预填后再人工校对。不要把正文打进日志。

## 3. 收尾自检

对照 `final.json` 和 `zh.json`：
- [ ] 英文媒体标签全部为知识库「媒体名称知识库」的键。
- [ ] 残留新闻稿（Press Release）为 0。
- [ ] 同一报道只出现一次（URL 去重生效）。
- [ ] `len(zh) == len(final)`，且按下标与 `idx` 对齐。
- [ ] 中文标题里的领导人名用知识库中文，不留英文全名。
- [ ] 中文只来自标题，没有摘抄正文。

## 4. 交给发布

产出 `final.json` 和 `zh.json` 后停止，交给 cision-mentions 技能的 `publish_daily_report.py`。发布参数不在本文件里。

## 5. 知识库维护

若需新增或修正媒体、品牌、领导人译名，编辑 `翻译知识库.xlsx` 后，用 `consolidate_kb.py` 重新整理：
```bash
python scripts/consolidate_kb.py --src "/path/待整理知识库.xlsx" --out "/path/翻译知识库.xlsx"
```
脚本会做「一一对应」校验（同一中文译名不得对应多个英文），并拆出独立的领导人表。
