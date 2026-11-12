---
name: cision-mentions
description: 导出 Cision / Streem mentions。列出监测流的 id 与 label，或在已有 stream id 时按上海时间窗口拉取 CSV、与上次全量去重，并推送增量。周二到周日的窗口是昨天 06:30 至今天 06:30；周一是上周五 06:30 至周一 06:30。提示词 run the cision mentions skill，以及上海时间周一到周五 06:30 的定时运行，都在同一次运行里先导出 stream 1023128、去重并重写比较表；delta_rows 大于 0 时再抓取正文，保留原列并追加 content，写成 delta-bodies.xlsx 发到同一群，然后按 baidu-competitor-daily 筛选、策展、翻译成四栏目日报，只用另一套飞书应用清空并重写副本飞书文档，不写 prnewswire 主文档，再把上海数据日期、副本链接和 Word 文件发到同一群。delta_rows 等于 0 就停，不抓取，也不改文档。用户提到 Cision、Streem、mentions、监测流、舆情导出、飞书推送增量、正文或当日表时使用。
---

# Cision mentions 导出

## 用途

- 列出账号下的 Mention Stream，只打印 `id` 和 `label`。
- 已有 stream id 时，导出该流在固定时间窗内的 mentions CSV，并与上一份全量去重。
- 两条命令分开调用。导出 mentions 时不要先调用列表接口。
- 提示词是 `run the cision mentions skill` 时，以及上海时间周一到周五 06:30 的定时自动化，都在同一次运行里做完整条流水线。先导出 stream `1023128`。`delta_rows` 大于 0 再抓取正文、生成四栏目日报、只用另一套飞书应用清空并重写副本飞书文档，不写 prnewswire 主文档，然后把数据日期、副本链接和 Word 文件发到同一群。等于 0 就停在导出摘要，不抓取，不改文档，也不再发一条消息。不要在周六或周日跑这条流水线。

基址是 `https://api.cision.one`。认证用请求头 `X-Auth-Token`，值只从环境变量 `CISION_API_TOKEN` 读取。不要把 token 放到命令行参数里，不要打印它，也不要写进日志。

## 凭证

导出前确认环境里已有 `CISION_API_TOKEN`。不要在命令里回显这个变量。

```bash
test -n "$CISION_API_TOKEN" && echo CISION_API_TOKEN=set || echo CISION_API_TOKEN=unset
```

## 列出 streams

只请求 `GET /public/api/v2/streams?format=json`。不导出 mentions。

```bash
python3 .cursor/skills/cision-mentions/scripts/list_streams.py
```

每行一条：`id`、制表符、`label`。不要打印 keywords 或其他字段，也不要打印 mention 标题。

## 导出 mentions

用户已经给出 stream id 时，直接运行。不要先跑列表命令。

```bash
python3 .cursor/skills/cision-mentions/scripts/export_mentions.py --stream-id 1023128
```

请求 `GET /public/api/v2/mentions/{streamId}`，查询参数：

- `format=csv`
- `filter[range][after]`
- `filter[range][before]`
- `pagination[page]`
- `pagination[page_size]`

括号键会做百分号编码（`filter%5Brange%5D%5Bafter%5D` 这种形式）。`pagination[page_size]=5000` 会返回 HTTP 400，且响应体为空。`page * page_size >= 5000` 也一样。脚本拒绝 5000，默认每页 4999。只要下一页仍合法，就继续请求，直到某一页没有数据行。下一页会触达这个上限、而当前页又没满时，不再发那个必然 400 的请求。标准输出只给计数和文件路径，不打印 mention 标题或正文。

## 时间窗口

每次运行都用 Asia/Shanghai（UTC+8，无夏令时）的日历日，不另开参数改窗口：

- 周二到周日：起点是昨天 06:30，含该时刻。终点是今天 06:30，不含该时刻。
- 周一：起点是上周五 06:30，含该时刻。终点仍是周一 06:30，不含该时刻。周六日没有定时任务，这一窗补上周五 06:30 之后、整个周六和周日。

再把这两个时刻换成 UTC 传给接口。运行日是上海时间 2026-10-27（周二）时，无论上午还是下午，窗口都是 2026-10-26 06:30+08 到 2026-10-27 06:30+08，对应：

