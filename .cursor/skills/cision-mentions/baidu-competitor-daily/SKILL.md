---
name: baidu-competitor-daily
description:
  This skill should be used when building the "百度海外舆情日报 · 竞品与领导人"
  (Baidu overseas media monitoring daily report — competitors & leaders). It applies
  when the user provides a raw media-monitoring export (CSV or xlsx, e.g. delta.csv /
  delta-bodies.xlsx) and wants it filtered, curated into three sections (国内竞品 /
  自动驾驶竞品 / 海外竞品, leaders nested under their brand), translated against a《翻译知识库》one-to-one glossary,
  and assembled into a two-line (English hyperlink + Chinese) Word report. Trigger phrases
  include "百度竞品日报", "百度海外舆情", "竞品同业日报", "媒体监测周/日报", or any request to
  turn a media export into a Baidu competitor/leader briefing.
agent_created: true
---

# 百度竞品同业日报（竞品与领导人）

Turn a raw media-monitoring export into a two-line briefing with three sections
(国内竞品 / 自动驾驶竞品 / 海外竞品). Each entry is two lines — English headline with hyperlink,
then the Chinese headline — with media / brand / leader names forced to the《翻译知识库》glossary.

When this folder is used by the Cision mentions skill, the last command is
`../scripts/publish_daily_report.py`. It clears and rewrites only
`https://jcn5bws14c2g.feishu.cn/wiki/DoXTwxbK1iX60yk282AcEN5Mn0e` with
`FEISHU_COPY_APP_ID` and `FEISHU_COPY_APP_SECRET`, and does not write
`https://prnewswire.feishu.cn/wiki/PP88weeBdi1Pcgkmpxbc48lSn5e`. It generates
the Word file with `scripts/build_doc.py`, then sends the Shanghai data date, the copy wiki link,
and the Word file to the fixed group. Do not send the file anywhere else. The copy app is not
used for the group, the bitable, or the Word file. The scheduled export
already has a `content` column, so do not insert `csv_to_delta.py` into that run.
Run `scripts/check_zh.py` after `zh.json` is filled and before publish; `error` must be 0.

## When to use

- The user hands over a raw media export (`.csv` or `.xlsx` with a `delta` sheet) and asks for a 百度竞品 / 海外舆情 / 同业日报.
- The user wants to re-run, update, or maintain the filtering / curation / translation pipeline.
- The user references the《翻译知识库》, or asks to add/remove competitors, leaders, or media.

## Pipeline (run in order)

```
delta.csv  ──csv_to_delta.py──> delta.xlsx (sheet "delta")
delta.xlsx + assets/翻译知识库.xlsx
   → filter3.py           → candidates.json
   → curation.py          → curated.json    (needs delta.xlsx again, for scoring)
   → prep_final.py        → final.json
   → make_zh_template.py  → zh_template.json
   [translate]            → zh.json
   → check_zh.py          → error 必须为 0
   → publish_daily_report.py → 副本飞书文档 + Word + 群消息
```

定时运行不要停在 `build_doc.py`。`publish_daily_report.py` 会调用它生成 Word。单独出 Word 时仍可直接跑 `build_doc.py`。

All scripts live in `scripts/` and take explicit `--input/--kb/--out` arguments; nothing is hard-coded.
Exact commands, environment setup, and the pre-delivery checklist are in `references/workflow.md`.

## Core rules (must hold every run)

1. **Media whitelist first, then language.** A source is kept only if it resolves to a name in
   `assets/翻译知识库.xlsx` → `媒体名称知识库` (61 outlets). Normalization, in order: exact match → strip a trailing
   ` Online` → exact `SRC_TO_KB` alias (`Bloomberg News Online→Bloomberg`, `BNN Bloomberg Online→BNN Bloomberg`,
   `KNTV-TV Online→NBC Bay Area`, `KPYX/KOVR-TV Online→CBS`, `MarketWatch*→MarketWatch`) →
   **case-insensitive retry** (KB has no case-only duplicates, so this is safe). The case-insensitive retry matters:
   exports write `POLITICO`, `Tech in Asia`, `marketwatch` in arbitrary casing and exact matching silently discards them
   as unknown sources. Only `languageCode ∈ {en, english}`.
   **The media whitelist outranks the key-market filter** — anything in the KB is explicitly chosen and is
   never dropped for being filed from Singapore / Canada / Australia. Resolve media *before* checking country.
   **`SRC_TO_KB` targets must exist in the KB** — the lookup validates this and prints a startup warning for bad
   mappings; without that check a typo silently admits a non-KB outlet (nearly shipped `ABC News`).
