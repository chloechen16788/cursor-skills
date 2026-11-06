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

## 二、板块（`section` 字段，顺序固定）

`section` 字段仍是国内企业、自动驾驶、海外企业、企业领导人。飞书正文只印有条目的栏目，标题为
「一、国内竞品（含领导人）」「二、自动驾驶竞品（含领导人）」「三、海外竞品（含领导人）」。
能解析到所属品牌的领导人挂到品牌下
（马云 → 国内企业/阿里巴巴，Sundar Pichai → 海外企业/Alphabet/Google，Dara Khosrowshahi → 自动驾驶/Uber），
所以「企业领导人」通常没有标题。解析不到的领导人保留自身实体，不丢条目。埃隆·马斯克没有单一品牌，仍是自动驾驶里的独立实体。
不要把已经归到品牌下的领导人再挪回去。

| 顺序 | `section` | 内容 | 上限 |
|------|-----------|------|------|
| 一 | 国内企业 | 国内品牌，含已归入的国内领导人 | **无** |
| 二 | 自动驾驶 | 自动驾驶品牌，含已归入的领导人；马斯克单独成实体 | **无** |
| 三 | 海外企业 | 海外品牌，含已归入的海外领导人 | **无** |
| 四 | 企业领导人 | 仅当领导人无法归入品牌时才有条目；现行表里通常为空 | **无** |

- **不设品牌配额**（`curation.py` 的 `CAP` 全为 `None`）。收录量由剔除规则决定，不由配额决定。
  定时命令不要加 `--event-dedup`。不同媒体对同一事件的报道都保留。
