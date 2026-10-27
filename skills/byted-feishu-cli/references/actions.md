# 命令与 OpenAPI 对照

入口：`python3 scripts/feishu_cli.py <command> ...`

## 全局 flags

| Flag | 说明 |
| --- | --- |
| `--app-id` / `--app-secret` | 覆盖 Bot 凭证 |
| `--tenant-token` | 直接使用 tenant_access_token |
| `--user-token` / `--use-user-token` | 用户令牌模式 |
| `--base-url` | 覆盖 OpenAPI 根路径 |
| `--timeout` | 超时秒数，默认 30 |

## 命令表

| CLI | HTTP | 读/写 |
| --- | --- | --- |
| `version` | 本地 | 读 |
| `auth status` | 本地 | 读 |
| `auth token` | `POST /auth/v3/tenant_access_token/internal` | 读 |
| `auth login-url` | 本地生成 OAuth URL | 读 |
| `auth login` | `POST /authen/v2/oauth/token` | 读 |
| `auth whoami` | `GET /authen/v1/user_info` | 读 |
| `auth logout` | 本地删凭证 | 读 |
| `summary unread` | 分页 `GET /im/v1/chats` + `GET /im/v1/messages` | 读 |
| `summary unread --notify` | 总结后 `POST /im/v1/messages` 推到飞书（手机通知） | **写** |
| `summary tick` | 北京时间 07:00-19:00 内总结近 30 分钟并推送 | **写** |
| `bot info` | `GET /bot/v3/info` | 读 |
| `chat list` | `GET /im/v1/chats` | 读 |
| `chat get --chat-id` | `GET /im/v1/chats/:chat_id` | 读 |
| `chat members --chat-id` | `GET /im/v1/chats/:chat_id/members` | 读 |
| `message send` | `POST /im/v1/messages` | **写** |
| `message reply` | `POST /im/v1/messages/:message_id/reply` | **写** |
| `message get` | `GET /im/v1/messages/:message_id` | 读 |
| `message list` | `GET /im/v1/messages` | 读 |
| `user get` | `GET /contact/v3/users/:user_id` | 读 |
| `api call` | 任意 path | 视方法 |

## message send 示例

文本：

```bash
python3 scripts/feishu_cli.py message send \
  --receive-id oc_xxx \
  --receive-id-type chat_id \
  --msg-type text \
  --text '巡检完成'
```

富文本 / 卡片：把 content JSON 放进 `--content` 或 `--content-file`。

```bash
python3 scripts/feishu_cli.py message send \
  --receive-id ou_xxx \
  --receive-id-type open_id \
  --msg-type interactive \
  --content-file ./card.json
```

## message list 时间

`--start-time` / `--end-time` 为秒级 Unix 时间戳。例如北京时间一天：

```bash
python3 - <<'PY'
from datetime import datetime, timezone, timedelta
tz = timezone(timedelta(hours=8))
start = datetime(2026, 6, 5, 0, 0, tzinfo=tz)
end = datetime(2026, 6, 5, 23, 59, 59, tzinfo=tz)
print(int(start.timestamp()), int(end.timestamp()))
PY
```

## 通用调用

未封装的接口用：

```bash
python3 scripts/feishu_cli.py api call \
  --method POST \
  --path /im/v1/messages \
  --params '{"receive_id_type":"chat_id"}' \
  --body '{"receive_id":"oc_xxx","msg_type":"text","content":"{\"text\":\"hi\"}"}'
```

官方文档：https://open.feishu.cn/document/
