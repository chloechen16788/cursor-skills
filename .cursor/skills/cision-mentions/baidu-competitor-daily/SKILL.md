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
raw monitoring export. Each entry is two lines (English title with hyperlink + Chinese title).
Media, brand, and leader names come from the《翻译知识库》. When this folder is used by the
Cision mentions skill, finish with `../scripts/publish_daily_report.py` (clear and rewrite the
fixed Feishu doc, then send the Shanghai data date and wiki link). Do not deliver a Word file
from that run.

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
final step. Do not stop at a `.docx`. Do not insert `build_doc.py` or `csv_to_delta.py`
into the Cision mentions run. The scheduled export already has a `content` column.

All scripts live in `scripts/` and take explicit `--input/--kb/--out` arguments (no hard-coded paths).
Detailed commands and the verification checklist are in `references/workflow.md`.

`final.json` entries keep `idx`, `section`, `entity`, `title`, `url`, `media_kb`, `impact`.
`section` is one of `国内企业`, `自动驾驶`, `海外企业`, `企业领导人`. `zh.json` maps each `idx` to `zh`.

## Core rules (must hold every run)

1. **Media whitelist first, then language.** A source is kept only if it resolves to a name in
   `assets/翻译知识库.xlsx` → `媒体名称知识库`. Normalization order: exact match, strip a trailing
   ` Online`, `SRC_TO_KB`, then a case-insensitive retry. `SRC_TO_KB` targets must exist in the KB.
   Only `languageCode ∈ {en, english}`.
   **The media whitelist outranks the key-market filter.** Anything already in the KB is kept
   even when the filing country is Singapore, Canada, or Australia. Resolve media before country.
2. **Press Releases excluded** — detect PR wires (PRNewswire, GlobeNewswire, Business Wire, EINPresswire,
   Newsfile, Cision, `press release`) in title/author/excerpt.
3. **Four section names stay.** The Feishu doc still prints 国内企业, 自动驾驶, 海外企业, 企业领导人.
   **No per-brand cap.** `CAP` values are `None`.
   Leaders with a known company are filed under that brand (`leader_placement`): 马云 → 阿里巴巴,
   Sundar Pichai → Alphabet/Google, Dara Khosrowshahi → Uber. Do not move them back into 企业领导人.
   Elon Musk has no single brand and stays his own entity under 自动驾驶. A leader that cannot be
   resolved keeps their own entity and is not dropped. A headline that only names a person is rescued
   onto that person's brand.
4. **Attribution is title-only.** `placed()` matches the headline against the alias tables and nothing else.
   A headline that names no brand and no leader is dropped.
   Apple Intelligence items (`focus` of `apple_intel_cn` or `apple_intel`) are placed on the
   earliest-mentioned entity, not by the domestic-first rule. Both `curation.unique_placement`
   and `prep_final` apply this branch.
5. **Product names roll up to their company.** ChatGPT/GPT → OpenAI, Claude → Anthropic,
   Kimi → 月之暗面/Moonshot, Gemini → Alphabet/Google. Do not open a separate section for a product.
6. **Keep every outlet's report.** Dedup drops the same URL, the same normalized title, and a near-duplicate
   from the same outlet (Jaccard ≥ 0.5 within one section, entity, and media). Cross-outlet coverage of one
   event stays. `prep_final.py` merges those only when called with `--event-dedup`. The scheduled command
   does not pass that flag.
7. **Title-only genre drops.** Promotions, Apple TV+ shows, pure stock moves, advertorials, lifestyle columns,
   and listicles are judged on the headline. Bare `deal`, `sale`, or `discount` are not promo signals.
   Supply-chain price moves (DRAM/NAND/HBM/wafer/GPU, no consumer device in the headline) stay.
   IPO debut-day moves stay. A pure politics headline drops unless it also carries a business signal.
   `STRONG_POLITICS_PAT` drops election-fight headlines even when a business word is present.
8. **`Moonshot` is case-sensitive.** Capital M is 月之暗面. Lowercase `moonshot` is a figure of speech and is dropped
   unless the headline also names Kimi or the company. `match_in_text()` must see the original-case title.
   `Biren` is case-sensitive for the same reason (the given name Biren Singh is not the company).
9. **Apple Intelligence is the client's top focus.** `apple_intel_cn` (+4) needs Apple Intelligence / Siri / Apple AI
   plus a China signal. Bare `chinese` is a language rollout, not 入华. `apple_intel` (+2) is other Apple
   Intelligence news, including reviews and how-tos. The score does not decide inclusion. The Feishu publisher
   re-sorts by `impact` and does not read `focus`; check the field on `final.json`.
