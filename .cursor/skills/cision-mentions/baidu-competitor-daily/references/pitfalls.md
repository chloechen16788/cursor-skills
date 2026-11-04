# 踩坑记录与修复（百度竞品同业日报）

以下是历次制作中实际踩过的坑与对应修复。新一期运行前对照检查，避免重复犯错。

| # | 问题 | 现象 | 修复方式 |
|---|------|------|----------|
| 1 | 品牌误判 | Microsoft 财报文被误标为 Apple / Nvidia | 改用「标题 + 关键词 count≥2」综合判定，不再单看正文 |
| 2 | Meta 误匹配 | Meta-Optics / metaEye 被当成 Meta | 品牌别名加边界正则 `(?<![a-z0-9])meta(?![a-z0-9A-Z\-])` |
| 3 | 亚马逊雨林误判 | "warrior of the Amazon" 被当巴西/亚马逊公司 | 加「亚马逊雨林/河流」排除规则（`rainforest\|amazon river/forest/basin`） |
| 4 | PR 漏剔（空格） | `GLOBE NEWSWIRE` 中间有空格未命中 | 正则改为 `globe ?newswire`（容错空格） |
| 5 | PR 漏剔（独立字样） | Yahoo "paid press release" 未命中 | 补 `press ?release` 独立字样（扫描 标题/作者/摘要） |
| 6 | 人名双键冲突 | 吴泳铭 `Eddie Wu` / `Yongen Wu` 并存 | 标准英文名取 `Eddie Wu`，`Yongen Wu` 仅作别名变体 |
| 7 | 限额失效 | Anthropic 本应封顶 5 条却到 12 条 | **「按标题定唯一归属」必须在 curation 限额之前完成**（见 filter3 已并入 curation 早期） |
| 8 | 中文错位 | final 由 66 变 61 后 ZH 列表未对齐 | `zh.json` 按 `idx` 对齐，并断言 `len(ZH)==len(final)`。飞书发布脚本按 `idx` 读取 |
| 9 | 翻译接口被拦截 | deep-translator 调用失败 | 改为模型逐条人工校对翻译，写入 `zh.json` |
| 10 | 媒体口径反转 | Benzinga / The Register 一度被剔除，后须在 KB 内 | 仅收录 KB 媒体后，二者因在 KB 内而被纳入（覆盖早期「非头部媒体」剔除） |
| 11 | Cruise 人名误命中 | `cruise` 词边界正则会命中 Tom Cruise、cruise ship / cruise missile / Princess Cruise Line | Cruise 不进 `AUTO_BRANDS`，改由 `cruise_hit(title)`：标题含 cruise，且同一标题有 AV 语境（gm / robotaxi / self-driving / autonomous / driverless / waymo），且没有旅游或影讯信号。关键词不参与 |
| 12 | 财报前瞻漏剔 | "everything you need to know ahead of earnings"、"earnings on deck"、"reports earnings tomorrow: what to expect" 未被初版前瞻正则命中 | 前瞻正则补充 `on deck`、收窄 "ahead of / to report" 必带 the\|its，并加 `ACTUAL_EARNINGS_PAT` 守护，避免误删实际业绩 |
| 13 | 亚马逊噪音外溢 | "OLED monitor price on Amazon"、Echo/Kindle 等消费硬件、外卖/物流 仍被当作亚马逊公司新闻收录 | 亚马逊稿只在标题命中芯片/云/AI/Agent/自动驾驶等实质信号时保留。裸 `deal` 不算保留词，否则 “Kindle deal” 会留下 |
| 14 | 关键词图误挂品牌 | `Qualcomm…After Earnings`→Uber；`Yum China…Transcript`→美团；`Leidos…`→Intel；`CVG…`→Zoox；`X-Energy Analyst…`→小马智行；选举夜报道→Google | 归属改为**纯标题判定**（`placed()` 只匹配 title），摘要/关键词/正文全不参与、无回退。代价：标题不点名的稿件不入报（如 `Lipstick King` 不再归阿里） |
| 15 | 关键词污染门控 | Musk/SpaceX 股价稿、Yahoo 纯股价稿放行 | 先收成标题+摘要。现行口径见第 21 条：`topic_gate` 只读标题 |
| 16 | 前瞻误判为实际业绩 | `Uber Q3 earnings preview` 存活（`results on Wednesday` 命中 ACTUAL） | `ACTUAL_EARNINGS_PAT` 删除 `results (?:on\|of)`，仅认 `results (?:beat\|missed\|topped\|came in)` |
| 17 | 摘要偶发 "AI" 放行 | Amazon 照相亭广告稿因摘要含 "AI" 过闸 | `AMAZON_KEEP` 去掉裸 `\bai\b`，改用实质信号（artificial intelligence / alexa ai / aws / cloud / chip / agent / autonomous / zoox …） |
| 18 | 同题重复 5 次 | CBS 本地台分发同一稿，URL 各异，URL 去重失效 | `prep_final.py` 增加全局「规范化标题」去重，保留 impact 最高一条 |
| 19 | Cruise 靠关键词误命中 | `2027 Chevy Bolt Review` 的 keywords 含 `"Cruise":12,"GM":5,"robotaxi":1`，被判为 GM Cruise | `cruise_hit()` 只读标题。关键词里的 Cruise / GM / robotaxi 频次不参与 |
| 20 | 同事件改题重发 | Bloomberg 的 Apple 行情综述 3 条、WSJ 的 Talarico/Musk 2 条，标题字面不同但同源同事件 | `prep_final.py` 增加近似标题去重：同板块+同实体+同媒体，词集 Jaccard ≥ 0.5 只留 impact 最高一条 |
| 21 | 摘要/关键词污染门控 | Musk-SpaceX 稿、Yahoo 股价稿因 keywords 含 ai/earnings 被放行 | `topic_gate` 的 `head` 改为 `title` 单字段，与归属同口径 |
| 22 | 生活杂讯占据自动驾驶板块 | "ambulance driver takes Uber home"、"Did you know you can use Lyft in Europe?"、"Options Action: Traders pump brakes on Uber" 进报 | 新增 EXCL「生活/消费杂讯」；另加「系统使用技巧」「纯估值倍数评论」两类低价值剔除 |
| 23 | 品牌限额挤掉重点稿 | `CAP={'海外企业':5}` 使 Apple 96 条候选只进 5 条；Siri AI、Anthropic IPO、Nvidia 中国业务等 10 条重点稿被挤出 | 取消限额（`CAP` 全置 `None`），收录量交给剔除规则决定；同时用事件级去重控制篇幅 |
| 24 | 同事件跨媒体刷屏 | 「Google 关闭学校搜索」12 个版本、「OpenAI 聘前陆军部长」7 个版本各占一行 | `prep_final.py` 增加事件级去重：同实体+同板块内，Jaccard≥0.5 或共享≥2 个稀有实词即合并，`--per-event` 默认 1 |
| 25 | 水果苹果误入 Apple 桶 | `José Pizarro's recipe for mussels with cider, chorizo and apple` 排到 Apple 桶第 2 | 加 `APPLE_FOOD_PAT`（菜谱/果园/果汁）与 `APPLE_TECH_PAT`（iphone/siri/tim cook）对照判定 |
| 26 | 前瞻一刀切误伤自动驾驶 | Uber Q3 前瞻（含 robotaxi 投入）被当海外竞品前瞻剔除 | 前瞻剔除改为仅对「纯海外竞品」生效（有 ovb 且无 auto/dom 命中） |
| 27 | 拿 pscore 当噪音判据 | 若按 `pscore>=1` 过滤，会误删 OpenAI 任命前陆军部长、好莱坞诉 OpenAI 版权、Anthropic 5.67 亿亏损、Meta 发债等高价值稿 | 只按议题类别剔除，不按评分阈值；`pscore` 仅用于排序 |
| 28 | 媒体白名单挡住重要稿 | Waymo 洛杉矶扩张稿（LA Times）因媒体不在 KB 被整条丢弃 | 媒体库补 `Los Angeles Times / 洛杉矶时报`；日后遇到同类先查 KB 而非改规则 |

