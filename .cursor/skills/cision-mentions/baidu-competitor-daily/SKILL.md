---
name: baidu-competitor-daily
description:
  This skill should be used when building the "百度海外舆情日报 · 竞品与领导人"
  (Baidu overseas media monitoring daily report — competitors & leaders). It applies
  when the user provides a raw media-monitoring export (e.g. delta-bodies.xlsx) and
  wants it filtered, curated into four section fields (国内企业 / 自动驾驶 / 海外企业 /
  企业领导人, leaders nested under their brand), translated against a《翻译知识库》
  one-to-one glossary, and assembled into a two-line report. The scheduled Cision run
  writes the fixed Feishu doc and also builds a Word file with build_doc.py, then sends
  the Shanghai date, the wiki link, and that Word file to the same group. Trigger phrases
  include "百度竞品日报", "百度海外舆情", "竞品同业日报", "媒体监测周/日报", or any request to
  turn a media export into a Baidu competitor/leader briefing.
agent_created: true
---

# 百度竞品同业日报（竞品与领导人）

Generate the Baidu overseas media-monitoring daily report from a raw monitoring export.
Each entry is two lines (English title with hyperlink, then the Chinese title). Media, brand,
and leader names come from the《翻译知识库》.

When this folder is used by the Cision mentions skill, the last command is
`../scripts/publish_daily_report.py`. It clears and rewrites the fixed Feishu doc, generates
the Word file with `scripts/build_doc.py`, then sends the Shanghai data date, the wiki link,
and the Word file to the fixed group. Do not send the file anywhere else. The scheduled export
already has a `content` column, so do not insert `csv_to_delta.py` into that run.

## When to use

- The user hands over a raw media export (`.xlsx`, typically `delta-bodies.xlsx` with a `delta` sheet) and asks for a 百度竞品 / 海外舆情 / 同业日报.
- The user wants to re-run, update, or maintain the filtering, curation, or translation pipeline.
- The user references the《翻译知识库》, or asks to add or remove competitors, leaders, or media.

## Pipeline (run in order)

```
delta-bodies.xlsx + 翻译知识库.xlsx
   → filter3.py           → candidates.json
   → curation.py          → curated.json   (needs the raw xlsx again for scoring)
   → prep_final.py        → final.json
   → make_zh_template.py  → zh_template.json
   [fill zh.json]
   → publish_daily_report.py → Feishu doc + Word file in the same group
```

`publish_daily_report.py` calls `build_doc.py`. Do not skip the Word file, and do not stop after only writing the Feishu doc.
All scripts take explicit `--input` / `--kb` / `--out` arguments. Commands and the checklist are in `references/workflow.md`.

`final.json` entries keep `idx`, `section`, `entity`, `title`, `url`, `media_kb`, `impact`, and `focus` when set.
`section` is one of `国内企业`, `自动驾驶`, `海外企业`, `企业领导人`. `zh.json` maps each `idx` to `zh`.
`build_doc.py` reads those four field names and prints the three display headings below.

## Core rules (must hold every run)

1. **Media whitelist first, then language.** A source is kept only if it resolves to a name in
   `assets/翻译知识库.xlsx` → `媒体名称知识库`. Normalization order: exact match, strip a trailing
   ` Online`, `SRC_TO_KB`, then a case-insensitive retry. The KB has no case-only duplicates, so the
   retry is safe. Exports write `POLITICO`, `Tech in Asia`, and `marketwatch` in arbitrary casing;
   exact matching alone silently discards them. Only `languageCode ∈ {en, english}`.
   **The media whitelist outranks the key-market filter.** Anything already in the KB is kept
   even when the filing country is Singapore, Canada, or Australia. Resolve media before country.
   **`SRC_TO_KB` targets must exist in the KB.** The lookup warns at startup. Without that check a typo
   admits a non-KB outlet.
2. **Key markets** apply only to sources that are not already in the whitelist: China, United States,
   United Kingdom, UAE. `Taiwan` maps to China. `England` maps to United Kingdom.
3. **Press Releases excluded.** Detect PR wires (PRNewswire, GlobeNewswire, Business Wire, EINPresswire,
   Newsfile, Cision, `press release`) in title, author, or excerpt.
