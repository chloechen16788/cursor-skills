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
英文媒体：英文标题（超链接）
中文媒体：中文标题
```

- 中文媒体名**不带书名号**（例：「财富」「CNBC」按 KB 显示）。
- 英文标题行保留英文原名 + 外部超链接（符合「英文媒体：英文标题」）。
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
7. **`ACTUAL_EARNINGS_PAT` 去掉 `results (?:on|of)`**；**`AMAZON_KEEP` 去掉裸 `\bai\b` 和裸 `deal`**（改用 aws/cloud/chip/agent/zoox/anthropic/openai 等实质信号）。`Kindle deal` 不保留。

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

