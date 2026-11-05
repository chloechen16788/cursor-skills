# 筛选标准与栏目结构（百度竞品同业日报）

本文件是 `scripts/filter3.py` 中竞品/领导人别名表与剔除规则的「可读版」来源。修改筛选口径时，
优先改此文档所描述的逻辑，再到 `filter3.py` 同步对应的字典/正则（两者必须一致）。

## 一、收录主题

优先收录与以下主题相关的报道：
- AI 模型 / 智能体 / 大模型竞争
- 芯片（出口管制、HBM、代工、AI 芯片）
- Robotaxi / 自动驾驶监管
- 业绩 / 财报 / 现金消耗
- 监管（反垄断、诉讼、DOJ/FTC/CMA/Ofcom、欧盟、英国）
- 上市（IPO）/ 融资 / 估值
- 企业领导人观点
- 联合国 / OECD / IEA 等机构 AI 预警
- 就业影响

## 二、四大板块（顺序固定）

| 顺序 | 板块 | 合并/拆分 | 上限 |
|------|------|-----------|------|
| 一 | 国内企业（含领导人） | 合并板块 | **无** |
| 二 | 自动驾驶（含领导人） | 合并板块 | **无** |
| 三 | 海外竞品企业 | 按品牌拆分 | **无** |
| 四 | 海外竞品领导人 | 按人名拆分 | **无** |

- **不设品牌配额**（`curation.py` 的 `CAP` 全为 `None`）。收录量由剔除规则决定，不由配额决定；
  篇幅靠去重（尤其事件级去重）控制，而不是靠砍条数。
- 海外板块：品牌 → 海外企业；领导人 → 企业领导人。
- **归属一律只看标题**：摘要、关键词频次、正文均不参与，也没有任何回退（详见 §九）。
- 同一篇报道**只归入一个板块 / 一个品牌**：按标题中最早出现的品牌名定唯一归属；
  领导人命中人名时优先归「企业领导人」，国内/自动驾驶标题仍命中本板块品牌则不迁移。

## 三、重点市场（白名单）

仅保留：`United States of America`、`United Kingdom`、`China`、`United Arab Emirates`（中东）。
归一化：`Taiwan → China`、`England → United Kingdom`。

> **媒体白名单优先于本条。** 只要来源在《翻译知识库》媒体表内，即视为显式选定，
> 其稿件**不因所在国被剔除**（新加坡《海峡时报》、加拿大 BNN 彭博、澳洲《澳大利亚人报》均属此类）。
> 本条仅对「非白名单来源」生效——但非白名单来源本就已被 §四 挡掉，故实际执行顺序为：先认媒体，再谈市场。
> 详见 §十一。

## 四、媒体口径（仅收录 KB 媒体）

- 仅收录《翻译知识库》「媒体名称知识库」所列媒体。
- 来源名做归一化：`* Online` 后缀去除；另有显式映射（见 `filter3.py` 的 `SRC_TO_KB`）：
  `Bloomberg News Online→Bloomberg`、`Associated Press Online→The Associated Press`、`Wired Online→WIRED`、
  `Aljazeera International→AI Jazeera`、`BNN Bloomberg Online→BNN Bloomberg`、`KNTV-TV Online→NBC Bay Area`、
  `KPYX-TV Online→CBS`、`KOVR-TV Online→CBS`。
- 语言：仅收录 `languageCode == 'en'`（英文稿件）。
- **媒体白名单优先于重点市场**：在库媒体不受所在国限制（详见 §十一）。

## 五、剔除规则

**新闻稿 / Press Release（必剔）：** 标题/作者/摘要中出现以下电头即剔除 ——
`prnewswire`、`globe newswire`（注意中间空格）、`einpresswire`、`business wire`、`news direct`、`marketwire`、
`accesswire`、`prweb`、`issuewire`、`send2press`、`newsfile`、`cision`、`press release`。
重点甄别 Benzinga 与美联社(AP)分发的通稿。

