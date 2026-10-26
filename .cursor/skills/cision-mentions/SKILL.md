---
name: cision-mentions
description: 导出 Cision / Streem mentions。列出监测流的 id 与 label，或在已有 stream id 时按上海时间昨天 07:00 至今天 07:00 拉取 CSV、与上次全量去重，并可选用飞书应用凭证推送增量。用户提到 Cision、Streem、mentions、监测流、舆情导出、飞书推送增量时使用。
---

# Cision mentions 导出

## 用途

- 列出账号下的 Mention Stream，只打印 `id` 和 `label`。
- 已有 stream id 时，导出该流在固定时间窗内的 mentions CSV，并与上一份全量去重。
- 两条命令分开调用。导出 mentions 时不要先调用列表接口。

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

要求推送飞书时，推送成功之后才替换 `latest.csv`。推送失败则保留原来的 `latest.csv`，同一窗口重跑仍会把这些行算进增量。未要求推送时，写出 delta 后立刻替换。

## 输出目录

默认目录在仓库外：

`~/.local/share/cision-mentions`

可用环境变量 `CISION_OUTPUT_DIR` 或参数 `--output-dir` 改位置。脚本发现目录落在 git 工作区里会直接退出。仓库 `.gitignore` 里另有 `cision-mentions-output/`，避免有人把输出指到这个名字下后又提交。不要提交这些 CSV。

同一个 stream 的稳定基线是：

`~/.local/share/cision-mentions/state/{streamId}/latest.csv`

## 飞书推送

这是增量 CSV 的推送，实现在导出命令的 `--push-feishu` 上，不是第三条拉数命令。认证只读两个环境变量，代码里不写死，也不再读别的密钥：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

这两个名字已经作为 Runtime Secret 保存在本云环境。脚本只在当前进程看得到它们时才读取。若这次虚拟机是在保存密钥之前启动的，进程里会是未设置；列表和导出不因此失败，也不要向用户索要粘贴。Runtime Secret 在 cloud agent 启动时注入，不写进环境快照，所以不需要、也不要为了注入它们去重建环境。使用本环境新开的一次 cloud agent 运行可以读到这两个变量。

推送只发到写死的群 `oc_27040b0dc3a733ab164199154c489fad`（`receive_id_type=chat_id`）。没有环境变量，也没有命令行参数可以改到别的群或私聊。

```bash
python3 .cursor/skills/cision-mentions/scripts/export_mentions.py \
  --stream-id 1017610 \
  --push-feishu
```

实际调用顺序：

1. `POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`，用 app id 和 app secret 换 `tenant_access_token`。不打印这个 token。
2. `POST /open-apis/im/v1/messages` 发一条文本，只含 stream id、UTC 窗口和行数。不含 mention 标题或正文。
3. 增量有数据行时，再 `POST /open-apis/im/v1/files`（`file_type=stream`）上传 delta CSV，并用 `msg_type=file` 发出。增量为空时只发文本。

用户需要自己在飞书开放平台准备：

- 企业自建应用，把 App ID 和 App Secret 放进上面两个环境变量。
- 打开机器人能力并发布版本。
- 开通「以应用身份发消息」(`im:message:send_as_bot`) 和「获取与上传图片或文件资源」(`im:resource`)。
- 把机器人拉进群 `oc_27040b0dc3a733ab164199154c489fad`。推送不会发到其他会话。

本技能没有飞书群机器人 Webhook，也不读取除此之外的密钥。

## 定时运行

本技能不安装、也不注册调度器。能不能定时，分两处：

**Cursor 云端，已在文档里确认的部分。** [Automations](https://cursor.com/docs/cloud-agent/automations) 可以按预设或 cron 启动 cloud agent。用户必须自己创建并启用，地址是 [cursor.com/automations](https://cursor.com/automations)，也可以在 Agents 窗口里建。创建时要：

1. 触发器选 Scheduled（预设或 cron）。文档写明可以延迟触发，但不会早于设定时间开始。
2. 选中本仓库。cron 类触发器默认可以不带仓库；不带仓库时 agent 拿不到这份脚本。
3. 提示词写明运行 `export_mentions.py --stream-id <id>`，并且不要打印 token 和 mention 内容。需要推送时只加 `--push-feishu`。目标群已经写死，不要再传 chat id。
4. 确认启动时能读到 `CISION_API_TOKEN`。`FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 已经是本环境的 Runtime Secret。新的 cloud agent 在启动时会注入它们，不要为它们重建环境。[Secrets 文档](https://cursor.com/docs/cloud-agent/security-network) 写明 Runtime Secret 会作为环境变量注入，同时在对话、工具输出和提交里打码。[构建文档](https://cursor.com/docs/cloud-agent/builds) 写明用户密钥在 agent 启动时加入，不进入构建快照。只核对变量名是否注入，不要打印值。

**文档没有保证、因此这里不当作已支持能力的部分。**

- Automations 文档页面没有写 cron 的时区。论坛里 Cursor 员工说按 UTC 计算，并提到也许可以加 `CRON_TZ=Asia/Shanghai` 前缀（[讨论](https://forum.cursor.com/t/automations-show-human-readable-description-for-cron-schedules/164058)）。这只是论坛回复，不是文档承诺。若按该回复的 UTC 理解，上海时间每天 07:05 对应 cron `5 23 * * *`。
- 同一次论坛线索提到，带有 “Skip Install” 的旧自动化可能拿不到环境变量。创建后只核对注入的变量名，不要打印值。
- 云端每次定时都会新开一次 cloud agent。环境快照保留的是构建好的依赖和仓库，不是上一次写到 `~/.local/share/cision-mentions` 的 CSV。文档里的 Memories 是跨次笔记，不是这个 CSV 基线，本技能也不会把 mention 内容写进 Memories。因此云端定时跑这条命令时，通常没有上一份 `latest.csv`，增量会等于当次全量。跨次去重要在家目录会保留的机器上跑。
- Automations 自带 Slack 等工具，没有飞书推送工具。飞书只能走本脚本和上面的两个环境变量。
- 本仓库不提供笔记本 crontab。同一台磁盘不重置的机器上，用户可以自行用系统 cron 调用导出命令，那样 `latest.csv` 才能留给下一次。

## 禁止事项

- 不要把 `CISION_API_TOKEN`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET` 或 tenant access token 打进命令行、日志、提交或对话。
- 不要提交 `full.csv`、`delta.csv`、`latest.csv` 或任何 mention 导出。
- 汇报结果时只给行数、窗口和路径，不粘贴 mention 标题或正文。
