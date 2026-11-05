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
| 11 | Cruise 人名误命中 | `cruise` 词边界正则会命中 Tom Cruise、cruise ship / cruise missile / Princess Cruise Line | Cruise 改用 `(?<![a-z] )cruise(?![a-z0-9])(?!\s+(?:ship|missile|control|line\|liner\|cruiser))`；已验证 GM Cruise / Cruise's robotaxi 正常命中 |
| 12 | 财报前瞻漏剔 | "everything you need to know ahead of earnings"、"earnings on deck"、"reports earnings tomorrow: what to expect" 未被初版前瞻正则命中 | 前瞻正则补充 `on deck`、收窄 "ahead of / to report" 必带 the\|its，并加 `ACTUAL_EARNINGS_PAT` 守护，避免误删实际业绩 |
| 13 | 亚马逊噪音外溢 | "OLED monitor price on Amazon"、Echo/Kindle 等消费硬件、外卖/物流 仍被当作亚马逊公司新闻收录 | Amazon 分支加入 电商/物流/零售/生鲜/外卖 + 消费硬件(Echo/Kindle/Alexa/Fire TV/Ring) 剔除，并以 芯片/云/AI/Agent/自动驾驶 作保留白名单 |
| 14 | 关键词图误挂品牌 | `Qualcomm…After Earnings`→Uber；`Yum China…Transcript`→美团；`Leidos…`→Intel；`CVG…`→Zoox；`X-Energy Analyst…`→小马智行；选举夜报道→Google | 归属改为**纯标题判定**（`placed()` 只匹配 title），摘要/关键词/正文全不参与、无回退。代价：标题不点名的稿件不入报（如 `Lipstick King` 不再归阿里） |
| 15 | 关键词污染门控 | Musk/SpaceX 股价稿、Yahoo 纯股价稿放行 | `topic_gate` 只用 `title + excerpt`（head-only），不读 keywords 与 content |
| 16 | 前瞻误判为实际业绩 | `Uber Q3 earnings preview` 存活（`results on Wednesday` 命中 ACTUAL） | `ACTUAL_EARNINGS_PAT` 删除 `results (?:on\|of)`，仅认 `results (?:beat\|missed\|topped\|came in)` |
| 17 | 摘要偶发 "AI" 放行 | Amazon 照相亭广告稿因摘要含 "AI" 过闸 | `AMAZON_KEEP` 去掉裸 `\bai\b`，改用实质信号（artificial intelligence / alexa ai / aws / cloud / chip / agent / autonomous / zoox …） |
| 18 | 同题重复 5 次 | CBS 本地台分发同一稿，URL 各异，URL 去重失效 | `prep_final.py` 增加全局「规范化标题」去重，保留 impact 最高一条 |
| 19 | Cruise 靠关键词误命中 | `2027 Chevy Bolt Review` 的 keywords 含 `"Cruise":12,"GM":5,"robotaxi":1`，被判为 GM Cruise | `cruise_hit()` 只读标题+摘要，AV 语境也只在标题+摘要内判断，keywords 完全排除 |
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
| 33 | 促销/影视/股价被摘要污染 | 摘要含 `premarket trading` 使 `Apple shares slide as higher memory costs` 被判「大盘行情」误剔；摘要含 `discount shopping platform` 使 Temu/京东商业模式稿误剔 | 新增 `TITLE_ONLY_RULES`：体裁类规则（股评/行情/促销/评测/估值/财经栏目）**只作用于标题** |
| 34 | 促销规则误伤实质稿 | 裸 `deal` 命中 "ADNOC OpenAI Deal"、裸 `sale` 命中 "sales meet estimates"、裸 `discount` 命中 "discount platform"、`goes on sale` 把新品开售当促销 | 只用特定写法：`best ... deals` / `on sale (now/for/at)` / `discount code` / `drops to $X`；并加 `SUBSTANTIVE_PAT`（memory/margin/pricing 等）守护股价稿 |
| 35 | Moonshot 大小写失效 | 别名加了大小写敏感正则，但 `match_in_text` 传入的是 `.lower()` 后的标题，`Moonshot AI raises…` 仍归不到公司 | `match_in_text` 改收**原始大小写**文本；归属与门控都传原始 `title`。另加小写通名 + 登月语境两道兜底 |
| 36 | 同事件被拆散 | 按大类分（memory/earnings/ai）时，同一事件的多家报道仍被拆开：手表音频 3 条分散在 ai 与 product 两处；「新CEO首份财报」1 条在 earnings、1 条在 leadership | `TOPIC_RULES` 改为**由细到粗**排序（ceo_debut→watch_audio→siri_dev→…→earnings→…→product 兜底），细粒度事件先命中。实测 Apple 46 条形成 7/19/3/2/2/2/2 的连续块 |
| 37 | 词集聚类效果差 | 试过 Jaccard + 稀有词做话题聚类，Apple 46 条聚成 44 簇（rise/rising、cost/costs 词形不同导致失配） | 改用议题标签（memory/earnings/ai…），稳定且分错不丢条目 |

