---
name: baidu-competitor-daily
description: 把百度海外舆情的原始监测导出（如 delta-bodies.xlsx）筛选、策展成四个栏目（国内企业 / 自动驾驶 / 海外企业 / 企业领导人），对照《翻译知识库》按标题翻译，产出 final.json 和 zh.json。处理顺序是 filter3 → curation → prep_final → make_zh_template → 按标题填 zh.json。成品交给 cision-mentions 的 publish_daily_report.py。本技能不写飞书文档，也不改监测流或定时。用户提到百度竞品日报、百度海外舆情、竞品同业日报、媒体监测周报或日报、翻译知识库，或要求改筛选与翻译规则时使用。
---

# 百度竞品同业日报（处理）

从原始监测导出做出四栏目条目和中文标题。本技能只做到 `final.json` 和 `zh.json`。
写文档和发链接交给 cision-mentions 的 `publish_daily_report.py`。

## 何时使用

- 用户给出原始媒体导出（`.xlsx`，通常是带 `delta` 工作表的 `delta-bodies.xlsx`），要做成百度竞品 / 海外舆情 / 同业日报。
- 用户要改筛选、策展、翻译或《翻译知识库》。

## 处理顺序

```
delta-bodies.xlsx + 翻译知识库.xlsx
   → filter3.py          → candidates.json
   → curation.py         → curated.json
   → prep_final.py       → final.json
   → make_zh_template.py → zh_template.json
   → 按标题填写 zh.json
```

脚本在 `scripts/`，参数用 `--input` / `--kb` / `--out`，不写死路径。命令和自检在 `references/workflow.md`。

## 必须守住的处理规则

1. 只留英文（`languageCode == 'en'`），媒体必须在《翻译知识库》。来源名要归一（去掉 `* Online`，`Bloomberg News Online → Bloomberg` 等）。
2. 剔除新闻稿。标题、作者、摘要里的 PR 电头（PRNewswire、GlobeNewswire、Business Wire、EINPresswire、`press release`）都要去掉。
3. 四个栏目顺序固定：国内企业 → 自动驾驶 → 海外企业 → 企业领导人。海外企业每品牌最多 5 条，企业领导人每人最多 8 条，国内企业和自动驾驶每个实体最多 50 条。
4. 一篇报道只归一处：按标题里最早出现的名称定栏目和品牌。领导人名优先归领导人栏目；国内和自动驾驶标题仍命中本栏目品牌时不迁走。全局按 URL 去重。
5. 中文只按标题填写，不读正文。媒体、品牌、领导人译名与知识库一一对应。中文媒体名不带书名号。`len(zh) == len(final)`，顺序跟 `final.json` 的 `idx`。

## 维护筛选

别名和剔除规则在 `scripts/filter3.py`（`DOMESTIC_BRANDS`、`DOMESTIC_LEADERS`、`AUTO_BRANDS`、`AUTO_LEADERS`、`OVERSEAS_BRANDS`、`OVERSEAS_LEADERS`、`EXCL`、`PR_PAT`）。可读对照是 `references/filtering_criteria.md`，改一边就要改另一边。知识库在 `assets/翻译知识库.xlsx`，改完用 `scripts/consolidate_kb.py` 重新整理。

## 踩坑

每次处理前读 `references/pitfalls.md`。最容易错的两处：

- 先按标题做唯一归属，再套每品牌限额，否则限额会失效。
- `zh.json` 只能按最终 `idx` 从 `make_zh_template.py` 的模板填，并断言 `len(zh) == len(final)`。

## 收尾

产出 `final.json` 和按标题填好的 `zh.json`，交给 cision-mentions 技能的 `publish_daily_report.py`。本技能到这里停止。
