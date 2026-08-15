# byted-feishu-cli

飞书 / Lark OpenAPI 命令行 Skill：Bot 鉴权、群聊、消息收发、用户查询与通用 API 调用。

## 快速开始

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

python3 scripts/feishu_cli.py auth status
python3 scripts/feishu_cli.py bot info
python3 scripts/feishu_cli.py chat list
```

## 依赖

Python 3.10+，仅标准库，无需额外 pip 包。

## 相关 Skill

- 文档/Wiki/表格搜索：`byted-viking-aisearch-feishu`
- 告警巡检分析：`byted-volcengine-alert-inspection-analyzer`
