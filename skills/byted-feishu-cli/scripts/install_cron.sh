#!/usr/bin/env bash
# Install a local cron tick: every 30 minutes, 07:00-19:00 Asia/Shanghai.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="$SCRIPT_DIR/feishu_cli.py"
ENV_FILE="${FEISHU_CLI_ENV:-$HOME/.config/feishu-cli/app.env}"
LOG_FILE="${FEISHU_SUMMARY_LOG:-$HOME/.config/feishu-cli/summary-cron.log}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "缺少 $ENV_FILE ，请写入 FEISHU_APP_ID / FEISHU_APP_SECRET" >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"
LINE="*/30 * * * * TZ=Asia/Shanghai . $ENV_FILE; /usr/bin/python3 $CLI summary tick --minutes 30 --notify --window-start 07:00 --window-end 19:00 >> $LOG_FILE 2>&1"

existing="$(crontab -l 2>/dev/null || true)"
filtered="$(printf '%s\n' "$existing" | grep -v 'feishu_cli.py summary tick' || true)"
printf '%s\n%s\n' "$filtered" "$LINE" | crontab -
echo "已安装 cron:"
echo "$LINE"
crontab -l | grep 'feishu_cli.py summary tick'