- `filter[range][after]=2026-10-25T22:30:00.000Z`
- `filter[range][before]=2026-10-26T22:30:00.000Z`

运行日是上海时间 2026-10-26（周一）时，窗口是 2026-10-23 06:30+08 到 2026-10-26 06:30+08，对应：

- `filter[range][after]=2026-10-22T22:30:00.000Z`
- `filter[range][before]=2026-10-25T22:30:00.000Z`

数据日期仍是窗口起点的日历日，所以周一的数据日期是上周五。去重仍用比较表里上一轮的 `id`。周五早上已经写入的稿不在这扇窗里，边界上重复的 id 会被去掉。不要在周六或周日手动跑 stream `1023128`，那一次会改写比较表。早于当天 06:30 的运行也按这个日历日计算，不会改成上一个窗口。

## 去重

同一次运行、同一个 stream id，顺序固定：

1. 把该窗口的全量 CSV 写到 `runs/{streamId}/{窗口}/full.csv`。
2. 从 `state/{streamId}/latest.csv` 读取上一份全量的 `id`。文件不存在时，增量就是本次全量。
3. 再写 `runs/{streamId}/{窗口}/delta.csv`，只保留 `id` 不在上一份全量里的行。空 id 的行留在增量里。
4. 用本次全量替换 `state/{streamId}/latest.csv`，下一次用它做比较。

其他 stream：要求推送飞书时，推送成功之后才替换 `latest.csv`。推送失败则保留原来的 `latest.csv`。未要求推送时，写出 delta 后立刻替换。

`1023128` 不读、不写 `latest.csv`。每次导出都按下一节同步多维表格，并用表里的 `id` 计算增量。

## 输出目录

默认目录在仓库外：

`~/.local/share/cision-mentions`

可用环境变量 `CISION_OUTPUT_DIR` 或参数 `--output-dir` 改位置。脚本发现目录落在 git 工作区里会直接退出。仓库 `.gitignore` 里另有 `cision-mentions-output/`，避免有人把输出指到这个名字下后又提交。不要提交这些 CSV。

除 stream `1023128` 外，稳定基线是：

`~/.local/share/cision-mentions/state/{streamId}/latest.csv`

`1023128` 不用这个文件。它的基线是下面那张飞书多维表格里的 `id` 列。

## 飞书推送

这是增量 CSV 的推送，实现在导出命令的 `--push-feishu` 上，不是第三条拉数命令。认证只读两个环境变量，代码里不写死，也不再读别的密钥：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

这两个名字已经作为 Runtime Secret 保存在本云环境。脚本只在当前进程看得到它们时才读取。若这次虚拟机是在保存密钥之前启动的，进程里会是未设置。这时列出 streams、以及导出除 `1023128` 以外的 stream 仍可进行；`1023128` 的多维表格同步不会执行，也不要向用户索要粘贴。Runtime Secret 在 cloud agent 启动时注入，不写进环境快照，所以不需要、也不要为了注入它们去重建环境。使用本环境新开的一次 cloud agent 运行可以读到这两个变量。

推送只发到写死的群 `oc_27040b0dc3a733ab164199154c489fad`（`receive_id_type=chat_id`）。没有环境变量，也没有命令行参数可以改到别的群或私聊。

```bash
python3 .cursor/skills/cision-mentions/scripts/export_mentions.py --stream-id 1023128
```

`1023128` 不需要 `--push-feishu`。同步写完表之后会把增量 CSV 推到上面那个群。其他 stream 仍要加 `--push-feishu` 才会推群，并且继续用本地 `latest.csv` 去重。

## 多维表格（仅 1023128）

标识写死，没有命令行参数或环境变量可以改到别的 wiki、表或群：

- wiki：`https://prnewswire.feishu.cn/wiki/ODp7wESdDiXrHjk7tEPcsQrSn6d`
- wiki node token：`ODp7wESdDiXrHjk7tEPcsQrSn6d`
- 多维表格 app token：`ByFgbm0xRaCBD2s8ohtcg0kgnWc`
- table id：`tblpvXJxxasNjP5e`
- 表名：`百度海外竞品最新数据`