- **归属一律只看标题**：摘要、关键词频次、正文均不参与，也没有任何回退（详见 §九）。
- 同一篇报道**只归入一个板块 / 一个品牌**：按标题中最早出现的品牌名定唯一归属；
  领导人命中人名时归入其所属品牌（`leader_placement`），国内/自动驾驶标题仍命中本板块品牌则不迁移。

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
英文媒体: 英文标题        ← 半角冒号+空格；整行一条超链接；整行加粗
中文媒体：中文标题        ← 全角冒号；不带链接；整行加粗
```

- 飞书正文没有文档大标题，开头是「原始记录 N 条，筛选入报告 M 条」。栏目是一级标题，品牌是二级标题。没有条目的栏目不印。
- **英文行用半角冒号 `: `**，媒体名和标题放在同一个加粗超链接里，指向原文。
- **中文行整行加粗**，全角冒号 `：`，不带链接。中文媒体名不带书名号。
- 中文媒体名**不带书名号**（例：「财富」「CNBC」按 KB 显示）。
- 中文标题内出现的领导人英文全名，自动替换为《翻译知识库》标准中文译名。

## 七、竞品 / 领导人别名表（当前口径）

> 以下为「标准化实体名 → 匹配别名」的精简版，完整定义在 `scripts/filter3.py` 的对应字典。
> 增删竞品时，直接编辑 `filter3.py` 中 `DOMESTIC_BRANDS / DOMESTIC_LEADERS / AUTO_BRANDS / AUTO_LEADERS / OVERSEAS_BRANDS / OVERSEAS_LEADERS`。

- 海外企业：Alphabet/Google（含 Gemini/DeepMind）、Microsoft、Meta、Apple、Amazon、Nvidia、IBM、Intel、**Tesla**、**OpenAI（含 ChatGPT/GPT）**、**Anthropic（含 Claude）**、Mistral、Perplexity
- 国内企业：阿里巴巴/通义千问/Qwen、字节跳动/抖音/豆包/火山引擎、腾讯/微信/混元、华为/深度求索/智谱/**月之暗面/Moonshot（含 Kimi）**/百川/零一万物/Manus/商汤/小米/美团/京东/拼多多/Temu 等
- **国内芯片 / 存储 / 光模块**（2026-11-05 补入）：沐曦 MetaX、摩尔线程 Moore Threads、长鑫存储 CXMT、长江存储 YMTC、天数智芯 Iluvatar、壁仞科技 Biren、中际旭创 Innolight
- **云徙科技 Yunxi Technology**（2026-11-06 补入）：知识库里一直有译名但别名表漏收，稿件被静默丢弃
- 自动驾驶：Waymo、Cruise、Zoox、Wayve、Uber、文远知行、小马智行、小鹏、滴滴、Lyft、Cybercab
- 领导人：Sundar Pichai、Satya Nadella、Sam Altman、Dario Amodei、Mark Zuckerberg、Jensen Huang、Tim Cook、Andy Jassy、Jeff Bezos、Elon Musk 等（含对应的国内/自动驾驶领导人）

> ⚠️ **有译名 ≠ 能归类。**《翻译知识库》的 `品牌名称翻译知识库` 只负责翻译；真正决定一篇稿能不能归位的是
> `filter3.py` 里的六个别名表。曾出现：CXMT / YMTC / Iluvatar / Biren / Innolight 在知识库里有中文名，
> 但别名表未收录，稿件在归属环节被静默丢弃（日志无异常、报告里只是「少了几条」）。
> **新增竞品的标准动作**：①加知识库品牌表 → ②加 `filter3.py` 别名表 → ③用一条真实标题验证能否归位 → ④重跑管线确认条数变化合理。
> 2026-11-06 起 `filter3.py` 启动时会把「知识库里有、别名表里没有」的品牌直接打印成 `WARNING`，
> 这类静默丢弃从此会暴露在运行日志里（`Cruise` 与 `Robotaxi`/`Cybercab` 等品类行属预期，已排除）。
>
> **别名撞常见词/人名时**用 `!` 前缀写大小写敏感正则，如壁仞：
> `!(?<![A-Za-z])(?:Biren|BIREN)(?![A-Za-z])(?!\s+Singh)` —— `Biren` 也是印度常见名（Biren Singh），
> 不加排除会把政客新闻归到壁仞科技。全大写写法（`BIREN`）也要一并覆盖。

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

> 用户明确：**不设置数量限额**；**海外企业剔除财报前瞻，自动驾驶与国内企业保留**；洛杉矶时报加入媒体库。

1. **取消每品牌限额**：`curation.py` 的 `CAP` 全部置为 `None`。收录量由「剔除规则」决定，不再由配额决定。
   踩过的坑：原 `CAP={'海外企业':5}` 使 Apple 96 条候选只进 5 条，Siri AI、Anthropic IPO、Nvidia 中国业务等 10 条重点稿被挤出。
2. **财报前瞻分板块**：`topic_gate` 第 6 条改为仅当 `ovb` 命中且无 auto/dom 命中时才剔。
   Uber/Xpeng 等自动驾驶前瞻（含 robotaxi 投入）与国内企业前瞻一律保留。
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

### 3. 同一事件的多篇报道相邻

定时飞书发布脚本在每个品牌内跑下面这套聚类，再按 focus 把入华稿整段抬到该品牌前面。不要在文档里手调顺序。

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
5. 簇间先按簇内最高 focus 等级（入华、其他 Apple Intelligence、其余），再按簇内最高 `impact` 降序；簇内同样先看 focus，再按 `impact`。聚类用全部条目做一次，再按 focus 稳定分块，避免子集聚类改动其他品牌的顺序。

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

### 3. 事件去重加强（`prep_final.event_dedup`）

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

## 十四、2026-11-05 三补：供应链价格 ≠ 零售促销

补入 5 家国内芯片竞品（长鑫存储 CXMT、长江存储 YMTC、天数智芯 Iluvatar、壁仞科技 Biren、中际旭创 Innolight）时，
用合成标题做端到端验证，发现两条既有规则会**吞掉这几家最核心的情报**：

| 标题 | 原判定 | 问题 |
|---|---|---|
| `Memory chip price drop squeezes CXMT margins` | 剔（促销/折扣） | 存储价格战是 DRAM 厂商的核心情报 |
| `GPU price hikes boost Biren's outlook` | 剔（消费硬件价格/规格） | 该规则本意是挡消费级显卡涨价 |
| `Nvidia cuts GPU prices for China market` | 剔（消费硬件价格/规格） | 中国区定价是竞争动作 |

