---
name: baidu-competitor-daily
description:
  This skill should be used when building the "百度海外舆情日报 · 竞品与领导人"
  (Baidu overseas media monitoring daily report — competitors & leaders). It applies
  when the user provides a raw media-monitoring export (e.g. delta-bodies.xlsx) and
  wants it filtered, curated into four sections (国内企业 / 自动驾驶 / 海外企业 / 企业领导人),
  translated against a《翻译知识库》one-to-one glossary, and assembled into a two-line
  (English hyperlink + Chinese) report. The scheduled Cision run writes that report
  into the fixed Feishu doc instead of delivering a Word file. Trigger phrases include "百度竞品日报",
  "百度海外舆情", "竞品同业日报", "媒体监测周/日报", or any request to turn a media
  export into a Baidu competitor/leader briefing.
agent_created: true
---

# 百度竞品同业日报（竞品与领导人）

Generate the Baidu overseas media-monitoring daily report (competitors & leaders) from a
raw monitoring export. The report has four sections, each entry shown
as two lines (English title with hyperlink + Chinese title), translations strictly aligned
to the《翻译知识库》glossary. When this folder is used by the Cision mentions skill, finish
with `../scripts/publish_daily_report.py` (clear and rewrite the fixed Feishu doc, then
send the Shanghai data date and wiki link). Do not deliver a Word file from that run.

## When to use

- The user hands over a raw media export (`.xlsx`, typically `delta-bodies.xlsx` with a `delta` sheet) and asks for a 百度竞品 / 海外舆情 / 同业日报.
- The user wants to re-run, update, or maintain the filtering/curation/translation pipeline for this report.
- The user references the《翻译知识库》or asks to add/remove competitors, leaders, or media.

## Pipeline (run in order)

```
delta-bodies.xlsx + 翻译知识库.xlsx
   → filter3.py      → candidates.json
   → curation.py     → curated.json   (needs raw xlsx again for scoring)
   → prep_final.py   → final.json
   → make_zh_template.py → zh_template.json
   [human fills zh.json]
   → publish_daily_report.py → Feishu doc + group link
```

`publish_daily_report.py` lives in the parent `scripts/` directory. It is the scheduled
final step. Do not stop at a `.docx`.

All scripts live in `scripts/` and take explicit `--input/--kb/--out` arguments (no hard-coded paths).
Detailed commands, environment setup, and the verification checklist are in
`references/workflow.md`.

## Core rules (must hold every run)

1. **Only English** (`languageCode == 'en'`) and **only KB-listed media** are kept.
   Media names are normalized (`* Online` stripped, `Bloomberg News Online → Bloomberg`, etc.).
2. **Press Releases excluded** — detect PR wires (PRNewswire, GlobeNewswire, Business Wire, EINPresswire…,
   `press release`) in title/author/excerpt.
3. **Four sections, fixed order**: 国内企业 → 自动驾驶 → 海外企业 → 企业领导人.
   Overseas brands split per-brand (cap 5); leaders per-person (cap 8); domestic/auto are "collect-all" (cap 50).
4. **One report per article**: assign each article to the single section/brand whose name appears earliest in the title
   (leader-name hits prefer the 领导人 section; domestic/auto keep their own brand when still matched). Dedupe globally by URL.
5. **Two-line format**: `英文媒体：英文标题（超链接）` / `中文媒体：中文标题`. Chinese media name has no book brackets.
6. **Glossary one-to-one**: media, brand, and leader names MUST come from《翻译知识库》. Leader H2 is
   `中文名（英文名｜公司）`; English full leader names in the Chinese line are auto-replaced by KB standard Chinese.

## Maintain the filter

Competitor/leader alias tables and exclusion rules live in `scripts/filter3.py`
(`DOMESTIC_BRANDS`, `DOMESTIC_LEADERS`, `AUTO_BRANDS`, `AUTO_LEADERS`, `OVERSEAS_BRANDS`, `OVERSEAS_LEADERS`, `EXCL`, `PR_PAT`).
Brand and leader topic gating (Yahoo stock noise, Musk/Tesla, Uber/Lyft, Amazon, earnings previews, crypto) lives in `topic_gate()` in the same file.
Priority weights live in `scripts/curation.py` (`PRIORITY`): earnings, IPO, funding, and regulation score 2; model updates score 1; an OpenAI or Anthropic IPO or funding hit adds 3 more.
The readable mirror is in `references/filtering_criteria.md` (section 八 has the nine refined rules, including the added Tesla brand) — keep the two in sync when editing.
A consolidated KB is bundled at `assets/翻译知识库.xlsx`; re-consolidate with `scripts/consolidate_kb.py` after edits.

## Known pitfalls

Read `references/pitfalls.md` before each run. The highest-risk ones:
- Run **unique title-based placement BEFORE the per-brand cap**, or the cap silently fails (Anthropic ballooned to 12).
- Assert `len(ZH) == len(final)`; only build `zh.json` from the final `idx` order (use `make_zh_template.py`).
- `Meta` needs a boundary regex or Meta-Optics/metaEye false-match; `GLOBE NEWSWIRE` needs the `?` space tolerance.

## Translation step

After `prep_final.py`, run `make_zh_template.py` to get `zh_template.json`, fill each `"zh"`, save as `zh.json`,
then `../scripts/publish_daily_report.py`. Title-level translation is sufficient; translate only after selection (do not read full bodies).
If an automated translation API is available in the environment, pre-fill then human-review; otherwise translate manually.
