---
name: cision-mentions
description: 导出 Cision / Streem mentions。列出监测流的 id 与 label，或在已有 stream id 时按上海时间昨天 07:00 至今天 07:00 拉取 CSV、与上次全量去重，并推送增量。stream 1017610 在同一次运行里、增量非空时，接着用 Firecrawl 抓取正文，标题用 CSV，正文保存整段 markdown，追加到 CSV 后只把文件发到固定群。用户提到 Cision、Streem、mentions、监测流、舆情导出、飞书推送增量、正文或当日表时使用。
---

# Cision mentions 导出

## 用途

- 列出账号下的 Mention Stream，只打印 `id` 和 `label`。
- 已有 stream id 时，导出该流在固定时间窗内的 mentions CSV，并与上一份全量去重。
- 两条命令分开调用。导出 mentions 时不要先调用列表接口。
- stream `1017610` 的同一次运行里，导出完成且 `delta_rows` 大于 0 之后，再抓取正文，把带正文的 CSV 发到固定群。增量为 0 则停，不抓取，也不再发一条消息。

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
python3 .cursor/skills/cision-mentions/scripts/export_mentions.py --stream-id 1017610
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

- 起点：昨天 07:00，含该时刻
- 终点：今天 07:00，不含该时刻

再把这两个时刻换成 UTC 传给接口。运行日是上海时间 2026-10-26 时，无论上午还是下午，窗口都是 2026-10-25 07:00+08 到 2026-10-26 07:00+08，对应：

- `filter[range][after]=2026-10-24T23:00:00.000Z`
- `filter[range][before]=2026-10-25T23:00:00.000Z`

早于当天 07:00 的运行也按这个日历日计算，不会改成上一个窗口。

## 去重

同一次运行、同一个 stream id，顺序固定：

1. 把该窗口的全量 CSV 写到 `runs/{streamId}/{窗口}/full.csv`。
2. 从 `state/{streamId}/latest.csv` 读取上一份全量的 `id`。文件不存在时，增量就是本次全量。
3. 再写 `runs/{streamId}/{窗口}/delta.csv`，只保留 `id` 不在上一份全量里的行。空 id 的行留在增量里。
4. 用本次全量替换 `state/{streamId}/latest.csv`，下一次用它做比较。

其他 stream：要求推送飞书时，推送成功之后才替换 `latest.csv`。推送失败则保留原来的 `latest.csv`。未要求推送时，写出 delta 后立刻替换。

`1017610` 不读、不写 `latest.csv`。每次导出都按下一节同步多维表格，并用表里的 `id` 计算增量。

## 输出目录

默认目录在仓库外：

`~/.local/share/cision-mentions`

可用环境变量 `CISION_OUTPUT_DIR` 或参数 `--output-dir` 改位置。脚本发现目录落在 git 工作区里会直接退出。仓库 `.gitignore` 里另有 `cision-mentions-output/`，避免有人把输出指到这个名字下后又提交。不要提交这些 CSV。

除 stream `1017610` 外，稳定基线是：

`~/.local/share/cision-mentions/state/{streamId}/latest.csv`

`1017610` 不用这个文件。它的基线是下面那张飞书多维表格里的 `id` 列。

## 飞书推送

这是增量 CSV 的推送，实现在导出命令的 `--push-feishu` 上，不是第三条拉数命令。认证只读两个环境变量，代码里不写死，也不再读别的密钥：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

这两个名字已经作为 Runtime Secret 保存在本云环境。脚本只在当前进程看得到它们时才读取。若这次虚拟机是在保存密钥之前启动的，进程里会是未设置。这时列出 streams、以及导出除 `1017610` 以外的 stream 仍可进行；`1017610` 的多维表格同步不会执行，也不要向用户索要粘贴。Runtime Secret 在 cloud agent 启动时注入，不写进环境快照，所以不需要、也不要为了注入它们去重建环境。使用本环境新开的一次 cloud agent 运行可以读到这两个变量。