4. **Four `section` field names stay** (`国内企业`, `自动驾驶`, `海外企业`, `企业领导人`), in that order.
   The Feishu doc and the Word file print three headings when the section has items:
   「一、国内竞品（含领导人）」「二、自动驾驶竞品（含领导人）」「三、海外竞品（含领导人）」.
   An empty section is omitted. Leaders with a known company are filed under that brand
   (`filter3.leader_placement`): 马云 → 阿里巴巴, Sundar Pichai → Alphabet/Google,
   Dara Khosrowshahi → Uber. Brands without parentheses use `LEADER_PARENT`. Parent names that are
   not canonical brand keys go through `LEADER_PARENT_ALIAS` (`DeepMind` / `Google` → Alphabet/Google,
   `AWS` → Amazon). Current overseas leaders: Bill Gates → Microsoft, Eric Schmidt → Alphabet/Google,
   Pichai / Hassabis → Alphabet/Google, Nadella → Microsoft, Jassy / Garman / Bezos → Amazon.
   `埃隆·马斯克/Elon Musk` has no single brand and stays his own entity under 自动驾驶.
   An unresolvable leader keeps their own entity and is not dropped. A headline that only names a person
   is rescued onto that person's brand. Do not move a leader who already sits under a brand back into 企业领导人.
   **No per-brand cap.** `CAP` values are `None`. Report size comes from the exclusion rules, not a quota.
   Do not trim a brand to 5 or 8 after the scripts run.
5. **Attribution is title-only.** `placed()` matches the headline against the alias tables and nothing else.
   Never use `excerpt`, `keywords`, or `content`, and there is no fallback. A headline that names no brand
   and no leader is dropped. Leader-name hits resolve to the leader's brand. Domestic and auto keep their
   own brand when the title still matches it.
   Apple Intelligence items (`focus` of `apple_intel_cn` or `apple_intel`) are placed on the
   earliest-mentioned entity, not by the domestic-first rule. Both `curation.unique_placement`
   and `prep_final` apply this branch, or the second pass undoes the first.
6. **Product names roll up to their company.** ChatGPT/GPT → OpenAI, Claude → Anthropic,
   Kimi → 月之暗面/Moonshot, Gemini → Alphabet/Google. Do not open a separate section for a product.
7. **Keep every outlet's report.** Dedup drops the same URL, the same normalized title, and a near-duplicate
   from the same outlet (Jaccard ≥ 0.5 within one section, entity, and media). Cross-outlet coverage of one
   event stays. `prep_final.py` merges those only when called with `--event-dedup` (`--per-event N` sets how
   many survive). The scheduled command does not pass that flag. Do not turn it on silently.
8. **Same event, adjacent rows — discovered from the data, never from a keyword list.**
   `build_doc.discover_events()` maps each word to the set of headlines containing it, drops words that appear in
   only one headline or in ≥80% of that entity's headlines, then merges words whose headline sets overlap
   ≥ `EVENT_OVERLAP` (0.5, min-normalized). **A cluster may not exceed `EVENT_CAP` (0.55) × the entity total.**
   Without that guard, single-linkage chains collapse (observed: 46 Apple items merged into one 45-item cluster).
   Leftover headlines stay standalone. The Feishu publisher uses the same function.
   `group_by_topic` clusters the **full** item set first, then does a stable partition by `focus`
   (`apple_intel_cn`, then `apple_intel`, then the rest). Do not cluster the focus subset by itself:
   the thresholds move and other brands reorder (observed: 17 displacements). Do not put `pscore` on the
   cluster sort key. `pscore` only orders items inside one exact-title group in `prep_final.py`.
   **Never reintroduce hand-written topic tags** (`school_ai`, `mna`, `buyout`). They fit one day's data and rot.
   The only tunables are the two thresholds above.
9. **Promo, Apple TV+, and pure stock moves are out**, judged on the headline only (`TITLE_ONLY_RULES`).
   Excerpts contain `premarket trading`, `discount platform`, and `movie`, and cause false drops.
   Bare `deal`, `sale`, or `discount` are not promo signals.
   **Supply-chain pricing is intel, not promo.** DRAM/NAND/HBM/wafer/GPU/optical-module price moves stay.
   `supply_price_intel(head)` needs a price-move verb, a supply subject, and no consumer device
   (iPhone, Pixel, Galaxy, AirPods), so "Pixel 11 price cut" is still dropped.
   IPO debut-day moves (`trading debut`, `market debut`) stay. "CXMT shares jump 20% in trading debut" stays.
   "CXMT shares jump 20% on Tuesday" does not.
10. **Pure politics is out.** Election horse-race, polling, and partisan commentary drop unless the headline
    also carries a business signal (`BUSINESS_SIGNAL_PAT`: AI, chips, contracts, regulation, IPO, products, tickers).
    `MUSK_DROP` only covers Starlink, SpaceX, X, and Grok, so a midterm wave otherwise floods the auto section.