**主题剔除（`EXCL`，共 28 条，命中即丢）：**

| 类别 | 涵盖 |
|---|---|
| 股评与评级 | 分析师评级/目标价/荐股；股评栏目（Cramer、Heard on the Street、Stock Movers、Bulls vs Bears）；大盘指数行情（S&P 500、期货、盘前）；投资论点/估值（P/E、Crown Jewel、FOMO、ETF）；纯估值倍数；律所投资者公告 |
| 消费电子 | iPhone/iPad/MacBook 评测与导购；硬件配件（防盗支架等）；消费硬件价格规格（RTX、GPU 涨价）；系统使用技巧（Windows 11 提速/8GB）；谷歌手机 Pixel；智能音箱；医学/临床/疫苗 |
| 通稿与程序化内容 | 市场报告/CAGR/行业报告；低价值通稿（price target、podcast、Robinhood）；财报电话会逐字稿 |
| 财经栏目 | Bloomberg Tech、CNBC newsletter、Fortune Tech；财经视频/综述（Watch…、World in Brief）；广告营销软文 |
| 生活杂讯 | 网约车纠纷、钓鱼诈骗提醒、急救车/Uber 打车趣闻 |
| 同名误判 | 亚马逊雨林/河流；Meta-Optics/metaEye；苹果水果/菜谱/果园（`APPLE_FOOD_PAT` 对 `APPLE_TECH_PAT`）；Windows 补丁漏洞、安卓更新 |
| 其他 | 低价值股市噪音（ETF 调仓、个股波动快讯）；class action 招揽、mark your calendars 等模板文 |

**标题损坏剔除：** `is_broken_title()` —— 长度 >220 字符，或开头 20/30/40 字符重复出现
（监测导出偶有多条标题粘连成一条），无法翻译也无法归位，直接剔除。

## 六、条目格式（两行式）

> 完整执行顺序见 `workflow.md`；脚本产出即为最终形态，一般无需手工调整。

```
英文媒体: 英文标题        ← 半角冒号+空格；三段均为超链接（同指向原文）；整体加粗
中文媒体：中文标题        ← 全角冒号；不带链接；整体加粗
```

- **英文行用半角冒号 `: `**，且**媒体名、冒号、英文标题三段各自包在超链接里**，都指向同一原文 URL。
- **条目内容一律加粗**：英文行三段、中文行的媒体名与标题，以及文档大标题，全部 `w:b`。
  中文行仍为全角冒号 `：`、不带链接。副标题与「筛选说明」为说明性文字，保持浅灰细体。
- 中文媒体名**不带书名号**（例：「财富」「CNBC」按 KB 显示）。
- 中文标题内出现的领导人英文全名，自动替换为《翻译知识库》标准中文译名。

## 七、竞品 / 领导人别名表（当前口径）

> 以下为「标准化实体名 → 匹配别名」的精简版，完整定义在 `scripts/filter3.py` 的对应字典。
> 增删竞品时，直接编辑 `filter3.py` 中 `DOMESTIC_BRANDS / DOMESTIC_LEADERS / AUTO_BRANDS / AUTO_LEADERS / OVERSEAS_BRANDS / OVERSEAS_LEADERS`。

- 海外企业：Alphabet/Google（含 Gemini/DeepMind）、Microsoft、Meta、Apple、Amazon、Nvidia、IBM、Intel、**Tesla**、**OpenAI（含 ChatGPT/GPT）**、**Anthropic（含 Claude）**、Mistral、Perplexity
- 国内企业：阿里巴巴/通义千问/Qwen、字节跳动/抖音/豆包/火山引擎、腾讯/微信/混元、华为/深度求索/智谱/**月之暗面/Moonshot（含 Kimi）**/百川/零一万物/Manus/商汤/小米/美团/京东/拼多多/Temu 等
- 自动驾驶：Waymo、Cruise、Zoox、Wayve、Uber、文远知行、小马智行、小鹏、滴滴、Lyft、Cybercab
- 领导人：Sundar Pichai、Satya Nadella、Sam Altman、Dario Amodei、Mark Zuckerberg、Jensen Huang、Tim Cook、Andy Jassy、Jeff Bezos、Elon Musk 等（含对应的国内/自动驾驶领导人）