这个 app token 就是 wiki 节点 `GET /open-apis/wiki/v2/spaces/get_node` 返回的 `obj_token`（`obj_type=bitable`）。当前两者相同，接口直接用这个 app token 和 table id。嵌入知识库的多维表格如果 app token 和 `obj_token` 不一致，必须用 `obj_token` 调 `/bitable/v1/apps/{token}`，否则会 404。表里原来的文本字段 `文本` 和占位行会保留字段、删掉占位记录。每个 CSV 列若还没有同名文本字段就新建，mention id 的字段名必须是 `id`。

每次导出 `1023128`，顺序固定：

1. 先读字段 `id` 的全部已有值。读取失败就停止，不删除任何记录。
2. 用这些 id 算增量。没有 `id` 字段，或表是空的，就视为没有上一份 id，增量等于本次全量。
3. 删掉表里的每一条记录。
4. 把本次窗口的全量写成记录，一行 mention 一条，不是只写增量。
5. 再把增量 CSV 推到群 `oc_27040b0dc3a733ab164199154c489fad`。

推送发生在写入之后。推送失败不会把表改回去，下一次增量会拿这次全量做比较。

应用还需要能读字段、建文本字段、读记录、删记录、建记录。把应用加为该多维表格的协作者。

飞书接口顺序：

1. `POST /open-apis/auth/v3/tenant_access_token/internal` 换 `tenant_access_token`。不打印这个 token。
2. `GET /open-apis/bitable/v1/apps/{app}/tables/{table}/fields` 和 `.../records`。失败则停止。
3. 缺列时 `POST .../fields`（`type=1` 文本）。表名不一致时 `PATCH .../tables/{table}`，请求体只有 `name`。不要用 `PUT`：同一路径会返回 HTTP 404，正文是 `404 page not found`，此时还没有删记录。这一步失败也不删除。
4. `POST .../records/batch_delete` 删掉全部记录。
5. `POST .../records/batch_create` 写入本次全量。
6. `POST /open-apis/im/v1/messages` 发一条只有行数的文本。增量有数据行时再 `POST /open-apis/im/v1/files` 上传 delta CSV，并用 `msg_type=file` 发出。

用户需要自己在飞书开放平台准备：

- 企业自建应用，把 App ID 和 App Secret 放进上面两个环境变量。
- 打开机器人能力并发布版本。
- 开通「以应用身份发消息」(`im:message:send_as_bot`) 和「获取与上传图片或文件资源」(`im:resource`)。
- 把机器人拉进群 `oc_27040b0dc3a733ab164199154c489fad`。推送不会发到其他会话。

本技能没有飞书群机器人 Webhook，也不读取除此之外的密钥。

## 正文文件（仅 1023128，紧接导出）

这一步和导出、日报在同一次运行里串行完成，不是第二条定时任务，也不是下一次对话。先跑导出。标准输出里的 `delta_rows` 为 0 时不要抓取，不要改日报文档，也不要再发一条飞书消息。大于 0 时，只用这一次写出的 `delta.csv`。抓完正文并推送 `delta-bodies.xlsx` 之后，立刻做下一节的四栏目日报。

```bash
python3 .cursor/skills/cision-mentions/scripts/extract_bodies.py --delta-csv <delta.csv> --after <after>
```

`--after` 用导出标准输出里的 `after`。不传时，从 `delta.csv` 的父目录名还原窗口起点。数据日期是这个起点在 Asia/Shanghai 的日历日。运行日 2026-10-27 的窗口起点是 2026-10-26 06:30+08，数据日期是 `2026-10-26`。运行日 2026-10-26（周一）的窗口起点是 2026-10-23 06:30+08，数据日期是 `2026-10-23`。

抓取在脚本里成批进行，调用 PATH 上的 `firecrawl scrape --only-main-content`。找不到命令时，和缺密钥一样，在发送文件之前停止。不要让 agent 每个 URL 单独开一轮。以后会有几百条 URL。密钥只从环境变量 `FIRECRAWL_API_KEY` 读取，不要写进命令行。

