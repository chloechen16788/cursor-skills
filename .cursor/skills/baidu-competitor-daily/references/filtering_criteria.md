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
| 一 | 国内企业（含领导人） | 合并板块 | 50 |
| 二 | 自动驾驶（含领导人） | 合并板块 | 50 |
| 三 | 海外竞品企业 | 按品牌拆分 | 每品牌 5 |
| 四 | 海外竞品领导人 | 按人名拆分 | 每品牌 8 |

- 海外板块：品牌 → 海外企业；领导人 → 企业领导人。
- 国内 / 自动驾驶为「全面收录」板块：除标题/摘要/关键词外，**额外允许正文命中**品牌别名。
- 同一篇报道**只归入一个板块 / 一个品牌**：按标题中最早出现的品牌名定唯一归属。

## 三、重点市场（白名单）

仅保留：`United States of America`、`United Kingdom`、`China`、`United Arab Emirates`（中东）。
其余（法/意/德/日/新加坡等）一律剔除。
归一化：`Taiwan → China`、`England → United Kingdom`。

## 四、媒体口径（仅收录 KB 媒体）

- 仅收录《翻译知识库》「媒体名称知识库」所列媒体。
- 来源名做归一化：`* Online` 后缀去除；`Bloomberg News Online→Bloomberg`、`Associated Press Online→The Associated Press`、
  `Wired Online→WIRED`、`Aljazeera International→AI Jazeera` 等（见 `filter3.py` 的 `SRC_TO_KB`）。
- 语言：仅收录 `languageCode == 'en'`（英文稿件）。

## 五、剔除规则

**新闻稿 / Press Release（必剔）：** 标题/作者/摘要中出现以下电头即剔除 ——
`prnewswire`、`globe newswire`（注意中间空格）、`einpresswire`、`business wire`、`news direct`、`marketwire`、
`accesswire`、`prweb`、`issuewire`、`send2press`、`newsfile`、`cision`、`press release`。
重点甄别 Benzinga 与美联社(AP)分发的通稿。

**主题剔除：** Windows/安卓补丁、手机/电脑等消费硬件、医学/医药、智能音箱、纯电商物流、
市场报告/通稿噪音、分析师评级/股市噪音、律所集体诉讼招揽、亚马逊雨林（非公司）、Meta-Optics/metaEye（非 Meta）。

**低价值：** 苹果手机/硬件配件（防盗支架等）、低价值股市噪音（ETF 调仓、个股波动快讯）等。

## 六、条目格式（两行式）

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

- 国内企业：阿里巴巴/通义千问/Qwen、字节跳动/抖音/豆包/火山引擎、腾讯/微信/混元、百度竞品侧（华为/深度求索/智谱/月之暗面/Kimi/百川/零一万物/Manus/商汤/小米/美团/京东/拼多多/Temu 等）
- 自动驾驶：Waymo、Cruise、Zoox、Wayve、Uber、文远知行、小马智行、小鹏、滴滴、Lyft、Cybercab
- 海外企业：Alphabet/Google、Microsoft、Meta、Apple、Amazon、Nvidia、IBM、Intel、OpenAI、Anthropic、Mistral、Perplexity、ChatGPT/GPT/Claude
- 领导人：Sundar Pichai、Satya Nadella、Sam Altman、Dario Amodei、Mark Zuckerberg、Jensen Huang、Tim Cook、Andy Jassy、Jeff Bezos、Elon Musk 等（含对应的国内/自动驾驶领导人）

> 特别注意 Meta 匹配正则 `(?<![a-z0-9])meta(?![a-z0-9A-Z\-])`，避免误命中 Meta-Optics / metaEye。
> 吴泳铭标准英文名取 `Eddie Wu`，`Yongen Wu` 仅作变体别名。

本文件只约束筛选和标题口径。处理停在 `final.json` 与按标题填好的 `zh.json`，交给 cision-mentions 的 `publish_daily_report.py`。