> **产品名归公司，不单列实体**：ChatGPT / GPT → OpenAI；Claude → Anthropic；Kimi → 月之暗面/Moonshot；Gemini → Alphabet/Google。
> 模型名、聊天机器人名一律视为所属公司的产品线，避免同一公司在报告中出现两个并列小节。
> 新增同类产品时，把产品名加进该公司别名列表即可，**不要**新建独立实体。

> 特别注意 Meta 匹配正则 `(?<![a-z0-9])meta(?![a-z0-9A-Z\-])`，避免误命中 Meta-Optics / metaEye。
> 吴泳铭标准英文名取 `Eddie Wu`，`Yongen Wu` 仅作变体别名。

## 八、2026-11-03 精细化口径（9 条，对应 filter3 的 topic_gate / curation 加权）

> ⚠️ **本节为历史记录，部分条款已被 §九 / §十 / §十一 取代。** 冲突时以后者为准。
> 主要差异：①判定依据已从「标题+摘要+关键词」收窄为**只看标题**（§九）；②不再设品牌配额（§十）；
> ③媒体白名单优先于重点市场（§十一）。以下保留原文以便追溯口径演变。

1. **Yahoo Finance 纯股价分析降噪**：仅当来源含 `yahoo` 且标题/摘要/关键词为纯股价波动（shares/stock rise·fall、price target、upgraded/downgraded、market cap 等）且**无**实质话题（AI/芯片/云/业绩/监管/上市融资等）时才剔除。
2. **Cruise 品牌去人名噪音**：Cruise **不出现在 `AUTO_BRANDS` 表**，改由 `cruise_hit()` 判定——必须同时满足：① `\bcruise\b` 出现在**标题**；② 同一标题内出现 AV 语境（gm / robotaxi / self-driving / autonomous / driverless / waymo / av）；③ 不含旅游/影讯信号（tom cruise / cruise ship / cruise line / mediterranean / box office 等）。**关键词字段不参与判定**（监测导出的 keywords 是「词→频次」映射，含 `"Cruise":12,"GM":5,"robotaxi":1` 会让 Chevy Bolt 车评被误判）。
3. **马斯克 / 特斯拉 话题门控**：
   - 马斯克（领导人）文章：若主要关于 星链 / SpaceX / 推特(X平台) / grok 且**不**含重点话题（AI/Agent/Robotaxi/Cybercab/机器人/芯片/重大政治事件）则剔除。
   - 特斯拉（新增品牌）文章：若主要关于**电动车更新换代**（new model / refresh / redesign / facelift / next-gen）且不含 FSD/Robotaxi/Cybercab/机器人/芯片/自动驾驶 则剔除；FSD/Robotaxi/Cybercab/机器人/芯片/自动驾驶 内容正常收录。