根因：`PROMO_PAT` 里的裸 `price (?:drop|cut|slashes?)` 与 `消费硬件价格/规格` 里的 `\bgpu\b.{0,25}(price|hike|shortage)`
都是按**零售促销**场景写的，没有区分「芯片/存储的批发价」和「整机的零售价」。

**修法**：`supply_price_intel(head)` 守卫，同时满足三条才豁免——
1. 出现价格变动（`price/pricing/cost` + drop/cut/hike/rise/surge/slump/decline/war，或 cut/drop/slash + prices）
2. 出现供应链主体（`dram|nand|hbm|wafer|foundry|capacity|asp|contract|memory|chip|semiconductor|gpu|accelerator|optical module` 等）
3. **不含消费电子整机**（`iphone|ipad|macbook|pixel|galaxy|airpods|apple watch|kindle|surface|console|ps5|xbox|buds` 等）

第 3 条是关键：没有它，`iPhone 17 price drop after chip shortage eases` 会因为提到 chip 而被放过。

同时修 IPO 首日：`SUBSTANTIVE_PAT` 补 `(?:trading|market|exchange)\s+debut`，
`CXMT shares jump 20% in trading debut` 不再被判为纯股价波动（上市首日是公司事件）；
`CXMT shares jump 20% on Tuesday` 这类日常涨跌仍会剔除。

回归：两批真实数据条数不变（11-05 批 129/120/120、11-04 批 199/191/191），确认没有噪音回流。

## 十五、2026-11-05 四补：新增 MarketWatch + 媒体名大小写

### 1. 新增媒体 MarketWatch（第 61 家，现共 63 家）

`marketwatch.com`（道琼斯旗下财经站）→ 英文 `MarketWatch` / 中文 `MarketWatch`（英文原名，同 Barron's、Benzinga 惯例）。
`SRC_TO_KB` 同时补四种可能写法：`MarketWatch Online`、`MarketWatch.com`、`MarketWatch.com Online`、`Dow Jones MarketWatch`。

**这批媒体偏股价/观点类**，用 20 条典型标题实测：保留 13、剔除 7。剔除的是大盘期货、荐股清单、
`What's going on with ... stock`、财报前瞻、特斯拉电动车股价、促销、`iPhone 涨价`转述。保留的是
芯片/存储报价、AI 战略、Robotaxi、并购、监管。

### 2. 媒体名大小写不敏感回退（`src_norm`）

导出会把同一家媒体写成不同大小写：`POLITICO` / `Politico`、`Tech in Asia` / `Tech In Asia`、
`marketwatch` / `MarketWatch`。原实现只做精确匹配，这些稿件被当作未知媒体**静默丢弃**。
11-04 批因此少了 3 条 Tech in Asia 稿（京东收购 Ceconomy、OpenAI 挖 Uber 高管、Nvidia 投资的 Cohere）。

修法：精确 → 剥 `Online` → `SRC_TO_KB` → **小写索引回退**。
前置检查：KB 内不存在「仅大小写不同」的重名，回退不会产生歧义。

### 3. 顺带修三处漏判

| 问题 | 原判定 | 修法 |
|---|---|---|
| `Amazon launches new AI model to rival OpenAI` | 剔（亚马逊非AI） | `AMAZON_KEEP` 补裸 `\bai\b`（原先只认 `artificial intelligence`） |
| `Dow Jones futures fall as Fed decision looms` | 留（漏） | 大盘规则补 `(?:dow|nasdaq|s&p)\s+(?:jones\s+)?futures` |
| `3 stocks to buy now and hold forever` | 留（漏） | 股评规则由 `stocks to watch` 扩为 `stocks to (watch|buy|own|hold|sell)` |

