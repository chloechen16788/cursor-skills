---
name: ant-test
description: >
  蚂蚁测试。只处理 Cision stream 1024448（Chloe test-the verge Stevie Bonifield）的单个记者取数和正文分析。
  触发说法包括「蚂蚁测试」「1024448」「Stevie Bonifield」「单个记者」「数据中心正文」。
  先按上海时间近一年只拉第 1 页；行数低于 4999 才导出。分析先写一句定位和数据概要（产出、标题选材），再从标题圈出数据中心稿，用 Firecrawl 抓正文，按正文写选材、写作手法、立场和内容。
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

分两段写。前一段只用已导出的 CSV。后一段才用裁剪后的正文。情感分和广告价值可以当对照，不能代替这两段。

### 简要说明

用一两句说明这个记者写什么、全年有多少篇、署名和语言和国家是否单一，以及数据中心占全年多少。数据中心占比低时，写成消费科技快讯记者，不是数据中心专线。占比用下面的标题命中重算。

### 数据概要

先写窗口：上海时间的起点（含）和终点（不含）。行数小于 4999 就写这一年是齐的。`keywords` 全部是 `{}` 时写明题材只看标题。

然后写产出和选材。数字每次从当次 CSV 重算。在仓库根目录执行，把 `CSV` 换成当次导出路径：

```bash
python3 - << 'PY'
import csv, re, statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

CSV = Path("CSV")
SH = timezone(timedelta(hours=8))
# 与取数相同的上海窗口：去年今天 00:00（含）到明天 00:00（不含）
today = datetime.now(SH).date()
try:
    start_day = today.replace(year=today.year - 1)
except ValueError:
    start_day = today.replace(year=today.year - 1, day=28)
window_start = datetime(start_day.year, start_day.month, start_day.day, tzinfo=SH)
window_end = datetime(today.year, today.month, today.day, tzinfo=SH) + timedelta(days=1)

rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig", newline="")))
titles = [re.sub(r"\s+", " ", row["title"]).strip() for row in rows]
n = len(titles)

def sh(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc).astimezone(SH)

def month_add(year, month, step):
    index = year * 12 + (month - 1) + step
    return index // 12, index % 12 + 1

moments = [sh(row["publishedAt"]) for row in rows]
counts = Counter(item.strftime("%Y-%m") for item in moments)
year, month = window_start.year, window_start.month
complete = []
while True:
    start = datetime(year, month, 1, tzinfo=SH)
    ny, nm = month_add(year, month, 1)
    end = datetime(ny, nm, 1, tzinfo=SH)
    if start >= window_end:
        break
    key = f"{year:04d}-{month:02d}"
    covered = start >= window_start and end <= window_end
    print(f"month={key} rows={counts[key]} complete={'yes' if covered else 'no'}")
    if covered:
        complete.append(counts[key])
    year, month = ny, nm

print(f"rows={n}")
print(f"unique_titles={len(set(titles))}")
print(f"window_start={window_start.strftime('%Y-%m-%d %H:%M')}")
print(f"window_end={window_end.strftime('%Y-%m-%d %H:%M')}")
print(f"published_first={min(moments).strftime('%Y-%m-%d %H:%M')}")
print(f"published_last={max(moments).strftime('%Y-%m-%d %H:%M')}")
if complete:
    mean = statistics.fmean(complete)
    print(f"complete_min={min(complete)} complete_max={max(complete)} complete_mean={int(mean + 0.5)}")
for column in ("author", "source", "languageCode", "locationCountry"):
    mode, count = Counter(row[column] for row in rows).most_common(1)[0]
    print(f"{column}={mode} share={count / n * 100:.1f}%")
print(f"keywords_empty={sum(1 for row in rows if row['keywords'].strip() == '{}')}/{n}")

stop = set("""
a an the of and or to in for on with from by at as is are was were be been
it its this that these those after over into about than then so not no but
if via per new says said will would can could may might their his her our
your they we you who what when where how which more most other out up down
off also just have has amid before during while
""".split())
freq = Counter()
for title in titles:
    for word in re.findall(r"[A-Za-z][A-Za-z0-9'’-]{2,}", title):
        token = word.lower()
        if token not in stop:
            freq[token] += 1
print("WORD_FREQ")
for word, count in freq.most_common(15):
    print(f"{count} {word}")

themes = [
    ("gemini", r"gemini"),
    ("android", r"android"),
    ("chatgpt_openai", r"chatgpt|openai"),
    ("claude", r"\bclaude\b"),
    ("linux", r"linux"),
    ("ai", r"\bai\b|artificial intelligence|openai|chatgpt|anthropic|gemini|llm"),
    ("data_center", r"data cent|data-cent"),
    ("ram_memory", r"\bram\b|\bmemory\b"),
    ("privacy_security", r"privacy|hack|breach|cyber|security|surveillance"),
]
print("TITLE_HITS")
for name, pattern in themes:
    count = sum(1 for title in titles if re.search(pattern, title, re.I))
    print(f"{name}={count} share={count / n * 100:.1f}%")
PY
```