11. **Advertorials and lifestyle are out**: law-firm accident ads, partner-award listings, dating-advice columns,
    `N ChatGPT prompts to get out of debt`, `17 better ways...`, `the "Uber of X"` clichés, film interviews.
12. **`Moonshot` is case-sensitive.** Capital M is 月之暗面. Lowercase `moonshot` is a figure of speech and is dropped
    unless the headline also names Kimi or the company. `match_in_text()` must see the original-case title.
    `Biren` is case-sensitive for the same reason (the given name Biren Singh is not the company).
13. **Apple Intelligence is the client's top focus.** Two levels, both decided on the headline only
    (`curation.apple_focus`), carried as `focus`:
    - `apple_intel_cn` (+4): Apple Intelligence / Siri / Apple AI plus a China signal (`China`, `mainland`,
      `国行`, `CAC` / `网信办`, or Alibaba / Qwen / Baidu / Tencent).
    - `apple_intel` (+2): other Apple Intelligence news, including reviews and how-tos.
    Bare `chinese` is a language rollout, not 入华. The pattern requires `chinese market/users/regulators/…`.
    The score does not decide inclusion. Ordering lifts `apple_intel_cn`, then `apple_intel`, to the front of
    that brand without reordering brands that have no focus item. Attribution uses the earliest-mentioned entity,
    so "Apple Intelligence launches in China with Alibaba's Qwen model" stays under Apple.
14. **Noise categories that reappear in every batch**, all judged on the headline. Skim the output for these
    before delivering:
    零售/散户股价叙事（`If You Invested $1,000…`、`Stock Is Now Cheaper Than…`、`Options Traders…`）·
    同词异义（`intel report` is intelligence, not Intel；`Big Apple` is New York）·
    本地商家好评/SEO 软文（`Google Reviews Recognize…`）· 罪案/司法花边 ·
    致富教程/副业（`Turn Your Job Skills Into A $100,000 Business`）· 娱乐职业转型 ·
    软件 bug/更新日志（`Excel 2016 copy-paste bug`）· 富豪榜/地产 · 通稿换皮（`Xinhua Silk Road`）·
    怀旧开箱 · 个人使用技巧 · 社媒使用场景/公益（`missionaries take to TikTok`）· 第一人称走访见闻。
    The individual-use-tips rule excludes Apple Intelligence, Siri, and AI. The client wants those reviews
    and how-tos kept. The rule carries a negative lookahead.
15. **Strong politics overrides business signals.** `STRONG_POLITICS_PAT` (election rout, `persecute`,
    `governor-elect`, `spent at least $X million in`, `lawyer up`, `DOGE`, `loses billions`) drops the item
    even when `BUSINESS_SIGNAL_PAT` matches. Otherwise "Musk fires back at Democrats over AI regulation after
    midterm rout" survives on the word `AI`. The pattern deliberately excludes bare `after the midterm`, so
    "Why Shares of Tesla, SpaceX Are Sliding After the Midterm Elections" stays.
16. **Two-line format, two outputs.**
    Feishu: the English line is one bold link, `媒体: 标题`, ASCII colon and space. The Chinese line is one bold
    run, `中文媒体：中文标题`, fullwidth colon, no link. Chinese media names have no book brackets.
    Word (`build_doc.py`): the English line is three bold hyperlinks (media, `: `, title) pointing at the same URL.
    The Chinese line is bold, fullwidth colon, no link. The document title is bold.
    Do not reorder either file by hand.
17. **Glossary one-to-one.** Media, brand, and leader names MUST come from《翻译知识库》. A Chinese name in the
    KB does not by itself make a brand trackable; add the alias in `filter3.py` as well. Leader entities that
    remain in 企业领导人 use `中文名（英文名｜公司）`. English full leader names in the Chinese line are
    replaced by the KB Chinese name.

## Maintain the filter

Alias tables and exclusion rules live in `scripts/filter3.py`:
`DOMESTIC_BRANDS` (41), `DOMESTIC_LEADERS` (14), `AUTO_BRANDS` (12), `AUTO_LEADERS` (10),
`OVERSEAS_BRANDS` (13), `OVERSEAS_LEADERS` (15), `LEADER_PARENT`, `LEADER_PARENT_ALIAS`,
plus `EXCL`, `PR_PAT`, and the per-brand regexes in `topic_gate()`.

