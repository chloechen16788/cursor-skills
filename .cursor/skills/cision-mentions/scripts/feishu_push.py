#!/usr/bin/env python3
"""用飞书企业自建应用凭证推送增量结果。只读取 FEISHU_APP_ID 与 FEISHU_APP_SECRET。"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
UPLOAD_URL = "https://open.feishu.cn/open-apis/im/v1/files"
MAX_FILE_BYTES = 30 * 1024 * 1024
# 只发到这个群。不要从环境变量或命令行读取，避免推到别的会话。
FEISHU_CHAT_ID = "oc_27040b0dc3a733ab164199154c489fad"
FEISHU_RECEIVE_ID_TYPE = "chat_id"


def _error_fields(body: bytes, status: int) -> str:
    text = body.decode("utf-8", errors="replace")
    for key in ("FEISHU_APP_SECRET", "FEISHU_APP_ID", "CISION_API_TOKEN"):
        secret = os.environ.get(key, "")
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if len(text) > 300:
            return f"HTTP {status}，响应体 {len(body)} 字节"
        return f"HTTP {status}：{' '.join(text.split())[:300]}"
    code = payload.get("code")
    msg = payload.get("msg") or payload.get("message")
    return f"飞书接口 code={code} msg={msg}"


def _post(url: str, data: bytes, headers: dict[str, str]) -> dict:
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
    except HTTPError as error:
        raw = error.read() if error.fp is not None else b""
        raise RuntimeError(_error_fields(raw, error.code)) from None
    except URLError as error:
        raise RuntimeError(f"飞书请求失败：{error.reason}") from None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"飞书响应不是 JSON（{error}）") from None
    code = payload.get("code")
    if code not in (0, None):
        raise RuntimeError(f"飞书接口 code={code} msg={_redact(str(payload.get('msg')))}")
    return payload


def _redact(text: str) -> str:
    for key in ("FEISHU_APP_SECRET", "FEISHU_APP_ID", "CISION_API_TOKEN"):
        secret = os.environ.get(key, "")
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text


def credentials_present() -> bool:
    return bool(os.environ.get("FEISHU_APP_ID", "").strip() and os.environ.get("FEISHU_APP_SECRET", "").strip())


def missing_credentials_message() -> str:
    return (
        "当前进程读不到 FEISHU_APP_ID 或 FEISHU_APP_SECRET。"
        "这两个 Runtime Secret 已保存在本云环境，新启动的 cloud agent 会在启动时注入，无需重建环境。"
        "不要把凭证写进命令、日志或对话。"
    )


def _tenant_access_token() -> str:
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise RuntimeError(missing_credentials_message())
    body = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    payload = _post(TOKEN_URL, body, {"Content-Type": "application/json; charset=utf-8"})
    token = payload.pop("tenant_access_token", None)
    if not token:
        raise RuntimeError(
            f"飞书未返回 tenant_access_token：code={payload.get('code')} msg={_redact(str(payload.get('msg')))}"
        )
    return token


def _send_message(token: str, msg_type: str, content: dict) -> None:
    query = urlencode({"receive_id_type": FEISHU_RECEIVE_ID_TYPE})
    body = json.dumps(
        {
            "receive_id": FEISHU_CHAT_ID,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        }
    ).encode("utf-8")
    _post(
        f"{MESSAGE_URL}?{query}",
        body,
        {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
    )


def _upload_file(token: str, path: Path) -> str:
    content = path.read_bytes()
    if len(content) > MAX_FILE_BYTES:
        raise RuntimeError(f"增量 CSV 超过 30MB（{len(content)} 字节），未上传")
    boundary = "----CisionMentions" + uuid.uuid4().hex
    filename = path.name.replace('"', "")
    prefix = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file_type"\r\n\r\n'
        "stream\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file_name"\r\n\r\n'
        f"{filename}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")
    payload = _post(
        UPLOAD_URL,
        prefix + content + suffix,
        {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
    )
    file_key = (payload.get("data") or {}).get("file_key")
    if not file_key:
        raise RuntimeError(
            f"飞书上传未返回 file_key：code={payload.get('code')} msg={_redact(str(payload.get('msg')))}"
        )
    return file_key


def summary_text(summary: dict) -> str:
    previous = "yes" if summary["previous_exists"] else "no"
    return "\n".join(
        [
            "Cision mentions 增量",
            f"stream_id={summary['stream_id']}",
            f"after={summary['after']}",
            f"before={summary['before']}",
            f"full_rows={summary['full_rows']}",
            f"previous_exists={previous}",
            f"delta_rows={summary['delta_rows']}",
        ]
    )


def push_delta(delta_path: Path, summary: dict) -> None:
    token = _tenant_access_token()
    _send_message(token, "text", {"text": summary_text(summary)})
    if summary["delta_rows"] > 0:
        file_key = _upload_file(token, delta_path)
        _send_message(token, "file", {"file_key": file_key})