标准输出只有计数。不要打印标题。

**产出。** 用脚本里的篇数、标题是否互不重复、作者列和来源列。完整月是窗口盖住整月的月份：该月 1 日 00:00 不早于窗口起点，下月 1 日 00:00 不晚于窗口终点。写出这些月的最少、最多，以及 `complete_mean`（中枢）。并列最高的月份点名。首月最早一篇晚于窗口起点时，写明从哪一天才开始，并给该月篇数。末月写出最后一篇的上海日期和钟点，并给该月篇数。

**选材。** 这里只看标题，分两种数。

- 词频是出现次数。切词用 `[A-Za-z][A-Za-z0-9'’-]{2,}`，转小写，去掉上面的停用词。同一标题里同一个词出现两次算两次。撇号留在词里，`Google's` 不计入 `google`。回复里点名机构名，跳过 now、app、reportedly、getting、next、year、data、users、first 这类词。
- 标题命中是一篇一次，题材之间可以重叠。给出篇数和占全年的百分比，保留一位小数。Gemini、Android、ChatGPT/OpenAI、Claude、Linux 用对应规则。AI 用 `ai` 那条。数据中心用 `data_center`。RAM/内存用 `ram_memory`，单独的 DRAM 不算，内存只是中文说法。隐私安全用 `privacy_security`。

用 2026-11-03 那次导出校验脚本时，词频是 Google 78、Apple 47、Amazon 25；标题命中是 Gemini 24、Android 22、ChatGPT/OpenAI 30、Claude 19、Linux 32、AI 181（21.1%）、数据中心 15（1.7%）、RAM/内存 22（2.6%）、隐私安全 31（3.6%）。完整月最少 43、最多 107、中枢 74。窗口变了就重算，不要把这组数写进新的回复。

### 内容分析

只根据裁剪后的数据中心正文。先说圈出几篇、抓到几篇、截断几篇，再写下面四项。

- **选材。** 这批评论实际写了哪些数据中心题目，材料来自公司公告、财报、民调还是其他媒体。给出篇数。
- **写作手法。** 篇幅、开头怎么下判断、引语从哪来、有没有转写和专题串联。
- **立场。** 作者把扩建、社区代价、公司效率声明和消费端价格放在什么关系里。不要把 Cision 的 ±0.1 情感桶当成立场。
- **内容。** 这些稿在一年里连成的情节。点明截断篇。

回复用简短中文。不要粘贴大段正文，不要打印密钥。

## 禁止

- 不要打印 `CISION_API_TOKEN`、`FIRECRAWL_API_KEY`。
- 不要提交 CSV、Firecrawl markdown 或正文摘录。
- 不要请求 `page_size=5000`，也不要在满 4999 行后再要第 2 页。
- 不要改 `cision-mentions` 的导出窗口、飞书群、wiki 或定时提示词。