**A Chinese name in the KB does not make a brand trackable.** `placed()` searches the alias tables.
A company that exists only in `品牌名称翻译知识库` is silently discarded. Add it to both, then verify a real headline lands.
Domestic chip, memory, and optics names sit together: 沐曦/MetaX, 摩尔线程/Moore Threads, 长鑫存储/CXMT,
长江存储/YMTC, 天数智芯/Iluvatar, 壁仞科技/Biren, 中际旭创/Innolight. `Biren` collides with the given name
Biren Singh, so its alias is case-sensitive and excludes that name.

- `topic_gate()` is title-only. It covers Yahoo stock noise, Musk, Tesla, Uber/Lyft delivery, Amazon,
  earnings previews, and crypto. Earnings-preview drops apply to pure overseas competitors only.
  Auto and domestic previews stay.
- `cruise_hit(title)` — Cruise is not in `AUTO_BRANDS`. A headline is kept only when it contains
  `cruise`, an AV context (gm / robotaxi / self-driving / autonomous / driverless / waymo), and no
  travel or cinema signal (Tom Cruise, cruise ship, box office).
- `is_broken_title()` rejects concatenated export titles (longer than 220 characters, or a repeated
  20/30/40-character prefix).
- `APPLE_FOOD_PAT` against `APPLE_TECH_PAT` keeps recipe and orchard "apple" out of the Apple bucket.
  `APPLE_MEDIA_PAT` drops Apple TV+ shows. `Big Apple` without a product name is New York, not Apple.
- `TITLE_ONLY_RULES`, `PROMO_PAT`, and `STOCK_MOVE_PAT` run on the headline. `supply_price_intel()`
  exempts chip and memory price moves. A stock-move headline that also names memory, margins, earnings,
  chips, AI, or a trading debut stays.
- Amazon stays only when the title hits a substantive signal (AI, AWS, cloud, chip, agent, robot, Zoox,
  Anthropic, OpenAI, lawsuit). A bare `deal` is not enough.
- `Nikkei Asian Review` maps to `Nikkei Asia`.

`scripts/curation.py` holds `PRIORITY` and `apple_focus()`. Regulation, IPO, funding, earnings, and AI
strategy score 2. Chip, China, employment, robotaxi, model updates, and exclusives score 1. An OpenAI
or Anthropic IPO or funding hit adds 3. Apple Intelligence 入华 adds 4; other Apple Intelligence adds 2.
A leader viewpoint adds 1. **The score only orders items inside a brand. It never decides inclusion.**
A score of 0 is not a noise signal. Parentheses in a leader entity are not aliases:
`Dara Khosrowshahi (Uber)` must not make every Uber headline belong to that person.

`prep_final.py` groups identical normalized titles, then orders those groups by focus, `pscore`, and `impact`.
It does not run `discover_events`. Display order is `build_doc.group_by_topic`.

`references/filtering_criteria.md` is the readable mirror. Keep it in sync when editing code.
Rebuild the KB with `scripts/consolidate_kb.py` after glossary edits. Do not edit that script.

## Known pitfalls

Read `references/pitfalls.md` before each run. Highest-risk, all previously observed:

- Never let `keywords` decide placement or gating. It is a term-to-frequency map
  (`{"Cruise":12,"GM":5,"robotaxi":1}`) and produced Qualcomm→Uber, Yum China→美团, Leidos→Intel, Chevy Bolt→GM Cruise.
- There is no per-brand cap. When a cap existed, five copies of one Bloomberg wrap ate all five Apple slots.
  Dedupe before any cap, and do not put a cap back.
- Adding a media name is not enough. Check it is not silently killed by the country gate (pitfall 30).
- Assert `len(zh) == len(final)`. Build `zh.json` from `final`'s `idx` order via `make_zh_template.py`.
- `Meta` needs a boundary regex, or Meta-Optics slips in. `GLOBE NEWSWIRE` needs the optional-space tolerance.
- Do not cluster a focus subset, and do not sort event clusters by `pscore` (pitfall 56).
- After a rule change, re-check the specific articles that motivated it.

## Translation step

`make_zh_template.py` writes `zh_template.json` (`idx`, `media_kb`, `section`, `entity`, `en`, `zh`).
Fill every `zh`, save as `zh.json`, then run `publish_daily_report.py`. Title-level translation only.
Do not read bodies, and do not pre-translate before selection. `zh.json` is keyed by `idx`.

When the article set changes only slightly, reuse a prior Chinese title by normalized English title, then
re-key by the new `idx`. Every `idx` must have a `zh` before publish.