不做模型清洗。`标题` 就是增量 CSV 里的 `title` 列，脚本不改这一列，也不另写标题。新增列名是 `content`，不叫 `正文`。它保存 Firecrawl 返回的整段 markdown，不删导航、不改写、不摘要，避免后面再抽取时丢掉原文。原有列全部保留，不丢列。输出用 Excel（`delta-bodies.xlsx`），不用 CSV：markdown 里的换行和逗号会把 CSV 在飞书和 Excel 里拆列。xlsx 单元格上限是 32767 个字符。超限的格子截断到这个长度，标准输出列出数据行号、`id`、原长度和写入长度。同一 url 的重复行都保留，并填入同一段 markdown。抓取失败的行仍保留，`content` 为空。

写文件前如果没有 `FIRECRAWL_API_KEY`，立刻停止，不要发送文件。不要把密钥打进命令行。

不要把正文写进当日表，也不要删除记录或新建字段。当日表保持不动：

- wiki：`https://prnewswire.feishu.cn/wiki/E3ABwkrHKiC6U4kdbKMcRRtdnYc?table=tblRwSj33U1e4t4N&view=vew0Gce8xU`
- wiki node token：`E3ABwkrHKiC6U4kdbKMcRRtdnYc`
- table id：`tblRwSj33U1e4t4N`
- view id：`vew0Gce8xU`
- 该节点的 `obj_token` 是 `MbglbIcF6aKwyXsCW7QcSTbIncb`。正文步骤不调用它。

顺序固定：

1. 确认密钥和 `firecrawl` 命令。缺失则停止，不发送文件，也不访问当日表。
2. 按 url 去重后抓取。每一行增量都保留。`content` 保存整段 markdown。
3. 写成 `delta-bodies.xlsx`。原有列顺序不变，最后追加 `content`。
4. 只向群 `oc_27040b0dc3a733ab164199154c489fad` 发两样东西：一段短文本，以及这个文件。短文本只有数据日期、`delta_rows`、抓到的行数和失败行数。不发到别的会话，不发当日表链接，不改当日表。

比较用的「百度海外竞品最新数据」仍只由导出步骤整表重写。这一步不读、不删那张表，也不读、不删当日表。

## 四栏目日报（仅 1023128，紧接正文）

`delta_rows` 为 0 时不要进入这一节。大于 0 时，用刚刚写出的 `delta-bodies.xlsx`，在同一次运行里做完。筛选、策展、翻译和踩坑以本技能目录里的 `baidu-competitor-daily/` 为准，不要依赖仓库外的路径。先读 `baidu-competitor-daily/references/pitfalls.md`。

产物写到这次运行的目录里，不要提交：

```bash
python3 -m pip install openpyxl python-docx
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/filter3.py \
  --input <delta-bodies.xlsx> \
  --kb .cursor/skills/cision-mentions/baidu-competitor-daily/assets/翻译知识库.xlsx \
  --out <run>/candidates.json
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/curation.py \
  --candidates <run>/candidates.json \
  --raw <delta-bodies.xlsx> \
  --out <run>/curated.json
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/prep_final.py \
  --input <run>/curated.json \
  --out <run>/final.json
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/make_zh_template.py \
  --final <run>/final.json \
  --out <run>/zh_template.json
```

顺序和规则：

1. `filter3.py`：只留英文，且媒体必须在《翻译知识库》。剔除新闻稿。四个栏目按 国内企业、自动驾驶、海外企业、企业领导人。
2. `curation.py`：先按标题做唯一归属。不设每品牌限额，`CAP` 全是 `None`。不要在脚本跑完后再把一个品牌裁到 5 条或 8 条。
3. `prep_final.py`：再按标题定归属，并按 URL 去重。同一规范化标题归在一起，组内按 focus、pscore、impact 排。`idx` 是译文键。展示顺序由 `build_doc.py` 的 `discover_events` 决定：同事件相邻，Apple Intelligence 入华在该品牌最前。不要手写事件标签，也不要把 `pscore` 放进这一层的排序键。
4. 只根据标题填写 `zh.json`，不要读正文，也不要打印正文。媒体、品牌、领导人译名与知识库一一对应。`len(zh) == len(final)`。
5. 运行发布脚本。它只用 `FEISHU_COPY_APP_ID` 和 `FEISHU_COPY_APP_SECRET` 解析 wiki 节点 `DoXTwxbK1iX60yk282AcEN5Mn0e` 的真实 docx token，先清空文档正文，再按样例版式写入。不要写 `https://prnewswire.feishu.cn/wiki/PP88weeBdi1Pcgkmpxbc48lSn5e`。三个一级标题是「一、国内竞品（含领导人）」「二、自动驾驶竞品（含领导人）」「三、海外竞品（含领导人）」；没有条目的栏目不印标题。品牌是二级标题。英文行整行加粗，半角冒号，整行链到原文。中文行整行加粗，全角冒号，不带链接。每条新闻的中文行之后空一行，再写下一条。同事件的报道排在一起，Apple Intelligence 入华排在该品牌前面。同一条命令再用 `build_doc.py` 生成 Word，英文行是媒体、冒号、标题三段加粗链接。不要删除这个 wiki 节点，也不要改成别的文档，也不要再手改版式。筛选和排序的完整规则在 `baidu-competitor-daily/SKILL.md`，不要用旧的品牌限额覆盖它。

