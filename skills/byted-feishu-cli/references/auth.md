# 鉴权说明

## 凭证来源（按优先级）

| 优先级 | 变量 | 说明 |
| --- | --- | --- |
| 1 | `FEISHU_TENANT_ACCESS_TOKEN` / `LARK_TENANT_ACCESS_TOKEN` / `FEISHU_TENANT_TOKEN` | 直接使用租户令牌 |
| 2 | `FEISHU_APP_ID` + `FEISHU_APP_SECRET`（或 `LARK_*`） | 调用 `/auth/v3/tenant_access_token/internal` |
| 3 | `LARK_USER_ACCESS_TOKEN` / `FEISHU_USER_ACCESS_TOKEN` | 用户身份；需加 `--use-user-token` |

命令行可用 `--app-id` / `--app-secret` / `--tenant-token` / `--user-token` 覆盖环境变量，但**不要**在共享日志中留下明文密钥。

## 如何获取 Bot 凭证

1. 打开 [飞书开放平台](https://open.feishu.cn/app)（国际版用 Lark）
2. 创建企业自建应用，或打开已有应用
3. 在「凭证与基础信息」复制 **App ID**、**App Secret**
4. 在「权限管理」开通所需权限（常见：获取与发送单聊/群组消息、获取群信息、获取用户基本信息）
5. 创建并发布应用版本
6. 将机器人拉入目标群（群消息场景）

## 域与 Base URL

| 场景 | 设置 |
| --- | --- |
| 飞书国内默认 | 无需设置，使用 `https://open.feishu.cn/open-apis` |
| Lark 国际版 | `export FEISHU_DOMAIN=lark` |
| 自定义网关 | `export FEISHU_BASE_URL=https://example.com/open-apis` |

## 用户登录（个人未读总结必需）

默认使用 **Device Flow**，对齐官方 lark-cli：**不用改应用重定向 URL**。

```bash
python3 scripts/feishu_cli.py auth login --no-wait
# 用飞书打开返回的 verification_uri_complete，点确认
python3 scripts/feishu_cli.py auth login --device-code '<device_code>'
python3 scripts/feishu_cli.py auth whoami
```

用户令牌保存在 `~/.config/feishu-cli/credentials.json`（权限 600），不要提交到 git。

## 自检

```bash
python3 scripts/feishu_cli.py auth status
python3 scripts/feishu_cli.py auth token --mask
python3 scripts/feishu_cli.py bot info
```

`auth status` 只报告是否配置了凭证，不会打印 Secret。