4. **Uber / Lyft 外卖剔除**：若文章主要关于 外卖（Uber Eats / food delivery / DoorDash 等）且不含 自动驾驶/Robotaxi/无人驾驶 则剔除；Robotaxi/无人驾驶 内容正常收录。
5. **亚马逊 电商/物流/外卖/消费硬件剔除**：若文章主要关于 电商/物流/仓储/零售/生鲜/外卖 或 消费硬件（Echo/Kindle/Alexa/Fire TV/Ring 等）且**不**含 芯片/云(AWS)/AI/Agent/自动驾驶/机器人 则剔除；芯片、云、AI、Agent、自动驾驶（如 Zoox）内容正常收录。
6. **财报前瞻剔除（保留实际业绩）**：标题/摘要/关键词出现「earnings preview / ahead of earnings / what to expect / to report earnings / on deck / everything you need to know ahead」等前瞻表述时剔除；但若同时出现实际业绩信号（reported / beats / misses / quarterly revenue / fiscal 等）则**不**剔除（保留实际业绩）。
7. **加密货币剔除**：标题/摘要/关键词出现 crypto / bitcoin / ethereum / blockchain / NFT / web3 / defi / coinbase / binance 等即剔除。
8. **业绩 / 上市融资 重点关注**：`curation.py` 中 业绩、上市(IPO)、融资 权重提升为 2；**OpenAI / Anthropic 的上市融资额外 +3 加权**，确保优先入选。
9. **模型功能更新收录**：新增 `模型更新/model` 识别（new model / model update / GPT-/Claude-/Gemini 版本 / feature update / rolled out 等），模型功能更新类报道正常收录。

## 九、2026-11-04 口径修正（**纯标题判定**）

> 已在 `scripts/filter3.py`、`scripts/prep_final.py` 实现。**这是当前唯一口径**。

1. **品牌/领导人归属「只看标题」**：`placed()` 只对 `title` 做匹配，摘要、关键词频次、正文一律不参与，**无任何回退**。
   - 起因：靠关键词频次归位导致 `Qualcomm…After Earnings`→Uber、`Yum China…Transcript`→美团、`Leidos…`→Intel、`Commercial Vehicle Group…`→Zoox、`X-Energy Analyst…`→小马智行、选举夜报道→Google、`Chevy Bolt` 车评→GM Cruise。
   - 代价（已知并接受）：英文标题不点名的稿件会整条不入报，例如 `China's 'Lipstick King'…`（实为阿里淘宝直播）不再归入阿里。若需回收，只能改标题匹配别名，不可恢复关键词回退。
2. **`topic_gate` 同样只看标题**：门控与归属同一口径，避免「归属看标题、门控看摘要」造成口径不一致。
3. **`cruise_hit(title)`**：仅标题同时满足「含 `\bcruise\b`」+「含 AV 语境（gm/robotaxi/self-driving/autonomous/driverless/waymo/av）」+「不含旅游/影讯信号」才认作 GM Cruise。Cruise 不在 `AUTO_BRANDS` 表内。
4. **剔除判定**只用 标题+摘要（摘要仅用于识别 PR 电头与硬件/生活类），不读关键词与正文。
5. **三道去重**（`prep_final.py`）：URL 去重 → 精确标题去重（CBS 本地台同一稿）→ **近似标题去重**（同板块+同实体+同媒体，词集 Jaccard ≥ 0.5 保留 impact 最高一条；解决 Bloomberg 改题重发的行情综述、WSJ 同选题双标题）。
6. **新增低价值剔除**：财报电话会逐字稿（`earnings call transcript`）、生活/消费杂讯（ambulance driver / did you know you can use / options action:）、系统使用技巧（`windows 11 … faster/8GB/requirements`）、纯估值倍数评论（`forward p/e`）。
7. **`ACTUAL_EARNINGS_PAT` 去掉 `results (?:on|of)`**；**`AMAZON_KEEP` 去掉裸 `\bai\b`**（改用 aws/cloud/chip/agent/zoox 等实质信号）。

## 十、2026-11-04 二次修正（取消限额 · 事件去重 · 前瞻分板块）

> 用户明确：**不设置数量限额**；**海外竞品剔除财报前瞻，自动驾驶与国内竞品保留**；洛杉矶时报加入媒体库。

1. **取消每品牌限额**：`curation.py` 的 `CAP` 全部置为 `None`。收录量由「剔除规则」决定，不再由配额决定。
   踩过的坑：原 `CAP={'海外企业':5}` 使 Apple 96 条候选只进 5 条，Siri AI、Anthropic IPO、Nvidia 中国业务等 10 条重点稿被挤出。