推送只发到写死的群 `oc_27040b0dc3a733ab164199154c489fad`（`receive_id_type=chat_id`）。没有环境变量，也没有命令行参数可以改到别的群或私聊。

```bash
python3 .cursor/skills/cision-mentions/scripts/export_mentions.py --stream-id 1017610
```

`1017610` 不需要 `--push-feishu`。同步写完表之后会把增量 CSV 推到上面那个群。其他 stream 仍要加 `--push-feishu` 才会推群，并且继续用本地 `latest.csv` 去重。

## 多维表格（仅 1017610）

标识写死，没有命令行参数或环境变量可以改到别的 wiki、表或群：

- wiki：`https://prnewswire.feishu.cn/wiki/ODp7wESdDiXrHjk7tEPcsQrSn6d`
- wiki node token：`ODp7wESdDiXrHjk7tEPcsQrSn6d`
- 多维表格 app token：`ByFgbm0xRaCBD2s8ohtcg0kgnWc`
- table id：`tblpvXJxxasNjP5e`
- 表名：`百度海外竞品最新数据`

这个 app token 就是 wiki 节点 `GET /open-apis/wiki/v2/spaces/get_node` 返回的 `obj_token`（`obj_type=bitable`）。当前两者相同，接口直接用这个 app token 和 table id。嵌入知识库的多维表格如果 app token 和 `obj_token` 不一致，必须用 `obj_token` 调 `/bitable/v1/apps/{token}`，否则会 404。表里原来的文本字段 `文本` 和占位行会保留字段、删掉占位记录。每个 CSV 列若还没有同名文本字段就新建，mention id 的字段名必须是 `id`。

每次导出 `1017610`，顺序固定：

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

## 正文文件（仅 1017610，紧接导出）

这一步和导出在同一次运行里串行完成，不是第二条定时任务。先跑导出。标准输出里的 `delta_rows` 为 0 时不要抓取，也不要再发一条飞书消息。大于 0 时，只用这一次写出的 `delta.csv`。

```bash
python3 .cursor/skills/cision-mentions/scripts/extract_bodies.py --delta-csv <delta.csv> --after <after>
```

`--after` 用导出标准输出里的 `after`。不传时，从 `delta.csv` 的父目录名还原窗口起点。数据日期是这个起点在 Asia/Shanghai 的日历日。运行日 2026-10-26 的窗口起点是 2026-10-25 07:00+08，数据日期是 `2026-10-25`。

抓取在脚本里成批进行，调用 PATH 上的 `firecrawl scrape --only-main-content`。找不到命令时，和缺密钥一样，在发送文件之前停止。不要让 agent 每个 URL 单独开一轮。以后会有几百条 URL。密钥只从环境变量 `FIRECRAWL_API_KEY` 读取，不要写进命令行。

不做模型清洗。`标题` 就是增量 CSV 里的 `title` 列，脚本不改这一列，也不另写标题。新增列名是 `content`，不叫 `正文`。它保存 Firecrawl 返回的整段 markdown，不删导航、不改写、不摘要、不截断，避免后面再抽取时丢掉原文。原有列全部保留，不丢列。输出用 CSV，不用 Excel：xlsx 单元格上限是 32767 个字符，整段 markdown 会更长；CSV 会给含换行、逗号和引号的字段加引号，可以原样放下。文件写在增量旁边，名字是 `delta-bodies.csv`。同一 url 的重复行都保留，并填入同一段 markdown。抓取失败的行仍保留，`content` 为空。

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
3. 写成 `delta-bodies.csv`。原有列顺序不变，最后追加 `content`。
4. 只向群 `oc_27040b0dc3a733ab164199154c489fad` 发两样东西：一段短文本，以及这个文件。短文本只有数据日期、`delta_rows`、抓到的行数和失败行数。不发到别的会话，不发当日表链接，不改当日表。

比较用的「百度海外竞品最新数据」仍只由导出步骤整表重写。这一步不读、不删那张表，也不读、不删当日表。