| 29 | 产品名被单列成实体 | 报告中出现「ChatGPT/GPT/Claude」独立小节，同一家 AI 公司被拆成两处；Anthropic 的 Claude 稿跑到别的小节 | 产品名一律归公司：ChatGPT/GPT→OpenAI，Claude→Anthropic，Kimi→月之暗面/Moonshot，Gemini→Alphabet/Google；删除独立实体，只加别名 |
| 30 | 白名单媒体被国家闸静默丢弃 | 新加坡《海峡时报》、加拿大 BNN 彭博、澳洲《澳大利亚人报》明明在媒体库内，稿件却全被「重点市场」挡掉；用户以为已加白名单实则没生效 | 媒体解析提到国家判断之前：**只要媒体在库就不受国家限制**。加媒体后必须回归验证「是否真的进报」 |
| 31 | 本地台来源名对不上 | `KNTV-TV Online`（= nbcbayarea.com）无法靠剥 ` Online` 匹配到 `NBC Bay Area` | `SRC_TO_KB` 加显式映射：BNN Bloomberg Online→BNN Bloomberg、KNTV-TV Online→NBC Bay Area、KPYX/KOVR→CBS |
| 32 | 标题粘连损坏 | 南华早报一条标题把 4 条不同新闻拼成一串（>300 字符），无法翻译也无法归位 | `is_broken_title()`：长度 >220 或首 20/30/40 字符重复出现即剔除 |

## 额外注意事项

- **同报道跨板块**：务必以「标题最早出现的品牌」定唯一归属，领导人命中人名优先归领导人板块；国内/自动驾驶板块标题仍命中本板块品牌则不迁移。
- **国内/自动驾驶为全面收录**：不设条数上限。归属只看标题，不读正文。
- **媒体中文名口径**：CNBC 等在 KB 为全称「美国消费者新闻与商业频道」，报告按 KB 显示；如需简称需改 KB。
- **数据覆盖偏差**：若某期国内/自动驾驶几乎无覆盖，多为数据本身特征，而非筛选问题，不必强行补录。
- **自动化沉淀**：定时运行走 filter3→curation→prep_final→按标题翻译→`publish_daily_report.py`（清空并重写飞书文档，再发日期和链接）。翻译步骤仍需人工/模型校对。不要把 Word 当作成品。