2. **财报前瞻分板块**：`topic_gate` 第 6 条改为仅当 `ovb` 命中且无 auto/dom 命中时才剔。
   Uber/Xpeng 等自动驾驶前瞻（含 robotaxi 投入）与国内竞品前瞻一律保留。
3. **事件级去重（`prep_final.py --per-event`，默认 1）**：同板块+同实体内，两条标题 Jaccard≥0.5
   或共享≥2 个「稀有实词」（该品牌候选内出现 ≤4 次）即判定同一事件，只保留最靠前一条。
   效果：「Google 关闭学校搜索」12 个版本→1 条；「OpenAI 聘前陆军部长」7 个版本→1 条。
4. **苹果（水果）排除**：`APPLE_FOOD_PAT` 命中菜谱/果园/果汁等且无 `APPLE_TECH_PAT`（iphone/siri/tim cook…）时不计入 Apple。
   踩过的坑：`José Pizarro's recipe for mussels with cider, chorizo and apple` 曾排进 Apple 桶第 2 名。
5. **新增低价值剔除（属既有「低价值」范畴的细化）**：
   消费电子评测/导购、股评/荐股栏目、分析师评级与目标价、大盘/指数行情、律所投资者公告、
   投资论点/估值（P/E、Crown Jewel、FOMO 等）、财经栏目/通讯（Bloomberg Tech、CNBC newsletter）、
   广告营销软文、财报电话会逐字稿、生活消费杂讯。
6. **媒体库新增**：`Los Angeles Times / 洛杉矶时报`（此前 Waymo 洛杉矶扩张稿因媒体不在库被挡）。

> 注意：`pscore==0` **不是**噪音判据。该桶里有 OpenAI 任命前陆军部长、好莱坞支持《纽时》诉 OpenAI 版权、
> Anthropic 5.67 亿美元亏损、Meta 发债 200 亿等高价值稿——只能按议题类别剔除，不能按评分一刀切。

## 十一、媒体白名单与「重点市场」的关系（2026-11-04 补充）

6 个外部指定域名核查结论：

| 域名 | 数据中的来源名 | 媒体库状态 |
|---|---|---|
| latimes.com | Los Angeles Times Online | 在库（洛杉矶时报） |
| theaustralian.com.au | The Australian Online | 在库（澳大利亚人报） |
| newyorker.com | New Yorker | 在库（纽约客） |
| bnnbloomberg.ca | BNN Bloomberg Online | 已补入（BNN彭博社） |
| nbcbayarea.com | KNTV-TV Online | 已补入（NBC湾区台） |
| politico.com | Politico | 已补入（政治新闻网） |

**关键规则：媒体白名单优先于重点市场。**
`filter3.py` 主循环已把媒体解析提到国家判断之前——只要媒体在《翻译知识库》媒体表内，即视为显式选定，
其稿件**不因所在国被丢弃**。此前「媒体在库 + 国家不在重点市场」的稿件会被静默丢掉，受影响的有：
新加坡《海峡时报》11 条、加拿大 BNN 彭博 3 条、澳洲《澳大利亚人报》1 条。
调整后本期由 158 条增至 161 条。

**本地台映射**：`src_norm` 除剥离 ` Online` 后缀外，另加显式映射
`BNN Bloomberg Online → BNN Bloomberg`、`KNTV-TV Online → NBC Bay Area`、
`KPYX-TV Online/KOVR-TV Online → CBS`。

**标题损坏剔除**：`is_broken_title()`——监测导出偶有多条标题粘连、同一片段重复多次
（曾见南华早报一条标题把 4 条不同新闻拼在一起），长度 >220 字符或首 20/30/40 字符重复出现即剔除。

**新增生活杂讯**：网约车纠纷（driver cancels ride / wrong direction）、钓鱼诈骗提醒（phishing scam / beware of … scam）。

## 十二、2026-11-05 口径补充（促销/影视/股价 · Moonshot 大小写 · 同类话题相邻）

