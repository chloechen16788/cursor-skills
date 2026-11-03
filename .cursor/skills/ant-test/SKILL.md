---
name: ant-test
description: >
  蚂蚁测试。只处理 Cision stream 1024448（Chloe test-the verge Stevie Bonifield）的单个记者取数和正文分析。
  触发说法包括「蚂蚁测试」「1024448」「Stevie Bonifield」「单个记者」「数据中心正文」。
  先按上海时间近一年只拉第 1 页；行数低于 4999 才导出。再从标题圈出数据中心稿，用 Firecrawl 抓正文，按正文写选材、写作手法、立场和内容。
  定时流水线、stream 1023128、飞书日报都不使用本技能。
---

# 蚂蚁测试：1024448 单个记者

给 OceanBase / 蚂蚁客户的媒体分析 demo 用。监测流固定是 `1024448`，名称是 `Chloe test-the verge Stevie Bonifield`。记者是 The Verge 的 Stevie Bonifield。

不要改 `cision-mentions`。上海 07:00 与 18:30 的自动化，以及提示词 `run the cision mentions skill`，仍然只走 `.cursor/skills/cision-mentions/SKILL.md`。本技能不推飞书，不写多维表格，不跑四栏目日报。

## 什么时候用

对方要拉 `1024448`、分析这一个记者，或按数据中心正文重做选材、写作手法、立场和内容。

## 什么时候不用

- 列出全部监测流：用 `cision-mentions` 的 `list_streams.py`。
- 导出 `1023128` 或别的 stream 的 07:00 窗口。
- 对方只要求改日报筛选、策展或译名：用 `baidu-daily-update`。

## 凭证

两个密钥都只从环境变量读。不要写进命令行、文件、日志或对话。

```bash
test -n "$CISION_API_TOKEN" && echo CISION_API_TOKEN=set || echo CISION_API_TOKEN=unset
test -n "$FIRECRAWL_API_KEY" && echo FIRECRAWL_API_KEY=set || echo FIRECRAWL_API_KEY=unset
firecrawl --version --auth-status
```

`CISION_API_TOKEN` 未设置就停止，不要向对方索取粘贴。`FIRECRAWL_API_KEY` 未设置或 `authenticated: false` 时，取数步骤仍可做；正文步骤停止，不要改用别的抓取器。

## 取数

不要跑 `export_mentions.py`。那个脚本的窗口是上海昨天 07:00 到今天 07:00，还会翻页并改写 `latest.csv`。

窗口按 Asia/Shanghai（UTC+8，无夏令时）的近一年：

- 终点：明天 00:00，不含该时刻
- 起点：去年同一天 00:00，含该时刻

再换成 UTC 传给接口。运行日是上海 2026-11-03 时：

- `filter[range][after]=2025-11-02T16:00:00.000Z`
- `filter[range][before]=2026-11-03T16:00:00.000Z`

只请求第 1 页。`pagination[page]=1`，`pagination[page_size]=4999`。`format=csv`。括号键由 `mentions_query` 百分号编码。请求头 `X-Auth-Token` 只用环境变量。复用 `.cursor/skills/cision-mentions/scripts/cision_lib.py` 的 `fetch_mentions_page`，不要另写一套 HTTP，也不要调用 `export_mentions`。在仓库根目录执行：

```bash
python3 - << 'PY'
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, ".cursor/skills/cision-mentions/scripts")
import cision_lib

today = datetime.now(cision_lib.SHANGHAI).date()
try:
    start_day = today.replace(year=today.year - 1)
except ValueError:
    start_day = today.replace(year=today.year - 1, day=28)
start = datetime(start_day.year, start_day.month, start_day.day, tzinfo=cision_lib.SHANGHAI)
end = datetime(today.year, today.month, today.day, tzinfo=cision_lib.SHANGHAI) + timedelta(days=1)
after = start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
before = end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

text = cision_lib.fetch_mentions_page("1024448", 1, cision_lib.MAX_PAGE_SIZE, after, before)
header, rows = cision_lib.parse_csv_page(text)
count = len(rows)
capped = count == cision_lib.MAX_PAGE_SIZE
print(f"rows={count}")
print(f"after={after}")
print(f"before={before}")
print(f"capped={'yes' if capped else 'no'}")
if capped:
    raise SystemExit(0)

stamp = f"{cision_lib.compact_stamp(after)}_{cision_lib.compact_stamp(before)}"
out = Path.home() / ".local/share/cision-mentions/runs/1024448" / f"{stamp}_page1.csv"
cision_lib.write_csv(out, header or ["id"], rows)
print(f"csv={out}")
PY
```