2. **Key markets** (applied only to non-whitelisted sources): China, United States, United Kingdom, UAE;
   `Taiwan→China`, `England→United Kingdom`.
3. **Press Releases excluded** — PR wires (PRNewswire, GlobeNewswire, Business Wire, EINPresswire, Newsfile,
   Cision…) and the literal `press release`, scanned in title / author / excerpt.
4. **Three sections, fixed order**: 国内竞品 → 自动驾驶竞品 → 海外竞品.
   **No separate 企业领导人 section** — leader coverage is folded into the leader's own brand
   (`filter3.leader_placement`): 马云 → 阿里巴巴, Sundar Pichai → Alphabet/Google, Dara Khosrowshahi → Uber, …
   Brands without parentheses in the entity name are resolved via `LEADER_PARENT`; parent names that aren't canonical
   brand keys go through `LEADER_PARENT_ALIAS` (`DeepMind`/`Google` → Alphabet/Google, `AWS` → Amazon).
   `埃隆·马斯克/Elon Musk` has **no single brand** (Tesla / SpaceX / X / xAI) and stays a standalone entity inside
   自动驾驶竞品. An unresolvable leader also keeps its own entity — never dropped.
   Current overseas leaders resolve as: Bill Gates → Microsoft, Eric Schmidt → Alphabet/Google,
   Pichai/Hassabis → Alphabet/Google, Nadella/Gates → Microsoft, Jassy/Garman/Bezos → Amazon, …
   Leaders still **rescue attribution**: a headline naming only a person ("Sundar Pichai says…") is placed under
   that person's brand. **No per-brand cap** (`CAP` values are `None`). Report size is governed by the exclusion
   rules, not a quota.
5. **Attribution is TITLE-ONLY.** `placed()` matches the headline against the alias tables and nothing else —
   never `excerpt`, `keywords`, or `content`, and no fallback. A headline that names no brand is dropped.
   Leader-name hits resolve to the leader's brand (see rule 4); domestic/auto keep their own brand when still matched.
6. **Product names roll up to their company** — never a separate section: ChatGPT/GPT → OpenAI,
   Claude → Anthropic, Kimi → 月之暗面/Moonshot, Gemini → Alphabet/Google. Add new product names as aliases.
7. **Keep every outlet's report; drop only true duplicates.** Three dedup passes run in `curation.py`:
   URL → exact title → near-duplicate within same section+entity+**same media** (Jaccard ≥ 0.5).
   **Event-level dedup is OFF by default** — when several outlets cover one event, all of them stay.
   Switch it on with `--event-dedup` only when a compact report is wanted (then `--per-event N` controls how
   many representatives survive). Do not re-enable it silently: it discards other outlets' angles.
8. **Same event, adjacent rows — discovered from the data, never from a keyword list.**
   `build_doc.discover_events()` maps each word to the set of headlines containing it, drops words that appear in
   only one headline (no co-occurrence evidence) or in ≥80% of them (brand names — no discriminating power), then
   merges words whose headline sets overlap ≥ `EVENT_OVERLAP` (0.5, min-normalized for headline-length asymmetry).
   **A cluster may not exceed `EVENT_CAP` (0.55) × total for that entity** — without this guard, single-linkage
   chains and collapses (observed: 46 Apple items merged into one 45-item cluster). Leftover headlines stay
   standalone. Clusters ordered by their top `impact`.
   **Never reintroduce hand-written topic tags** (`school_ai`, `mna`, `buyout`…): they are fitted to one day's
   data and silently rot when the news cycle changes. The only tunables are the two thresholds above.
9. **Promo / Apple TV+ / pure stock moves are out** — and these three are judged on the **headline only**
   (`TITLE_ONLY_RULES`), because excerpts carry `premarket trading`, `discount platform`, `movie` etc. and cause
   false drops. Beware: bare `deal` / `sale` / `discount` must not be used (business deals, sales figures, discount retail).
   **Supply-chain pricing is intel, not promo.** A headline reporting DRAM/NAND/HBM/wafer/GPU/optical-module price
   moves belongs in the report — "memory price drop squeezes CXMT margins" is core competitor intelligence.
   `supply_price_intel(head)` exempts such headlines from `PROMO_PAT` and from the `消费硬件价格/规格` rule;
   it requires a price-move verb plus a supply subject (chip/memory/GPU/wafer…) **and the absence of a consumer
   device** (iPhone/Pixel/Galaxy/AirPods/…), so "Pixel 11 price cut" is still dropped.
   IPO debut-day moves (`trading debut` / `market debut`) count as substantive, so
   "CXMT shares jump 20% in trading debut" survives the pure-stock-move rule.