### 1. 新增三类剔除（只看标题）

体裁类特征必然写在标题上；若连摘要一起扫，会被摘要里的 **premarket trading**、**discount shopping platform**、
**movie** 等词误伤（实例：`Apple shares slide as higher memory costs fuel margin concerns` 因摘要含
`premarket trading` 被判为「大盘行情」而误剔）。因此新增 **`TITLE_ONLY_RULES`**：下列规则只作用于标题。

| 规则 | 剔除对象 | 关键写法 |
|---|---|---|
| 促销/折扣/导购（`PROMO_PAT`） | 任何品牌的纯促销 | `$X off`、`X percent off`、`price drop/cut`、`record-low price`、`black friday`、`cyber monday`、`prime day`、`best ... deals`、`already on sale`、`drops to $X` |
| 苹果影视内容（`APPLE_MEDIA_PAT`） | Apple TV+ 剧集/电影 | `apple tv+`、`apple studios`、`tv series/show`、`season N`、`box office`、`emmy/oscar` |
| 纯股价波动（`STOCK_MOVE_PAT`） | 仅股价涨跌、无实质议题 | `stock/shares + rises/falls/climbs/slips`、`what's going on with ... stock`、`premarket` |

**必须避开的误伤写法**（都已验证保留）：
- 裸 `deal`（`ADNOC OpenAI Deal` 是商业交易）→ 只用 `best ... deals` / `deals of the day`
- 裸 `sale`（`sales` 是销售额）→ 只用 `on sale (now/for/at)`、`already on sale`
- 裸 `discount`（`discount shopping platform` 指折扣电商模式）→ 只用 `discount code`
- `goes on sale`（新品开售）→ 不算促销
- 含实质议题（memory/margin/earnings/chip/AI/监管…）的股价稿 → 保留
- `Apple TV 4K`（机顶盒硬件）→ 不算影视

### 2. Moonshot：公司 vs 登月计划

`moonshot` 是普通词（登月式构想），公司名首字母大写。别名表引入 **`!` 前缀 = 大小写敏感正则**：

```python
'月之暗面/Moonshot': ['!(?<![A-Za-z])(?:Moonshot|MOONSHOT)(?![A-Za-z])', '月之暗面', 'kimi'],
```

**关键前提**：`match_in_text()` 必须接收**原始大小写**文本，否则先 `.lower()` 会让大小写敏感正则永远失配
（曾因此让 `Moonshot AI raises $500M` 归不到月之暗面）。归属与门控现在都传原始标题。

另有两道兜底（`exclusion_reason`，只看标题）：
- 小写 `moonshot` 且无公司语境（`Moonshot AI` / `kimi` / `月之暗面` / `LLM` / `杨植麟`）→ 剔
- 有登月语境（`NASA` / `moon` / `lunar` / `rocket` / `artemis`）且非公司语境 → 剔

效果：`Moonshot AI raises $500M` ✓收、`MOONSHOT unveils new model` ✓收、
`NASA's moonshot to the Moon` ✗剔、`A moonshot plan to cure cancer` ✗剔、
`moonshot thinking at Google X` ✗剔且正确归 Google。

### 3. 同一事件的多篇报道相邻（`build_doc.py`）—— 从数据自动发现，无手工词表

**早期做法已废弃**：曾用手写事件标签（`school_ai` / `mna` / `buyout` / `watch_audio`…）。
问题很明确——标签是照着当期数据写的，换一批数据就失效，无法支撑每日生成。**已全部删除。**

现行算法（词级单链合并 + 规模护栏）：

1. 每个词 → 包含它的标题集合。只出现在 1 条标题的词无共现证据；出现在 ≥80% 标题的词
   （品牌名、`apple`、`google` 等）无区分度 —— 两者都排除。
2. 按标题集合从大到小处理词；若某词与已有簇的标题集合重合度 ≥ `EVENT_OVERLAP`（0.5，
   用 min 归一以容忍长短标题不对称），并入该簇。