10. **Two-line format**: `英文媒体：英文标题（超链接）` / `中文媒体：中文标题`. Chinese media name has no book brackets.
11. **Glossary one-to-one**: media, brand, and leader names MUST come from《翻译知识库》. A Chinese name in the
    KB does not by itself make a brand trackable; add the alias in `filter3.py` as well. Leader names that
    remain in 企业领导人 use H2 `中文名（英文名｜公司）`. English full leader names in the Chinese line are
    replaced by the KB Chinese name.

## Maintain the filter

Alias tables and exclusion rules live in `scripts/filter3.py`:
`DOMESTIC_BRANDS`, `DOMESTIC_LEADERS`, `AUTO_BRANDS`, `AUTO_LEADERS`,
`OVERSEAS_BRANDS`, `OVERSEAS_LEADERS`, `LEADER_PARENT`, `LEADER_PARENT_ALIAS`,
plus `EXCL`, `PR_PAT`, and the per-brand regexes in `topic_gate()`.

Domestic chip and optics names sit together: 长鑫存储/CXMT, 长江存储/YMTC, 天数智芯/Iluvatar,
壁仞科技/Biren, 中际旭创/Innolight, plus 沐曦/MetaX and 摩尔线程/Moore Threads.

- `topic_gate()` is title-only, same as attribution. It covers Yahoo stock noise, Musk, Tesla, Uber/Lyft
  delivery, Amazon, earnings previews, and crypto. Earnings-preview drops apply to pure overseas
  competitors only. Auto and domestic previews stay.
- `cruise_hit(title)` — Cruise is not in `AUTO_BRANDS`. A headline is kept only when it contains
  `cruise`, an AV context (gm / robotaxi / self-driving / autonomous / driverless / waymo), and no
  travel or cinema signal (Tom Cruise, cruise ship, box office).
- `is_broken_title()` rejects concatenated export titles (longer than 220 characters, or a repeated
  20/30/40-character prefix).
- `APPLE_FOOD_PAT` against `APPLE_TECH_PAT` keeps recipe and orchard “apple” out of the Apple bucket.
  `APPLE_MEDIA_PAT` drops Apple TV+ shows. `Big Apple` without a product name is New York, not Apple.
- `TITLE_ONLY_RULES`, `PROMO_PAT`, and `STOCK_MOVE_PAT` run on the headline. `supply_price_intel()`
  exempts chip and memory price moves. A stock-move headline that also names memory, margins, earnings,
  chips, AI, or a trading debut stays.
- `POLITICS_PAT` drops election and partisan headlines that miss `BUSINESS_SIGNAL_PAT`.
  `STRONG_POLITICS_PAT` drops even when a business signal is present.
- Amazon stays only when the title hits a substantive signal (AI, AWS, cloud, chip, agent, robot, Zoox,
  Anthropic, OpenAI, lawsuit). A bare `deal` is not enough.
- `月之暗面/Moonshot` uses a case-sensitive alias. `Nikkei Asian Review` maps to `Nikkei Asia`.
  Case-insensitive media lookup keeps `POLITICO` and `Tech in Asia`.

`scripts/curation.py` holds `PRIORITY` and `apple_focus()`. Regulation, IPO, funding, earnings, and AI
strategy score 2. Chip, China, employment, robotaxi, model updates, and exclusives score 1. An OpenAI
or Anthropic IPO or funding hit adds 3. Apple Intelligence 入华 adds 4; other Apple Intelligence adds 2.
**The score only orders items inside a brand. It never decides inclusion.**
A score of 0 is not a noise signal. `CAP` is `None` for every section.
Parentheses in a leader entity are not aliases: `Dara Khosrowshahi (Uber)` must not make every Uber
headline belong to that person.

`references/filtering_criteria.md` is the readable mirror. Keep it in sync when editing code.
Rebuild the KB with `scripts/consolidate_kb.py` after glossary edits. Do not edit that script.

## Known pitfalls

Read `references/pitfalls.md` before each run. The highest-risk ones:

- Never let `keywords` decide placement or gating.
- There is no per-brand cap. Do not trim a brand back to 5 or 8 after the scripts run.
- Do not move a leader who already sits under a brand back into 企业领导人.
- Assert `len(ZH) == len(final)`. Build `zh.json` from `final`'s `idx` order via `make_zh_template.py`.
- A brand needs both a KB row and an alias. CXMT, YMTC, Iluvatar, Biren, and Innolight were dropped when only the KB had them.
- `Meta` needs a boundary regex. `Biren` and `Moonshot` need case-sensitive aliases.
- After a rule change, re-check the specific articles that motivated it.

## Translation step

After `prep_final.py`, run `make_zh_template.py` to get `zh_template.json`, fill each `"zh"`, save as `zh.json`,
then `../scripts/publish_daily_report.py`. Title-level translation is sufficient; translate only after selection (do not read full bodies).
If an automated translation API is available in the environment, pre-fill then human-review; otherwise translate manually.
When the article set barely changes, reuse a prior Chinese title by normalized English title, then re-key by the new `idx`.
Every `idx` must have a `zh` before publish.