| 38 | 纯政治评论大量涌入 | 中期选举批次中，马斯克 26 条里 19 条是选举 horse-race；`MUSK_DROP` 只匹配 星链/SpaceX/X/Grok，不含这些词故全部放行 | 新增 `POLITICS_PAT` + `BUSINESS_SIGNAL_PAT` 组合判据：政治词命中且无商业信号才剔 |
| 39 | 同事件换主语漏合 | 「Google 关闭学校搜索」10 版：Mamdani 指控 / Sanders 指控 / 课堂噩梦，只共享 `{accuses, school}`，`school` 频次高不算稀有 → 原判据漏合 | 新增判据「共享≥2 且≥1 稀有」+ **词形归一化**（centre→center、15bn→15billion、复数还原） |
| 40 | 实体词虚高相似度 | 把「太空数据中心」「1000亿无线通信」「进军印度」并成一簇，因 `Elon`/`Musk`/`wants` 计入共享词数 | `EV_STOP` 补充人名与高频虚动词（elon/musk/wants/set/back/make/need…） |
| 41 | 软文与生活类混入 | 律师事故广告、商会公告、`5 ChatGPT Prompts To Get Out Of Debt`、约会建议专栏、`17 better ways...`、`the "Uber of sales"` | 新增 6 类 EXCL：律所广告/商业软文/生活情感/个人理财/清单体/他业类比/人物访谈 |
| 42 | 股价问句变体逃逸 | `What Is Going On With Apple Stock`（Is 而非 What's）未被股价规则拦住 | `STOCK_MOVE_PAT` 改为 `what(?:'s| is| are)? going on with` |
| 43 | Big Apple 被当苹果公司 | `A Big Night for the Big Apple?` 讲纽约，被判入 Apple | 加规则：含 Big Apple 且无 iPhone/Siri/Cupertino 等科技信号 → 视为纽约 |

| 44 | 通用技术词被当稀有词 | `data`/`center` df 低被认作「稀有」，导致 `TeraWulf gets credit backstop for Anthropic data-center project` 被并进 `Google to invest $15bn in Malaysia's data center expansion`；`Anthropic tweaks Claude Code ... games` 被并进 `Cat Wu has left` | 新增 `EV_GENERIC` 通用技术/商业名词黑名单，这些词即使低频也不算有效稀有词；产品名（claude/chatgpt/gemini/siri…）加入 `EV_STOP` |
| 45 | 稀有度判据方向反了 | 真正的事件词（school/search）因被反复报道 df 高、不算稀有；通用词因只在一小簇出现 df 低、反被当稀有 | 判据改为「有效稀有词 = 低频 **且** 非常用名词」，并简化为三条：Jaccard≥0.5 / 有效稀有≥2 / 共享≥2且有效稀有≥1 |
| 46 | 手写事件标签无法适配每日数据 | 曾用 `school_ai`/`mna`/`buyout`/`watch_audio` 等标签做分组，全是照当期数据写的；换批数据后 Google 学校政策 11 条被 6 条无关稿隔开 | 删除全部手工词表，改为 `discover_events()` 从标题自动发现事件（词→标题集合，重合度≥0.5 合并） |
| 47 | 单链聚类会链式塌缩 | 改用自动发现后，旧批次 Apple 46 条被并成 45 条一巨簇（甲像乙、乙像丙，传递后全并） | 加护栏 `EVENT_CAP=0.55`：单簇标题数不得超过该实体总数的 55%。旧批次 Apple 恢复为 [21,10,7,3] |
| 48 | 平均链接虽安全但碎化 | 试过平均链接层次聚类（0.3–0.7）：不再塌缩，但 Uber 财报 13 篇被拆成 6+3+2+2，措辞差异大的大事件碎掉 | 放弃平均链接，回到单链 + 规模护栏——保住大事件，只偶有 1–2 条相邻稿被带入 |


## 额外注意事项

- **同报道跨板块**：务必以「标题最早出现的品牌」定唯一归属，领导人命中人名优先归领导人板块；国内/自动驾驶板块标题仍命中本板块品牌则不迁移。
- **国内/自动驾驶为全面收录**：不设条数上限。归属只看标题，不读正文。
- **媒体中文名口径**：CNBC 等在 KB 为全称「美国消费者新闻与商业频道」，报告按 KB 显示；如需简称需改 KB。
- **数据覆盖偏差**：若某期国内/自动驾驶几乎无覆盖，多为数据本身特征，而非筛选问题，不必强行补录。
- **事件级去重默认关闭**。定时命令不传 `--event-dedup`，不同媒体对同一事件的报道都保留。同一媒体的近题重复仍会去掉。
- **自动化沉淀**：定时运行走 filter3→curation→prep_final→按标题翻译→`publish_daily_report.py`（清空并重写飞书文档，再发日期和链接）。翻译步骤仍需人工/模型校对。不要把 Word 当作成品。
