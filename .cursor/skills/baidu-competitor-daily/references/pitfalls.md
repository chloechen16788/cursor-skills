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
| 8 | 中文错位 | final 由 66 变 61 后中文列表未对齐 | 只按 final 的 `idx` 填 `zh.json`（用 `make_zh_template.py`），并断言 `len(zh)==len(final)` |
| 9 | 翻译接口被拦截 | deep-translator 调用失败 | 改为模型逐条人工校对翻译，写入 `zh.json` |
| 10 | 媒体口径反转 | Benzinga / The Register 一度被剔除，后须在 KB 内 | 仅收录 KB 媒体后，二者因在 KB 内而被纳入（覆盖早期「非头部媒体」剔除） |

## 额外注意事项

- **同报道跨板块**：务必以「标题最早出现的品牌」定唯一归属，领导人命中人名优先归领导人板块；国内/自动驾驶板块标题仍命中本板块品牌则不迁移。
- **国内/自动驾驶为全面收录**：匹配允许正文命中，可能命中量大，属正常。
- **媒体中文名口径**：CNBC 等在 KB 为全称「美国消费者新闻与商业频道」，报告按 KB 显示；如需简称需改 KB 或 `MEDIA_CN` 逻辑。
- **数据覆盖偏差**：若某期国内/自动驾驶几乎无覆盖，多为数据本身特征，而非筛选问题，不必强行补录。
- **处理停在翻译**：顺序是 filter3 → curation → prep_final → make_zh_template → 按标题填 `zh.json`。产出 `final.json` 和 `zh.json` 后交给 cision-mentions 的 `publish_daily_report.py`。翻译仍需人工或模型校对。