3. **护栏**：单簇覆盖标题数不得超过 `EVENT_CAP`（0.55）× 该实体总数。
   没有这道护栏，大品牌会因**链式传递**塌缩成一个巨簇 —— 实测旧批次 Apple 46 条曾被并成 45 条一簇。
4. 剩余未覆盖的标题各自独立成簇，不并成一个大「其他」。
5. 簇间按簇内最高 `impact` 降序，簇内按 `impact` 降序。

**阈值回归**（新旧两批数据同时验证）：

| 参数 | 取值 | 依据 |
|---|---|---|
| `EVENT_OVERLAP` | 0.5 | 新批次 Google 学校政策 12 篇、马来西亚投资 8 篇、离职补偿 3 篇，Uber 财报 10 篇均完整成簇；0.6 起大簇开始碎裂 |
| `EVENT_CAP` | 0.55 | 旧批次 Apple 46 条分为 [21,10,7,3]；无护栏时塌缩为 45 条一簇 |

实测分组（新批次）：

| 品牌 | 分组结果 |
|---|---|
| Google 25 条 | 学校搜索政策 12 / 员工离职补偿 3 / 马来西亚数据中心投资 8 / 其余独立 |
| Uber 22 条 | Q3 财报 10 / Robotaxi 布局 4 / AI 智能体叫车 2 / 无人车队 4 |
| 腾讯 8 条 | Oracle 取消 70 亿交易 5 / 发布 AI 模型 3 |

> 已知局限：偶有 1–2 条词汇相近但事件不同的稿被带入相邻簇
> （如 TeraWulf 数据中心融资挨着马来西亚投资）。这是纯词面方法的固有误差，
> 代价远小于「同一事件被拆散」，且无需维护词表。

定时飞书发布不跑 `build_doc.py`。发布脚本在每个品牌内仍按标题归组后按影响力排序，不会套用上面的自动分簇。分簇算法留在这里，供对照 Word 版的条目顺序。

### 4. 顺带修复

`SRC_TO_KB` 补 `Nikkei Asian Review → Nikkei Asia`（原缺失，导致该媒体稿件被当作野媒体丢弃）。

## 十三、2026-11-05 二轮补充（纯政治 · 软文/生活类 · 事件去重加强）

### 1. 纯政治评论剔除（`POLITICS_PAT`）

选举 horse-race、民调、党派攻防类报道，**在不含任何商业信号时**剔除。判据是两条正则的组合：
`POLITICS_PAT` 命中 **且** `BUSINESS_SIGNAL_PAT` 未命中 → 剔。

- 剔：`Texas Turns Blue in Rebuke of Trump, Musk and GOP`、`Voters Set $400 Million of Elon Musk's Money on Fire`
- 留：`Why Shares of Elon Musk's Tesla, SpaceX Are Sliding After the Midterm Elections`（含 tesla/股价，属市场影响）
- 留：`Grant Cardone Warns ... Could Spell Trouble for Elon Musk's SPCX, AI Bets`（含 spcx，属业务影响）

起因：`MUSK_DROP` 只匹配 星链/SpaceX/X/Grok 类稿件，纯选举评论不含这些词，因此整批中期选举报道涌入（马斯克 26 条中 19 条为选举评论）。这是规则缺口，非设计意图。

### 2. 新增软文/生活类剔除

