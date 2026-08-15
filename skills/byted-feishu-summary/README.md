# byted-feishu-summary

总结飞书近 24 小时消息，分为「与我相关」和「其他消息」。

命令实现位于 `../byted-feishu-cli`：

```bash
python3 ../byted-feishu-cli/scripts/feishu_cli.py auth login-url
python3 ../byted-feishu-cli/scripts/feishu_cli.py auth login --code '<CODE>'
python3 ../byted-feishu-cli/scripts/feishu_cli.py summary unread --hours 24
```
