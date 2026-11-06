---
name: byted-feishu-cli
version: 1.1.0
metadata:
  author: volcengine-agentkit
description: |
  飞书 / Lark OpenAPI 命令行工具。用于机器人鉴权、用户 OAuth 登录、查询 Bot 信息、管理群聊、收发与回复消息、查询用户、通用 OpenAPI 调用，以及近 24 小时未读消息总结。
  当用户提到「飞书 CLI」「飞书机器人」「发飞书消息」「拉飞书群消息」「Lark bot」「feishu cli」或需要通过飞书开放平台执行 IM/通讯录操作时使用。
  文档搜索请优先使用 byted-viking-aisearch-feishu。未读总结也可使用 byted-feishu-summary。
---

# 飞书 CLI

先定位本 Skill 目录，再将
`python3 <skill目录>/scripts/feishu_cli.py` 作为唯一命令入口。
脚本可从任意当前目录运行。不要手写 HTTP 请求；构造不熟悉的参数前先查看对应命令的 `--help`。

## 与现有 Skill 的关系

| Skill | 能力 | 鉴权 |
| --- | --- | --- |
| **byted-feishu-cli（本 Skill）** | Bot/IM + 用户登录 + 24h 消息总结 | App 凭证；用户未读需 OAuth |
| `byted-feishu-summary` | 未读总结的工作流封装（调用本 CLI） | 用户 OAuth |
| `byted-viking-aisearch-feishu` | 云文档 / 表格 / 多维表格 / Wiki **只读搜索与读取** | `LARK_USER_ACCESS_TOKEN` |
| `byted-volcengine-alert-inspection-analyzer` | 告警巡检分析流程（依赖宿主飞书拉消息工具） | 宿主注入 |

IM、Bot、群消息走本 CLI；文档搜索继续用 `byted-viking-aisearch-feishu`。

## 鉴权

优先级：

1. 环境变量 `FEISHU_TENANT_ACCESS_TOKEN` / `LARK_TENANT_ACCESS_TOKEN` / `FEISHU_TENANT_TOKEN`
2. `FEISHU_APP_ID` + `FEISHU_APP_SECRET`（或 `LARK_APP_ID` + `LARK_APP_SECRET`）换取 tenant token
3. 需要用户身份时：执行 `auth login`（Device Flow，打开飞书链接确认即可，**不必改应用重定向 URL**）

可选：

- `FEISHU_BASE_URL` / `LARK_BASE_URL`：自定义 OpenAPI 根路径
- `FEISHU_DOMAIN=lark`：切换到 `https://open.larksuite.com/open-apis`

**不要把 App Secret / Token 写入对话、日志或提交到仓库。** 缺凭证时向用户索取 Bot 的 App ID 与 App Secret（或现成 tenant token）。

详情见 [references/auth.md](references/auth.md)。

## 命令导航

```bash
python3 scripts/feishu_cli.py version
python3 scripts/feishu_cli.py auth status
python3 scripts/feishu_cli.py auth token --mask
python3 scripts/feishu_cli.py auth login-url
python3 scripts/feishu_cli.py auth login --code '<CODE>'
python3 scripts/feishu_cli.py auth whoami
python3 scripts/feishu_cli.py summary unread --hours 24
python3 scripts/feishu_cli.py summary unread --hours 24 --notify
python3 scripts/feishu_cli.py summary tick --minutes 30 --notify --force
# 安装本机 cron（每天 07:00-19:00 每 30 分钟，需 ~/.config/feishu-cli/app.env）
bash scripts/install_cron.sh
python3 scripts/feishu_cli.py bot info
python3 scripts/feishu_cli.py chat list --page-size 20
python3 scripts/feishu_cli.py chat get --chat-id oc_xxx
python3 scripts/feishu_cli.py chat members --chat-id oc_xxx
python3 scripts/feishu_cli.py message send --receive-id oc_xxx --receive-id-type chat_id --text 'hello'
python3 scripts/feishu_cli.py message reply --message-id om_xxx --text '收到'
python3 scripts/feishu_cli.py message get --message-id om_xxx
python3 scripts/feishu_cli.py message list --chat-id oc_xxx --start-time 1710000000 --end-time 1710086400
python3 scripts/feishu_cli.py user get --user-id ou_xxx --user-id-type open_id
python3 scripts/feishu_cli.py api call --method GET --path /im/v1/chats --params '{"page_size":10}'
```

完整 Action 与参数说明见 [references/actions.md](references/actions.md)。

## 强制规则

1. **默认只读**：`auth` / `bot info` / `chat list|get|members` / `message get|list` / `user get` 可直接执行。
2. **写操作需确认**：`message send` / `message reply` 以及会改状态的 `api call`，先展示将要发送的摘要，取得用户明确同意后再执行。
3. **凭证不出境**：输出里可对 token 使用 `--mask`；不要回显完整 App Secret。
4. **时间戳**：`message list` 的 `--start-time` / `--end-time` 使用**秒级** Unix 时间戳。
5. **权限不足**：若返回 `99991672` / `99991663` 等权限错误，提示用户在飞书开放平台给应用开通对应 IM/通讯录权限并发布版本，必要时把机器人拉进目标群。

## 输出约定

所有命令输出统一 JSON 信封：

```json
{
  "success": true,
  "action": "bot.info",
  "request_id": null,
  "result": {},
  "error": null
}
```

失败时 `success=false`，`error.code` / `error.message` 供排查；保留飞书原始 `error.response` 中的公开字段。