10. **Pure politics is out.** Election horse-race / polling / partisan commentary is dropped **unless** the headline
   also carries a business signal (`BUSINESS_SIGNAL_PAT`: AI, chips, contracts, regulation, IPO, products, tickers).
   Rationale: `MUSK_DROP` only covers Starlink/SpaceX/X/Grok, so a midterm wave floods the report with vote-count stories.
11. **Advertorials and lifestyle are out**: law-firm accident ads, partner-award/marketplace-listing PR, dating-advice
   columns, `N ChatGPT prompts to get out of debt`, `17 better ways...`, `the "Uber of X"` clichés, film interviews.
12. **`Moonshot` is case-sensitive** — capital-M means the company (月之暗面), lowercase `moonshot` is a moon-shot idea.
   Requires `match_in_text()` to receive the **original-case** text; lowercasing first silently breaks it.
13. **Client's top focus: Apple Intelligence — 入华优先.** Two levels, both decided on the **headline only**
   (`curation.apple_focus`), and carried as a `focus` field through the whole pipeline:
   - `apple_intel_cn` (+4): `Apple Intelligence` / `Siri` / `Apple AI` **plus** a China signal — `China`, `mainland`,
     `国行`, `CAC`/`网信办`, or a Chinese model partner (`Alibaba`/`Qwen`/`Baidu`/`Tencent`…).
   - `apple_intel` (+2): other Apple Intelligence / Siri / AI-agent news, incl. reviews and how-tos (client wants these).
   Bare `chinese` does **not** count as China: "Apple Intelligence in Chinese language" is a worldwide language
   rollout, not 入华 — the pattern requires `chinese market/users/regulators/…`.
   Effects: (a) scoring — 入华 outranks every other item; (b) ordering — `build_doc.group_by_topic` lifts all
   `focus` items to the top of their brand, 入华 first, **without touching other brands' order** (it clusters the
   full item set first, then does a stable partition by focus); (c) attribution — focus items are placed by the
   **earliest-mentioned** entity instead of the usual 国内优先 rule, so "Apple Intelligence launches in China with
   Alibaba's Qwen model" stays under Apple rather than being moved to 阿里巴巴. Both `curation.unique_placement`
   and `prep_final`'s re-attribution must apply this branch, or the second pass undoes the first.
14. **Noise categories that reappear in every batch** — all judged on the headline only. When a new export
   arrives, skim the output for these before delivering:
   零售/散户股价叙事（`If You Invested $1,000…`、`Stock Is Now Cheaper Than…`、`Options Traders…`）·
   同词异义（`intel report` ＝ 情报，不是 Intel；`Big Apple` ＝ 纽约）· 本地商家好评/SEO 软文（`Google Reviews Recognize…`）·
   罪案/司法花边 · 致富教程/副业（`Turn Your Job Skills Into A $100,000 Business`）· 娱乐职业转型 ·
   软件 bug/更新日志（`Excel 2016 copy-paste bug`）· 富豪榜/地产 · 通稿换皮（`Xinhua Silk Road`）·
   怀旧开箱 · 个人使用技巧 · 社媒使用场景/公益（`missionaries take to TikTok`）· 第一人称走访见闻。
   **Individual-use-tips excludes Apple Intelligence / Siri / AI**: the client explicitly wants those reviews and
   how-tos kept and boosted (rule 13), so that rule carries a negative lookahead.
15. **Institution actions aimed at a *known brand* are intelligence, not politics.** `INSTITUTION_ACTION_PAT`
   (asked to brief / seek a briefing / testify / subpoena / congressional hearing / appear before lawmakers)
   exempts a headline from the pure-politics drop **when the headline also names a tracked brand**. Otherwise
   `Nvidia's Huang is asked to brief Congress on reported Chinese spy relationship` dies purely on the word
   `Congress`. Election narratives are unaffected: "Texas Turns Blue…", "Musk spent $445M to help Republicans"
   still drop, because they carry no institution action.
   Also note `campaign` needs a word boundary — bare `campaign` matched `campaigners` and killed
   "Google refused 54K-name petition, say campaigners".
16. **Strong politics overrides business signals.** `STRONG_POLITICS_PAT` (election rout / `persecute` /
   `governor-elect` / `spent at least $X million in` / `lawyer up` / `DOGE` / `loses billions`) drops the item
   **even when** `BUSINESS_SIGNAL_PAT` fires — otherwise "Musk fires back at Democrats over AI regulation after
   midterm rout" survives on the strength of the word `AI`. Deliberately excludes bare `after the midterm`, so
   "Why Shares of Tesla, SpaceX Are Sliding After the Midterm Elections" (market impact) is still kept.