回归影响：11-05 批 120→121、11-04 批 191→195。新增全部可核实为真实稿件
（3 条 Tech in Asia + 1 条 Amazon 的 Anthropic AI 持仓），无噪音回流。

## 十六、2026-11-05 五补：客户重点关注 Apple Intelligence（入华优先）

客户第一优先关注 Apple Intelligence 的产品与政策动态，其中「入华」类关注度最高。实现分三层，
`focus` 字段写在 curation 和 prep_final 的条目上。定时飞书发布脚本读取它：`apple_intel_cn` 整段在该品牌最前，其次 `apple_intel`，其余仍按事件簇的最高影响力。入华稿按标题里最早出现的实体留下，而不是被国内品牌优先规则整条搬走。

### 1. 判定（`curation.apple_focus`，只看标题）

| 等级 | 权重 | 判定 | 例子 |
|---|---|---|---|
| `apple_intel_cn` | **+4** | Apple 的 AI 载体（Apple Intelligence / Siri / Apple AI）+ 中国要素（`China`、`mainland`、`国行`、`CAC`/`网信办`、阿里/百度/腾讯/Qwen 等合作方） | `Apple Intelligence launches in China with Alibaba's Qwen model`、`Apple taps Baidu to power Siri in China`、`Apple Intelligence 国行版上线` |
| `apple_intel` | **+2** | 其他 Apple Intelligence 动态：功能上线、Siri 改造、AI 代理风险、评测与使用技巧 | `Siri overhaul slips to 2027`、`Apple Intelligence review: useful but half-baked` |
| — | 0 | 不含 Apple 的 AI 载体 | `Apple's China sales fall 12%`、`Apple Q4 earnings beat` |

**关键排除：裸 `chinese` 不算入华。** `Apple Intelligence in Chinese language` 是全球语言支持，
不是中国市场落地 —— 因此 `APPLE_CN_PAT` 要求 `chinese market/users/regulators/government/authorities/iphone`。
（首版直接写了 `chinese`，把语言版稿误判成入华。）

评测与使用技巧类**按客户要求保留并加权**，不视为低价值噪音。

### 2. 排序

`pscore` 只影响 curation 在品牌内部的挑选顺序。`CAP` 为 `None`，所以加权不决定进不进报告。
飞书文档在品牌内先按事件簇排，再把 `apple_intel_cn`、`apple_intel` 整段抬到该品牌前面。核对时看文档里该品牌开头是不是入华稿，并对照 `final.json` 的 `focus` 字段。

### 3. 归属（`curation.unique_placement` + `prep_final` 重归位）

focus 稿**按标题中最早出现的实体**归位，不套用「国内企业优先」。
否则 `Apple Intelligence launches in China with Alibaba's Qwen model` 会被整条挪进「国内企业/阿里巴巴」，
Apple 板块看不到最关键的入华动态。

**两处都要改**：`prep_final` 第 1 步「归属唯一化」有一份自己的逻辑（领导人优先），
若不加同样的 focus 分支，会把 curation 已归到 Apple 的稿子重新挪回领导人板块
（实测 `Apple's Siri AI Could Become a Paid…CEO John Ternus` 被改回 John Ternus）。

### 4. 已知的连带影响

含 Apple AI 的跨品牌稿，会在其所属板块内也被提前，例如
`What Nvidia and Apple's Tug-of-War Says About the AI Trade`（Nvidia 板块）、
`AMD Earnings To Test Whether PC Weakness Is Intel-Specific, Apple's AI…`（Intel 板块）。
这是有意为之：只要讲 Apple Intelligence 就享受优先度。条数不变，仅位置变化。

## 十七、2026-11-06 批次：12 类新增噪音 + 两处结构性 bug

### 1. 新增 12 类剔除（均只看标题）

