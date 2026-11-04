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

The scheduled export is already an xlsx with a `content` column. `scripts/csv_to_delta.py`
is only for a hand-delivered CSV that still has the body in `transcript`. Do not insert it
into the Cision mentions run.

All scripts live in `scripts/` and take explicit `--input/--kb/--out` arguments (no hard-coded paths).
Detailed commands, environment setup, and the verification checklist are in
`references/workflow.md`.

## Core rules (must hold every run)

1. **Media whitelist first, then language.** A source is kept only if it resolves to a name in
   `assets/翻译知识库.xlsx` → `媒体名称知识库`. Normalization strips a trailing ` Online`, with
   explicit aliases in `SRC_TO_KB`. Only `languageCode ∈ {en, english}`.
   **The media whitelist outranks the key-market filter.** Anything already in the KB is kept
   even when the filing country is Singapore, Canada, or Australia. Resolve media before country.
2. **Press Releases excluded** — detect PR wires (PRNewswire, GlobeNewswire, Business Wire, EINPresswire,
   Newsfile, Cision, `press release`) in title/author/excerpt.
3. **Four sections, fixed order**: 国内企业 → 自动驾驶 → 海外企业 → 企业领导人.
   **No per-brand cap.** `CAP` values are `None`. Report size comes from the exclusion rules and dedup.
4. **Attribution is title-only.** `placed()` matches the headline against the alias tables and nothing else.
   A headline that names no brand is dropped. Leader-name hits prefer 企业领导人; domestic and auto keep
   their own brand when the title still matches it.
5. **Product names roll up to their company.** ChatGPT/GPT → OpenAI, Claude → Anthropic,
   Kimi → 月之暗面/Moonshot, Gemini → Alphabet/Google. Do not open a separate section for a product.
6. **One entry per event.** Dedup in order: URL, exact title, near-duplicate within the same
   section + entity + media (Jaccard ≥ 0.5), then event-level (Jaccard ≥ 0.5, or at least two shared
   rare tokens). `prep_final.py` keeps one representative per event (`--per-event`, default 1).
7. **Two-line format**: `英文媒体：英文标题（超链接）` / `中文媒体：中文标题`. Chinese media name has no book brackets.
8. **Glossary one-to-one**: media, brand, and leader names MUST come from《翻译知识库》. Leader H2 is
   `中文名（英文名｜公司）`; English full leader names in the Chinese line are replaced by the KB Chinese name.

## Maintain the filter

Alias tables and exclusion rules live in `scripts/filter3.py`:
`DOMESTIC_BRANDS`, `DOMESTIC_LEADERS`, `AUTO_BRANDS`, `AUTO_LEADERS`,
`OVERSEAS_BRANDS`, `OVERSEAS_LEADERS`, plus `EXCL`, `PR_PAT`, and the per-brand regexes in `topic_gate()`.

- `topic_gate()` is title-only, same as attribution. It covers Yahoo stock noise, Musk, Tesla, Uber/Lyft
  delivery, Amazon, earnings previews, and crypto. Earnings-preview drops apply to pure overseas
  competitors only. Auto and domestic previews stay.
- `cruise_hit(title)` — Cruise is not in `AUTO_BRANDS`. A headline is kept only when it contains
  `cruise`, an AV context (gm / robotaxi / self-driving / autonomous / driverless / waymo), and no
  travel or cinema signal (Tom Cruise, cruise ship, box office).
- `is_broken_title()` rejects concatenated export titles (longer than 220 characters, or a repeated
  20/30/40-character prefix).
- `APPLE_FOOD_PAT` against `APPLE_TECH_PAT` keeps recipe and orchard “apple” out of the Apple bucket.
- Amazon stays only when the title hits a substantive signal (AWS, cloud, chip, agent, robot, Zoox,
  Anthropic, OpenAI, lawsuit). A bare `deal` is not enough, so “Kindle deal” drops.

`scripts/curation.py` holds `PRIORITY`. Regulation, IPO, funding, earnings, and AI strategy score 2.
Chip, China, employment, robotaxi, model updates, and exclusives score 1. An OpenAI or Anthropic IPO
or funding hit adds 3. **The score only orders items inside a brand. It never decides inclusion.**
A score of 0 is not a noise signal. `CAP` is `None` for every section.

`references/filtering_criteria.md` is the readable mirror. Keep it in sync when editing code.
Rebuild the KB with `scripts/consolidate_kb.py` after glossary edits. Do not edit that script.

## Known pitfalls

Read `references/pitfalls.md` before each run. The highest-risk ones:

- Never let `keywords` decide placement or gating. It is a term-to-frequency map and has attached
  Qualcomm to Uber, Yum China to 美团, and a Chevy Bolt review to GM Cruise.
- There is no per-brand cap. Do not trim a brand back to 5 or 8 after the scripts run.
- Assert `len(ZH) == len(final)`. Build `zh.json` from `final`'s `idx` order via `make_zh_template.py`.
- `Meta` needs a boundary regex or Meta-Optics/metaEye slips in. `GLOBE NEWSWIRE` needs the optional space.
- After a rule change, re-check the specific articles that motivated it.

## Translation step

After `prep_final.py`, run `make_zh_template.py` to get `zh_template.json`, fill each `"zh"`, save as `zh.json`,
then `../scripts/publish_daily_report.py`. Title-level translation is sufficient; translate only after selection (do not read full bodies).
If an automated translation API is available in the environment, pre-fill then human-review; otherwise translate manually.
When the article set barely changes, reuse a prior Chinese title by normalized English title, then re-key by the new `idx`.
Every `idx` must have a `zh` before publish.