```bash
python3 .cursor/skills/cision-mentions/scripts/publish_daily_report.py \
  --final <run>/final.json \
  --zh <run>/zh.json \
  --after <after> \
  --raw-count <delta_rows>
```

`--after` 用导出标准输出里的 `after`。数据日期是这个起点在 Asia/Shanghai 的日历日。副本写完并核对子块数之后，脚本向群 `oc_27040b0dc3a733ab164199154c489fad` 发两条消息：一条是上海数据日期和 `https://jcn5bws14c2g.feishu.cn/wiki/DoXTwxbK1iX60yk282AcEN5Mn0e`，另一条是 `build_doc.py` 生成的 Word。不发到别的会话，文本里不附文章标题或正文。

日报只写入 `https://jcn5bws14c2g.feishu.cn/wiki/DoXTwxbK1iX60yk282AcEN5Mn0e`（节点 `DoXTwxbK1iX60yk282AcEN5Mn0e`）。这套应用只读 `FEISHU_COPY_APP_ID` 和 `FEISHU_COPY_APP_SECRET`，不用于群消息、比较表、正文文件或 Word。群消息和 Word 仍用原来的 `FEISHU_APP_ID` 与 `FEISHU_APP_SECRET`，链接只放副本。不要清空或重写 prnewswire 主文档。副本写入失败时不要发群消息，也不要改去写主文档。不要为此再跑一遍发布脚本。

## 定时运行

本技能不安装、也不注册调度器。能不能定时，分两处：

