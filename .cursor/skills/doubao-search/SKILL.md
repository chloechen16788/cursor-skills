---
name: doubao-search
description: 调用豆包搜索 Custom 接口进行单次或并发检索（开启 QueryRewrite），并将结果导出为 Excel。用于用户提到豆包搜索、Query 改写、导出 xlsx、字段筛选、标题为空丢弃等场景。
disable-model-invocation: true
---

# 豆包搜索

## 用途

- 使用豆包搜索接口 `https://open.feedcoopapi.com/search_api/web_search`。
- 固定开启 `QueryControl.QueryRewrite=true`。
- 支持多 query 并发检索。
- 导出 Excel，只保留指定字段，并丢弃标题为空的记录。
- 输出 Excel 前按标题去重（去除首尾空格后进行去重）。
- 基于 query 中的时间段筛选 `PublishTime`，仅保留时间段内的数据（含起止日期）。

## 前置检查

1. 确认项目根目录存在 `.env`。
2. 确认 `.env` 内存在 `DOUBAO_API_KEY=...`。
3. 使用项目内脚本执行（见下文），不要改业务代码。

## 导出字段（中英文）

- 标题 (`Title`)
- 相关摘要 (`Summary`)
- 媒体/站点 (`SiteName`)
- 链接 (`Url`)
- 发布时间 (`PublishTime`)
- 正文 (`Content`)
- 权威度描述 (`AuthInfoDes`)
- 权威度等级 (`AuthInfoLevel`)

## 处理规则

- 请求参数固定：
  - `SearchType=web`
  - `Count=30`
  - `Filter.NeedContent=true`
  - `Filter.NeedUrl=true`
  - `QueryControl.QueryRewrite=true`
- 结果处理：
  - 仅使用 `Result.WebResults`
  - `Title` 为空的记录直接丢弃
  - 基于 query 中的时间段（如 `7.31-8.3`）筛选 `PublishTime`，仅保留区间内数据
  - 多 query 合并后按 `Title` 去重
  - 导出列仅保留上面的 8 个字段

## 执行命令

单 query：

```bash
python3 ~/.cursor/skills/doubao-search/scripts/doubao_search_export.py \
  --query "7.10-7.17 中国传感器领域有什么企业或机构发布新产品技术的新闻？"
```

并发多 query：

```bash
python3 ~/.cursor/skills/doubao-search/scripts/doubao_search_export.py \
  --query "query A" \
  --query "query B" \
  --query "query C" \
  --max-workers 3
```

输出：

- 生成 `Doc/doubao_search_export_时间戳.xlsx`
- 同目录生成 `Doc/doubao_search_export_时间戳.json`（原始响应汇总）