| 规则 | 剔除对象 |
|---|---|
| 律所/事故索赔广告 | `Car Accident Attorney Explains Uber Claims`、`free consultation`、`no win no fee` |
| 商业软文/产品上架 | `wins two 2026 ... Partner awards`、`Now Available on ... Marketplace`、`Logo New Website`、`OTC:` |
| 生活/情感专栏 | `dating advice`、`Is It Rude to ...`、`sparks a debate`、`my 7 Sonos speakers` |
| 个人理财/攻略 | `5 ChatGPT Prompts To Get Out Of Debt`、`prompts to make money` |
| 清单体/调侃文 | `17 better ways ...`、`N things/reasons/lessons`、`could have wasted` |
| 他业类比 | `the "Uber of sales"`（主语非本公司，纯比喻） |
| 人物/影视访谈 | `On Life Since the Release of His Film`、`The Man Who Inspired ...` |
| 估值补充 | `absurdly cheap`、`overvalued`、`undervalued`、`fair value`、`hidden gem` |

另修 `STOCK_MOVE_PAT`：原只匹配 `What's Going On With ... Stock`，补 `What Is/Are` 变体。
另加 `Big Apple` 判定——标题含 `Big Apple` 且无 iPhone/Siri/Cupertino 等科技信号时，视为纽约市而非苹果公司。

### 3. 事件去重加强（`prep_final.event_dedup`，需显式 `--event-dedup`）

定时命令不带这个参数，默认保留各家媒体对同一事件的报道。下面的合并效果只在加上 `--event-dedup` 时出现。

原判据只认「Jaccard≥0.5」或「共享≥2 个稀有词」，遇到**各家换主语**的同事件报道会漏合：
`Zohran Mamdani Accuses Google...` / `Bernie Sanders Accuses Google...` 只共享 `{accuses, school}`，
`school` 出现频次高、不算稀有，于是 10 条「Google 关闭学校搜索」全部保留。

两项改进：

1. **词形归一化**（`EV_SYN` + `_canon`）：`centre→center`、`15bn→15billion`、`schools→school`。
   缺这层时，「data center expansion」与「data centre expansion」会被当成两个事件。
2. **新增判据 4**：共享 ≥2 个实词且其中至少 1 个稀有 → 视为同事件。
   配合 `EV_STOP`（已剔除品牌名、人名、高频虚动词）避免虚高相似度：
   曾把「太空数据中心」「1000 亿无线通信」「进军印度」错并成一簇，就是 `Elon`/`Musk`/`wants` 计入共享所致。

效果：本期 455 条原始 → 129 候选 → 120 curated → 87 条；「Google 关闭学校搜索」10 版→2 条、
「Google 投资马来西亚 15 亿」5 版→1 条；马斯克 26→8 条。

### 4. 误合并修复（同日追加）

审出 2 处误删 —— 只因共享通用技术名词就被判为同事件：

| 被误删 | 误并到 | 误判依据 |
|---|---|---|
| `TeraWulf gets credit backstop from Google for Anthropic data-center project` | `Google to invest $15bn in Malaysia's data center expansion` | 仅共享 `{data, center}` |
| `Anthropic tweaks how Claude Code handles requests about making games` | `Top Anthropic product leader Cat Wu ... has left` | 仅共享 `{claude, code}` |

**根因很反直觉**：`data`/`center` 这类通用词因为只出现在一小簇里，df 反而低，被当成「稀有词」；
而 `school`/`search` 这些真正的事件词因为被反复报道，df 高、不被认作稀有。**判据取反了。**

修法：
1. 新增 `EV_GENERIC`（通用技术/商业名词白名单外的黑名单：data/center/model/code/cloud/chip/
   platform/service/product/market/invest/billion/deal…），这些词即使低频也**不算有效稀有词**。
2. 本公司产品名加入 `EV_STOP`（claude/chatgpt/gemini/copilot/grok/siri/codex），作用等同品牌名。
3. 判据简化为三条：`Jaccard ≥ 0.5` 或 `有效稀有词 ≥ 2` 或 `共享 ≥ 2 且有效稀有词 ≥ 1`。

效果：83 → **87 条**，救回上述 2 条独立新闻 + 2 条措辞差异较大的同事件稿
（Oracle 腾讯交易的第 4 个版本、马来西亚投资的 2027/2028 表述）；学校政策仍保持合并，**未丢失任何原有条目**。