**Cursor 云端，已在文档里确认的部分。** [Automations](https://cursor.com/docs/cloud-agent/automations) 可以按预设或 cron 启动 cloud agent。用户必须自己创建并启用，地址是 [cursor.com/automations](https://cursor.com/automations)，也可以在 Agents 窗口里建。

现在只留一套定时自动化，上海时间周一到周五 06:30。cron 用 `30 22 * * 0-4`，也就是 UTC 周日到周四 22:30。不要写成 `1-5`，那会跳过周一早上，改成周六早上发。不要再加 18:30。一个自动化里放两条 cron 时，只会触发第一条。提示词是 `run the cision mentions skill`。这句话的意思是在同一次运行里按顺序做导出、正文、四栏目日报和文档链接，不要再拆成第二个定时任务，也不要等用户再说一次。

1. 触发器选 Scheduled，只用 `30 22 * * 0-4`。Automations 的 cron 按 UTC 计算。周二到周五的窗口是昨天 06:30（含）到今天 06:30（不含）。周一的窗口是上周五 06:30（含）到周一 06:30（不含）。不要改回每一天都只拉 24 小时，也不要在周六日触发。文档写明可以延迟触发，但不会早于设定时间开始。
2. 选中本仓库。cron 类触发器默认可以不带仓库；不带仓库时 agent 拿不到这份脚本。
3. 看到 `run the cision mentions skill`，或这套定时自动化被触发时，同一次运行里只做这些事。先运行 `export_mentions.py --stream-id 1023128`。它会按表里的 `id` 去重，清空并重写比较用的多维表格，并在 `delta_rows` 大于 0 时把只有原始列的 `delta.csv` 推到群。看标准输出的 `delta_rows`。等于 0 就停在这条导出摘要，不要抓正文，不要跑 `baidu-competitor-daily`，不要清空或重写日报文档，不要发第二条消息。大于 0 时，立刻用同一次输出的 `delta_csv` 和 `after` 运行 `extract_bodies.py`，写成 `delta-bodies.xlsx` 并推送。然后按上一节跑筛选、策展、翻译，再运行 `publish_daily_report.py`：只用副本应用清空并重写 `https://jcn5bws14c2g.feishu.cn/wiki/DoXTwxbK1iX60yk282AcEN5Mn0e`，不写 prnewswire 主文档，然后把上海数据日期、副本链接和 Word 文件发到同一群。不要逐条 URL 另开对话。不要打印 token、密钥或 mention 正文。不要再传 chat id、wiki 或 table id。不要把正文写入当日表。Word 只由这个发布脚本生成并发送，不要另存一份再发到别的会话。其他 stream 需要推群时才给导出命令加 `--push-feishu`，并且不要跑正文脚本，也不要跑日报。
4. 确认启动时能读到 `CISION_API_TOKEN`。`FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 已经是本环境的 Runtime Secret。日报文档还要 `FEISHU_COPY_APP_ID` 和 `FEISHU_COPY_APP_SECRET`，只给副本 wiki 用。正文步骤还要 `FIRECRAWL_API_KEY`。缺抓取密钥时，脚本在发送正文文件之前停止，也不改当日表。缺副本凭证时不要改文档，也不要发日报群消息，不要改去写主文档。新的 cloud agent 在启动时会注入已保存的 Runtime Secret，不要为它们重建环境。[Secrets 文档](https://cursor.com/docs/cloud-agent/security-network) 写明 Runtime Secret 会作为环境变量注入，同时在对话、工具输出和提交里打码。[构建文档](https://cursor.com/docs/cloud-agent/builds) 写明用户密钥在 agent 启动时加入，不进入构建快照。只核对变量名是否注入，不要打印值。

**文档没有保证、因此这里不当作已支持能力的部分。**

- 同一次论坛线索提到，带有 “Skip Install” 的旧自动化可能拿不到环境变量。创建后只核对注入的变量名，不要打印值。
- 云端每次定时都会新开一次 cloud agent。环境快照不保留 `latest.csv`。`1023128` 的去重基线在飞书多维表格里，两次云端运行可以对着同一张表。其他 stream 仍靠本机 `latest.csv`；云端没有这份文件时，增量等于当次全量。Memories 不是 CSV 基线，本技能也不会把 mention 内容写进去。
- Automations 自带 Slack 等工具，没有飞书推送工具。飞书只能走本脚本。群、比较表和 Word 用 `FEISHU_APP_ID` 与 `FEISHU_APP_SECRET`。日报文档只用 `FEISHU_COPY_APP_ID` 与 `FEISHU_COPY_APP_SECRET`。
- 本仓库不提供笔记本 crontab。同一台磁盘不重置的机器上，用户可以自行用系统 cron 调用导出命令，那样 `latest.csv` 才能留给下一次。

## 禁止事项

- 不要把 `CISION_API_TOKEN`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_COPY_APP_ID`、`FEISHU_COPY_APP_SECRET`、`FIRECRAWL_API_KEY` 或 tenant access token 打进命令行、日志、提交或对话。
- 不要提交 `full.csv`、`delta.csv`、`latest.csv` 或任何 mention 导出。
- 汇报结果时只给行数、窗口和路径，不粘贴 mention 标题或正文。
- 正文 xlsx 只发到 `oc_27040b0dc3a733ab164199154c489fad`，不要发到其他会话，也不要写入当日表。
- 日报链接和 Word 也只发到这个群。文本里要有上海数据日期和 `https://jcn5bws14c2g.feishu.cn/wiki/DoXTwxbK1iX60yk282AcEN5Mn0e`，不要附文章正文，也不要放 prnewswire 主文档链接。
- 不要删除日报 wiki 节点。只清空并重写 `DoXTwxbK1iX60yk282AcEN5Mn0e` 的文档正文，不要删节点，也不要改成别的文档。不要清空或重写 `https://prnewswire.feishu.cn/wiki/PP88weeBdi1Pcgkmpxbc48lSn5e`。
- 不要逐条 URL 让 agent 循环。抓取在 `extract_bodies.py` 里完成。