| 规则 | 剔除对象 | 触发写法 |
|---|---|---|
| 散户股价推算/择时 | 教人算收益、猜底、择时 | `if you invested $`、`cheaper than a toilet-paper company`、`options traders`、`what history suggests is the floor`、`buy X or Y?`、`look like bargains`、`Cathie Wood buys`、`^Opinion \|` |
| intel=情报 | 把「情报」当 Intel 公司 | `intel report`、`in intel`、`intel community` |
| 本地商家好评软文 | Google Reviews 实为本地商家 SEO | `google reviews recognize … home sellers` |
| 罪案/司法花边 | 与业务无关的个案 | `found guilty for threatening`、`murder-for-hire`、`catches thief`、`home invasion` |
| 致富教程/副业指南 | 变现教程 | `turn your … into a $100,000 business` |
| 娱乐/职业转型花边 | 网红转行 | `made the move from TikTok to TV` |
| 软件bug/更新日志 | 补丁与 changelog | `copy-paste bug`、`excel 2016`、`seasonal clock change` |
| 富豪榜/地产花边 | 身家排名 | `billionaire rankings`、`created 5 billionaires`、`drops to no. 9 in`、`billionaire magnet` |
| 通稿/SEO换皮 | 小站转载与上架贴 | `Xinhua Silk Road`、`AIVideoFree`、`integrates OpenAI … a day after` |
| 怀旧开箱/复古测评 | nostalgia 内容 | `back to unboxing`、`unboxing a GeForce` |
| 个人使用技巧 | 个人设备用法（**排除 AI**） | `how I use my …`、`how to use your …`，前置负向前瞻排除 `apple intelligence / siri / ai` |
| 社媒使用场景/公益 | 平台被使用而非平台经营 | `missionaries take to TikTok`、`church`、`charity drive` |
| 第一人称走访/见闻 | 现场随笔 | `^I went to`、`everyone talked about` |

### 2. 强政治判据（`STRONG_POLITICS_PAT`）

政治叙事此前靠 `POLITICS_PAT` + `BUSINESS_SIGNAL_PAT` 两级判断，但商业信号词太宽（含 `\bai\b`、`lawsuit`、股价代码），
于是「马斯克在中期选举惨败后回击民主党 AI 监管」凭一个 `AI` 就过关。现加一级**强政治**判据，命中即剔、
不受商业信号豁免：`midterm rout` / `persecut` / `governor-elect` / `spent at least $X million in` /
`lawyer up` / `\bdoge\b` / `loses billions`。

**刻意不含裸 `after the midterm`** —— 那会误伤「选举后特斯拉、SpaceX 股价为何下跌」这类市场影响稿，此前已确认保留。

### 3. 两处结构性 bug（都不是规则问题）

**a) 领导人实体吞掉品牌稿（严重）**

`aliases_of` 对非领导人实体按 `/` 和括号整体切分，于是 `Dara Khosrowshahi (Uber)`
产生别名 `uber`，**所有 Uber 标题都命中该领导人**。而 `unique_placement` 在位置并列时只按 `min(hits, key=位置)` 取，
顺序取决于 `set` 的遍历顺序 —— 同一批数据两次运行，Uber 的 9 条稿可能在 `Uber` 和 `Dara Khosrowshahi` 之间漂移。

修法：括号仅出现在领导人实体上（三个品牌表均无括号），故以括号为领导人标记，括号内公司名不作别名；
并列排序改为 `(位置, 品牌优先, 实体名)`。`curation.py` 与 `prep_final.py` 各有一份 `aliases_of`，两处同步。

**b) 媒体映射指向不存在的媒体**

给地方台补映射时写了 `'WABC-TV Online': 'ABC News'`，但 KB 没有 ABC News。原 `src_norm` 直接返回映射值、
不校验，于是「未知媒体」照样通过白名单闸门进报。现改为目标必须在 KB 内，否则返回 None，并在启动时打印
`WARNING: SRC_TO_KB 指向不存在的媒体`。

### 4. 本批结果