17. **Two-line format**: `英文媒体: 英文标题` / `中文媒体：中文标题`.
   The English line uses an **ASCII colon + space**, and **all three segments — media name, colon, headline — are
   wrapped in hyperlinks** pointing at the same source URL (three `<w:hyperlink>` runs).
   **All entry text is bold**: every segment of both lines (English and Chinese), plus the document title.
   The Chinese line keeps the fullwidth colon and carries no link. Chinese media name has no book brackets.
18. **Glossary one-to-one**: media, brand, and leader names MUST come from《翻译知识库》. Leader H2 is
   `中文名（英文名｜公司）`; English full leader names in the Chinese line are replaced by the KB Chinese name.
19. **China-related tech coverage of every tracked brand is mandatory.** A headline that carries a **China signal**
   (`China/Chinese/Beijing/PRC/mainland/Hong Kong/Taiwan/Shanghai/Shenzhen/Hangzhou`, `CAC/网信办/工信部/商务部`,
   `rare earth`, and Chinese company names — `Huawei/BYD/SMIC/YMTC/CXMT/Alibaba/Tencent/ByteDance/Xiaomi/Baidu/
   DeepSeek/Moonshot/Qwen/Zhipu/MiniMax/SenseTime/Innolight/MetaX/Moore Threads/Iluvatar`, so a headline like
   "Oracle scraps deal to lease chips to Tencent" counts as China even without the word China) **and a tech-topic signal** (chips/semiconductor/foundry/HBM/DRAM/GPU,
   AI/LLM/model/agent, autonomous/self-driving/driverless/robotaxi/FSD, regulation/export control/entity list/
   antitrust/tariff/Congress/hearing) is `china_tech` (`filter3.china_tech_focus`, title only) and must be kept:
   - it is **exempt from every per-brand topic gate** — Tesla EV/sales, Amazon non-AI, Musk non-priority,
     Uber/Lyft delivery, overseas earnings-preview. Example: "Tesla's China sales of FSD cars climb as robotaxi
     pilot expands" previously died on `TESLA_DROP`; "Nvidia loses billions in China as export curbs bite" died on
     `STRONG_POLITICS_PAT`.
   - it is **exempt from the strong-politics drop** (US-China tech regulation *is* the intelligence, not an
     election narrative).
   - `curation.priority_score` adds **+2** (`FOCUS_CN_TECH`), so these items surface at the top of their brand.
     Same pattern as Apple Intelligence (rule 13); the two pattern sets are duplicated on purpose in
     `filter3.py` and `curation.py` — **edit both**, or inclusion and ordering silently disagree.
   - Crypto stays excluded even with a China signal.

## Maintain the filter

Alias tables and exclusion rules live in `scripts/filter3.py`:
`DOMESTIC_BRANDS` (42) / `DOMESTIC_LEADERS` (14) / `AUTO_BRANDS` (12) / `AUTO_LEADERS` (10) /
`OVERSEAS_BRANDS` (13) / `OVERSEAS_LEADERS` (15), plus `EXCL` (48 low-value rules), `PR_PAT`, and the
per-brand regexes used by `topic_gate()`.

**A Chinese name in the KB does NOT make a brand trackable.** `DOMESTIC_BRANDS` / `AUTO_BRANDS` /
`OVERSEAS_BRANDS` are what `placed()` actually searches — a company present only in
`品牌名称翻译知识库` has a translation but no attribution, so its articles are silently discarded.
`filter3.py` now prints a startup `WARNING` listing every KB brand with no alias entry (this is how
云徙科技/Yunxi Technology was found missing); `Cruise` and the KB category rows (`Robotaxi`, `Cybercab`) are
expected in that list and are skipped. **The check is per name-segment, not per row**: `Zhipu / Z.AI` passed
row-level checking while every overseas story was bylined `Z.AI`, so the whole line was being dropped —
`Z.AI`, `GLM-x`, `ChatGLM` and `清言` are now aliases of `智谱/Zhipu`. Watch for the same pattern with any
brand that has a different overseas name than its Chinese one (`MiniMax`↔`海螺/Hailuo`, `月之暗面`↔`Kimi`).
When adding a competitor, add it to **both** the KB and the alias table, then verify a real headline lands.
Domestic chip / memory / optics names are grouped together in the table (沐曦 MetaX, 摩尔线程 Moore Threads,
长鑫存储 CXMT, 长江存储 YMTC, 天数智芯 Iluvatar, 壁仞科技 Biren, 中际旭创 Innolight) — keep new
semiconductor names in that block. Note `Biren` is also an Indian given name (Biren Singh), hence its alias is
case-sensitive with a name exclusion; follow that pattern for any brand that collides with a common word.