返回的数据行数等于 4999 时，这一年至少 4999，可能不全。脚本到此停止：不要请求第 2 页，不要把这一页写成全年导出，也不要进入正文分析。行数小于 4999 时，全年在这一页里，脚本写成 CSV。

文件名里的戳由 `compact_stamp` 生成，例如 `20251102T160000Z_20261103T160000Z_page1.csv`。输出放在仓库外：

`~/.local/share/cision-mentions/runs/1024448/{after戳}_{before戳}_page1.csv`

不要把 CSV 写进 git 工作区，也不要提交。

标准输出只给行数、窗口、是否顶满、文件路径。可以补充作者、来源、语言是否单一，以及 `publishedAt` 的最早和最晚。不要打印 mention 标题清单或正文。

## 圈数据中心

只在已导出的 CSV 里做。标题匹配 `data center` 或 `data centre`，忽略大小写和中间一个空格。`keywords` 列是空对象 `{}` 时不要用它筛选。

圈出的行保留 `publishedAt`、`title`、`url`、`sentiment`。回复里标题只在举例时出现，每个维度最多 3 条短标题。

## 抓正文

对圈出的 URL 调用 Firecrawl，只要主内容。一次可以传多个 URL，不要逐条另开对话。

```bash
mkdir -p ~/.local/share/cision-mentions/runs/1024448/datacenter-bodies
firecrawl scrape --only-main-content \
  -o ~/.local/share/cision-mentions/runs/1024448/datacenter-bodies \
  "<url>" "<url>"
```

产物放在仓库外。命令行工具若再套一层 `.firecrawl/`，留在该目录即可，不要移进 git 工作区：

`~/.local/share/cision-mentions/runs/1024448/datacenter-bodies/`

`--only-main-content` 仍会带上导航、相关稿和 cookie 文案。分析前先裁剪：从署名 `Stevie Bonifield` 之后开始，到 `Follow topics`、`Most Popular`、`Subscribe to The Verge to continue reading` 或评论区之前结束。出现订阅墙那句时，该篇记为截断，分析只使用墙前的正文，并在结果里点明哪几篇不完整。

抓取失败的 URL 留在名单里，正文为空，不要用标题冒充正文分析。

## 分析

只根据裁剪后的正文写下面四项。情感分、广告价值和标题词频可以当对照，不能代替正文判断。

- **选材。** 这批评论实际写了哪些数据中心题目，材料来自公司公告、财报、民调还是其他媒体。给出篇数。
- **写作手法。** 篇幅、开头怎么下判断、引语从哪来、有没有转写和专题串联。
- **立场。** 作者把扩建、社区代价、公司效率声明和消费端价格放在什么关系里。不要把 Cision 的 ±0.1 情感桶当成立场。
- **内容。** 这些稿在一年里连成的情节。点明截断篇。

回复用简短中文。先说圈出几篇、抓到几篇、截断几篇，再写四项。不要粘贴大段正文，不要打印密钥。

## 禁止

- 不要打印 `CISION_API_TOKEN`、`FIRECRAWL_API_KEY`。
- 不要提交 CSV、Firecrawl markdown 或正文摘录。
- 不要请求 `page_size=5000`，也不要在满 4999 行后再要第 2 页。
- 不要改 `cision-mentions` 的导出窗口、飞书群、wiki 或定时提示词。