436 条原始 → 166 候选 → 147 条；首版（未加规则）为 182 条，其中约 35 条属上述噪音。

## 十八、2026-11-06 口径调整：领导人归入品牌 + 自动驾驶垂媒

### 1. 领导人归入所属品牌

飞书只印有条目的栏目，标题用「国内竞品 / 自动驾驶竞品 / 海外竞品」。能解析到品牌的领导人写入该品牌的 `section`，第四栏通常不出现。

实现：`filter3.leader_placement()` 把领导人实体解析成所属品牌 `(板块, 品牌)`。
- 实体名带括号的（`Sundar Pichai (Alphabet/Google)`）直接取括号内公司；`DeepMind`/`AWS` 这类非 canon 名
  经 `LEADER_PARENT_ALIAS` 归一。
- 实体名不带括号的国内领导人靠 `LEADER_PARENT` 显式指定（马云 → 阿里巴巴 …）。
- `埃隆·马斯克/Elon Musk` 无单一品牌（Tesla/SpaceX/X/xAI），保留为独立实体，仍在自动驾驶板块。
- 解析不到的领导人退回自身实体，**不丢条目**。

领导人匹配仍然承担「救回归属」的作用：标题只提人名（`Sundar Pichai says…`）时，靠领导人命中把稿件放到其品牌下。

### 2. 新增两家自动驾驶垂媒（媒体库 61 → 63）

| 英文 | 中文 | 域名 |
|---|---|---|
| InsideEVs | InsideEVs | insideevs.com |
| Electrek | Electrek | electrek.co |

`SRC_TO_KB` 兼容 `InsideEVs.com` / `Inside EVs` / `InsideEVs Online` / `Electrek.co` / `Electrek Online`。

> 注意：这两家以特斯拉与电动车产品为主，其 EV 类标题仍会被既有的「特斯拉非重点（EV/股价/销量）」规则剔除，
> 实际进报的主要是 robotaxi / 自动驾驶 / 车队合作类稿件。这是既有口径，不是新问题。

### 3. 媒体标准写法：`Tech in Asia`

KB 内原写法 `Tech In Asia` 统一为 **`Tech in Asia`**；`SRC_TO_KB` 保留旧写法映射，历史导出仍可识别。

### 4. 领导人补充（2026-11-06）

| 领导人 | 归属 | 说明 |
|---|---|---|
| Bill Gates | Microsoft | 原已在表内（`Bill Gates (Microsoft)`），解析路径正确 |
| **Eric Schmidt** | Alphabet/Google | **新增**。谷歌前 CEO/董事长；同时补入《翻译知识库》领导人表（埃里克·施密特） |

`Eric Schmidt` 只收全名 `eric schmidt`，**不收裸 `Schmidt`** —— 德语姓氏过于常见
（Helmut Schmidt、Schmidt hammer lassen 等），加裸姓会误收无关政治/建筑新闻。

### 5. 政治规则的第三次收紧：机构动作豁免（2026-11-06）

用户指出 `CNBC: Nvidia's Huang is asked to brief Congress on reported Chinese spy relationship` 未收录。
追查：标题含 `Congress` → 命中 `POLITICS_PAT`；`BUSINESS_SIGNAL_PAT` 无对应词（不含 chip/AI/lawsuit 等）
→ 判「纯政治评论」剔除。

**这是误剔。** 国会/议会针对本公司的实质动作（要求作证、简报、传唤、听证）是监管与地缘政治议题，
正是核心竞争情报。原规则的漏洞在于：`POLITICS_PAT` 里 `\bsenate\b|\bcongress\b` 与选举词混在一起，
而 `BUSINESS_SIGNAL_PAT` 只认产业词、不认「公司被监管机构传唤」这一事实。

**修法**：新增 `INSTITUTION_ACTION_PAT`