- `topic_gate()` — Yahoo stock-noise, Musk, Tesla, Uber/Lyft delivery, Amazon, earnings-preview, crypto.
  Also **title-only**, same as attribution. Earnings-preview applies to **pure overseas competitors only**;
  auto and domestic previews are kept (Uber's robotaxi capex lives there).
- `cruise_hit(title)` — `Cruise` is deliberately **not** in `AUTO_BRANDS`. Admitted only when the headline
  contains `cruise` **and** an AV context (gm / robotaxi / self-driving / autonomous / driverless / waymo),
  **and** no travel/cinema signal (tom cruise / cruise ship / mediterranean / box office…).
- `is_broken_title()` — rejects mangled exports where several headlines are concatenated (>220 chars, or a
  repeated 20/30/40-char prefix).
- `APPLE_FOOD_PAT` vs `APPLE_TECH_PAT` — keeps recipe/orchard "apple" out of the Apple bucket.

`scripts/curation.py` holds `PRIORITY` (regulation/IPO/funding/earnings/AI-strategy = 2, chip/china/UK/UN/
employment/robotaxi/model/exclusive = 1, leader-viewpoint +1, OpenAI/Anthropic IPO+funding +3).
**The score only orders items inside a brand — it never decides inclusion.** A score of 0 is not a noise signal.

`references/filtering_criteria.md` is the readable mirror (§七 alias tables, §八–§十一 successive refinements);
keep it in sync when editing code. Rebuild the KB with `scripts/consolidate_kb.py` after edits.

## Known pitfalls

Read `references/pitfalls.md` before each run. Highest-risk, all previously observed:

- Never let `keywords` decide placement or gating. It is a term→frequency map (`{"Cruise":12,"GM":5,"robotaxi":1}`)
  and produced Qualcomm→Uber, Yum China→美团, Leidos→Intel, Chevy Bolt→GM Cruise.
- **Dedupe before capping** — when a cap existed, five copies of one Bloomberg wrap ate all five Apple slots.
- Adding a media name is not enough: check it is not silently killed by the country gate (pitfall #30).
- Assert `len(ZH) == len(final)`; build `zh.json` from `final`'s `idx` order via `make_zh_template.py`.
- `Meta` needs a boundary regex or Meta-Optics/metaEye slips in; `GLOBE NEWSWIRE` needs the `?` space tolerance.
- Hit rate matters more than rules: after each change, re-verify the specific articles that motivated it.

## Translation step

`make_zh_template.py` → `zh_template.json` (idx / media_kb / section / entity / en / zh).
Fill every `zh`, save as `zh.json`, run `check_zh.py`, then `publish_daily_report.py` (it calls `build_doc.py`). Title-level translation only — never read bodies.
Do not pre-translate: selection changes, and `zh.json` is keyed by `idx`.

**Wording rules (client has flagged these; `scripts/check_zh.py` enforces them):**

- **`AI` is never translated.** Write `AI`, never 「人工智能」. `AI agent` → `AI 智能体`,
  `AI chip` → `AI 芯片`, `generative AI` → `生成式 AI`. Keep `AI` and the Chinese noun separated by a space,
  matching the existing typography. `LLM` / `GPU` / `AGI` / `Agent` are also kept in Latin script.
- **But an `AI` inside a company name follows the glossary.** `Z.AI` / `Z.ai` → **智谱**,
  `01.AI` → 零一万物, `Pony.AI` → 小马智行. Product names stay as-is: `GLM-5`, `ChatGLM`, `ChatGPT`,
  `Claude`, `Gemini`, `Apple Intelligence`. So `Z.ai launches GLM-5 AI model` → 「智谱发布 GLM-5 AI 模型」.
- **No Latin brand names in the Chinese line.** Google→谷歌, Huawei→华为, Nvidia→英伟达, Tencent→腾讯 …
  per `品牌名称翻译知识库`. Exceptions are the entries whose KB Chinese name is itself Latin
  (OpenAI, Anthropic, Meta, IBM, TikTok, MiniMax) plus 品类词 `Robotaxi`/`CyberCab`.
- Run `check_zh.py` before building: `error` must be 0. It catches 「人工智能」, leftover Latin brand names,
  and missing spaces around `AI`; `--soft` reports without failing (use it when re-checking old issues).


**Reordering shortcut**: when the article set changes only slightly, reuse prior work by mapping
normalized English title → Chinese title from the old `zh_template.json` + `zh.json`, then re-key by the
new `idx`. Verify every `idx` is covered before building.