## 定时运行

本技能不安装、也不注册调度器。能不能定时，分两处：

**Cursor 云端，已在文档里确认的部分。** [Automations](https://cursor.com/docs/cloud-agent/automations) 可以按预设或 cron 启动 cloud agent。用户必须自己创建并启用，地址是 [cursor.com/automations](https://cursor.com/automations)，也可以在 Agents 窗口里建。

上海时间 07:00 和 18:30 是两套已经存在的自动化，各带一条 cron，不是同一个自动化上的两条 cron。一个自动化里放两条 cron 时，只会触发第一条。这两套自动化的提示词必须相同，都在同一次运行里按顺序做导出和正文，不要再拆成第二个定时任务。

1. 触发器选 Scheduled。07:00 那套只用 `0 23 * * *`，18:30 那套只用 `30 10 * * *`。Automations 的 cron 按 UTC 计算。数据窗口都是昨天 07:00（含）到今天 07:00（不含），不要改窗口。文档写明可以延迟触发，但不会早于设定时间开始。
2. 选中本仓库。cron 类触发器默认可以不带仓库；不带仓库时 agent 拿不到这份脚本。
3. 提示词先运行 `export_mentions.py --stream-id 1017610`。看标准输出的 `delta_rows`。等于 0 就停，不要抓正文，不要发第二条消息。大于 0 时，用同一次输出的 `delta_csv` 和 `after` 运行 `extract_bodies.py`。不要逐条 URL 另开对话。不要打印 token、密钥或 mention 正文。不要再传 chat id、wiki 或 table id。不要把正文写入当日表。其他 stream 需要推群时才给导出命令加 `--push-feishu`，并且不要跑正文脚本。
4. 确认启动时能读到 `CISION_API_TOKEN`。`FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 已经是本环境的 Runtime Secret。正文步骤还要 `FIRECRAWL_API_KEY`。缺抓取密钥时，脚本在发送正文文件之前停止，也不改当日表。新的 cloud agent 在启动时会注入已保存的 Runtime Secret，不要为它们重建环境。[Secrets 文档](https://cursor.com/docs/cloud-agent/security-network) 写明 Runtime Secret 会作为环境变量注入，同时在对话、工具输出和提交里打码。[构建文档](https://cursor.com/docs/cloud-agent/builds) 写明用户密钥在 agent 启动时加入，不进入构建快照。只核对变量名是否注入，不要打印值。

**文档没有保证、因此这里不当作已支持能力的部分。**

- 同一次论坛线索提到，带有 “Skip Install” 的旧自动化可能拿不到环境变量。创建后只核对注入的变量名，不要打印值。
- 云端每次定时都会新开一次 cloud agent。环境快照不保留 `latest.csv`。`1017610` 的去重基线在飞书多维表格里，两次云端运行可以对着同一张表。其他 stream 仍靠本机 `latest.csv`；云端没有这份文件时，增量等于当次全量。Memories 不是 CSV 基线，本技能也不会把 mention 内容写进去。
- Automations 自带 Slack 等工具，没有飞书推送工具。飞书只能走本脚本和上面的两个环境变量。
- 本仓库不提供笔记本 crontab。同一台磁盘不重置的机器上，用户可以自行用系统 cron 调用导出命令，那样 `latest.csv` 才能留给下一次。

## 禁止事项

- 不要把 `CISION_API_TOKEN`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FIRECRAWL_API_KEY` 或 tenant access token 打进命令行、日志、提交或对话。
- 不要提交 `full.csv`、`delta.csv`、`latest.csv` 或任何 mention 导出。
- 汇报结果时只给行数、窗口和路径，不粘贴 mention 标题或正文。
- 正文 CSV 只发到 `oc_27040b0dc3a733ab164199154c489fad`，不要发到其他会话，也不要写入当日表。
- 不要逐条 URL 让 agent 循环。抓取在 `extract_bodies.py` 里完成。