```
(asked|called on|urged|summoned|invited) to (brief|testify|appear)
(seek|seeks|seeking|requested) (a) briefing
(brief|briefing|testimony|testify) (congress|lawmakers|senate)
testify | subpoena* | congressional hearing | senate hearing | hearing before
appear(ed) before (congress|senate|lawmakers)
```

政治判断改为三条件：命中政治词 **且** 无商业信号 **且** **不是**（命中品牌 + 机构动作）→ 才判纯政治。
`exclusion_reason()` 因此新增 `has_brand` 参数（主循环传入品牌命中结果）。

**同时修 `campaign` 缺词边界**：裸 `campaign` 会匹配 `campaigners`（活动人士），
导致 `Google refused 54K-name petition, say campaigners` 被当成选举稿剔除。改为 `campaigns?\b`。

## 十九、2026-11-06 补充：中国相关科技议题一律收录

**客户口径**：这些品牌（三个板块全部 tracked 品牌）在**芯片、AI、自动驾驶、无人驾驶、Robotaxi、
中美科技监管**方面**与中国相关**的报道，必须收录。

### 判据（只看标题）

`filter3.china_tech_focus(head)` = 中国信号 **且** 科技议题信号：

| 类别 | 关键词（节选） |
|---|---|
| 中国信号 | `China / Chinese / Beijing / PRC / mainland / Hong Kong / Taiwan / Shanghai / Shenzhen / Hangzhou`、`CAC / 网信办 / 工信部 / 商务部`、`rare earth`、以及中国公司名本身（`Huawei / BYD / SMIC / YMTC / CXMT / Alibaba / Tencent / ByteDance / Xiaomi / Baidu / DeepSeek / Moonshot / Qwen / Zhipu / MiniMax / SenseTime / Innolight / MetaX / Moore Threads / Iluvatar`）|
| 科技议题 | `chip / semiconductor / foundry / HBM / DRAM / wafer / GPU`、`AI / LLM / model / agent`、`autonomous / self-driving / driverless / robotaxi / FSD`、`regulation / export control / entity list / antitrust / tariff / Congress / hearing` |

### 三道效果

1. **豁免各品牌话题门控**（`topic_gate`）。原口径下这些稿会被品牌门控误剔：
   - `Tesla's China sales of FSD cars climb as robotaxi pilot expands` → 命中 `TESLA_DROP`（sales）
   - `Amazon cuts China cloud prices to counter Alibaba's Qwen` → 命中「亚马逊非 AI」
   - `Uber Eats expands in China with robotaxi pilot` → 命中「Uber/Lyft 外卖」
2. **豁免「政治攻防」判据**（`STRONG_POLITICS_PAT`）。
   `Nvidia loses billions in China as export curbs bite` 会命中 `loses billions`，
   但它恰恰是中国市场最核心的情报。选举类叙事不受影响（不含中国科技信号）。
3. **加权 +2**（`curation.FOCUS_CN_TECH`）：加在 `pscore` 上，**不写入 `focus`**。
   `prep_final` 里同一规范化标题的分组会受这个分数影响。飞书和 Word 的品牌内展示仍只看
   Apple Intelligence 的 `focus` 和事件簇影响力，不会因为这 2 分把中国科技稿抬到品牌最前。
   单独的中国科技 `focus` 先不做，与当前外部包的代码一致。筛选说明里仍写「在该品牌下优先展示」，这句话沿用外部包原文。

> 两处正则 `filter3.CHINA_SIGNAL_PAT/CHINA_TECH_PAT` 与 `curation.CN_SIGNAL_PAT/CN_TECH_PAT` 是
> **故意重复**的：filter3 决定「收不收」，curation 决定「`pscore` 加不加 2」。改一处必须改另一处，
> 否则会出现「保留了却没加权」或「加权了却没保留」的静默不一致。

### 边界

- 加密货币仍按原口径剔除（即使带中国信号）。
- 无品牌归属的标题仍不进报（归属只看标题，这是既有铁律）。
- 纯中国宏观稿（`China's GDP slows`）不含 tracked 品牌 → 本来就不在归属范围内。
