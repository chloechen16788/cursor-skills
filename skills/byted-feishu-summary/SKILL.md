---
name: byted-feishu-summary
version: 1.0.0
metadata:
  author: volcengine-agentkit
description: |
  总结飞书近 24 小时未读/待处理消息，分为「与我相关」和「其他消息」。
  当用户提到「飞书总结」「未读消息」「今日飞书」「总结一下飞书」「@我的消息」时使用。
  依赖 byted-feishu-cli 的用户登录与 summary unread 命令。
---

# 飞书未读总结

先定位 `skills/byted-feishu-cli`，再用
`python3 <feishu-cli目录>/scripts/feishu_cli.py` 作为唯一命令入口。
不要手写 HTTP 请求。

## 目标

拉取近 24 小时（可改）会话消息，排除用户自己发的，分成：

| 分组 | 规则 |
| --- | --- |
| **与我相关** | 单聊（p2p）；@我；回复我的消息 |
| **其他消息** | 群里未点名、未回复我的消息 |

飞书开放平台**没有精确未读字段**。本 Skill 用「近 N 小时 + 非本人发送」近似未读待办，并在结果里说明这一点。

## 每次会话先检查登录

```bash
python3 scripts/feishu_cli.py auth status
python3 scripts/feishu_cli.py auth whoami
```

未登录时：

1. 生成链接：`python3 scripts/feishu_cli.py auth login-url`
2. 请用户在飞书开放平台「安全设置」添加重定向 URL（默认 `http://127.0.0.1:8765/callback`）
3. 请用户打开 `authorize_url` 登录授权
4. 用户把回调 URL 里的 `code` 发回来后执行：

```bash
python3 scripts/feishu_cli.py auth login --code '<CODE>'
```

已有 `user_access_token` 时可：

```bash
python3 scripts/feishu_cli.py auth login --user-token '<TOKEN>'
```

**不要把 token / App Secret 写进仓库或完整回显。**

## 执行总结

```bash
python3 scripts/feishu_cli.py summary unread --hours 24 --format json
```

只看可读稿：

```bash
python3 scripts/feishu_cli.py summary unread --hours 24 --format markdown
```

## 对用户的输出格式

用 CLI 返回的 `related` / `others` 写成中文摘要，结构固定为：

1. **概览**：时间范围、扫描会话数、两类条数
2. **与我相关**：按群/单聊列出，优先完整转述 @我、单聊、回复
3. **其他消息**：按群汇总要点，长群只保留关键几条
4. **未能读取的会话**：原样提示权限/机器人不在群等原因

不要编造未返回的消息。不要输出完整 token。

## 权限不足

若报 `99991679` / `230027` / `20027`，请用户在开放平台开通并**发布**：

- `im:chat:readonly`
- `im:message:readonly`
- `im:message.p2p_msg:get_as_user`
- `im:message.group_msg:get_as_user`
- `offline_access`

然后重新 `auth login-url` 授权。
