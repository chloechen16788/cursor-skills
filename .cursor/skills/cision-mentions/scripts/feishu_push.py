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
# 只有这个 stream 把全量写入下面这张表，并用表里的 id 做去重基线。标识都写死，不能改指向。
BITABLE_SYNC_STREAM_ID = "1017610"
WIKI_URL = "https://prnewswire.feishu.cn/wiki/ODp7wESdDiXrHjk7tEPcsQrSn6d"
WIKI_NODE_TOKEN = "ODp7wESdDiXrHjk7tEPcsQrSn6d"
# 已用 wiki get_node 核对：该节点 obj_type=bitable，obj_token 就是这个值。改表名必须 PATCH；PUT 会得到纯文本 404 page not found。
BITABLE_APP_TOKEN = "ByFgbm0xRaCBD2s8ohtcg0kgnWc"
BITABLE_TABLE_ID = "tblpvXJxxasNjP5e"
BITABLE_TABLE_NAME = "百度海外竞品最新数据"
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"
BITABLE_BATCH = 500


_SECRET_ENV_KEYS = (
    "FEISHU_APP_SECRET",
    "FEISHU_APP_ID",
    "CISION_API_TOKEN",
    "FIRECRAWL_API_KEY",
    "ARTICLE_MODEL_API_KEY",
    "OPENAI_API_KEY",
)


def redact_secrets(text: str) -> str:
    for key in _SECRET_ENV_KEYS:
        secret = os.environ.get(key, "")
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text


def _error_fields(body: bytes, status: int) -> str:
    text = redact_secrets(body.decode("utf-8", errors="replace"))
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
        raise RuntimeError(
            f"飞书接口 code={code} msg={_redact(str(payload.get('msg')))}"
        )
    return payload


def _redact(text: str) -> str:
    return redact_secrets(text)


def credentials_present() -> bool:
    return bool(
        os.environ.get("FEISHU_APP_ID", "").strip()
        and os.environ.get("FEISHU_APP_SECRET", "").strip()
    )


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
    payload = _post(
        TOKEN_URL, body, {"Content-Type": "application/json; charset=utf-8"}
    )
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


def api_request(
    url: str, method: str, payload: dict | None = None, token: str | None = None
) -> dict:
    return _request(url, method, payload, token)


def tenant_token() -> str:
    return _tenant_access_token()


def send_text(text: str) -> None:
    """只发一条文本，不上传文件。目标群仍是写死的 FEISHU_CHAT_ID。"""
    _send_message(_tenant_access_token(), "text", {"text": text})


def send_file(path: Path) -> None:
    """只向固定群发一个文件，不发文本，也不写多维表格。"""
    token = _tenant_access_token()
    file_key = _upload_file(token, path)
    _send_message(token, "file", {"file_key": file_key})


def _open_api_path(url: str) -> str:
    marker = "/open-apis"
    index = url.find(marker)
    return url[index:] if index >= 0 else url


def _request(
    url: str, method: str, payload: dict | None = None, token: str | None = None
) -> dict:
    headers: dict[str, str] = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
    except HTTPError as error:
        raw = error.read() if error.fp is not None else b""
        detail = _error_fields(raw, error.code)
        raise RuntimeError(f"{method} {_open_api_path(url)}：{detail}") from None
    except URLError as error:
        raise RuntimeError(f"飞书请求失败：{error.reason}") from None
    try:
        body = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"飞书响应不是 JSON（{error}）") from None
    code = body.get("code")
    if code not in (0, None):
        raise RuntimeError(f"飞书接口 code={code} msg={_redact(str(body.get('msg')))}")
    return body


def cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    if isinstance(value, dict):
        return str(value.get("text") or "").strip()
    return str(value).strip()


class FeishuBitable:
    """只访问写死的那张表。不接受 app token、table id 或 wiki token 参数。"""

    def __init__(self) -> None:
        self._token = ""

    def _bearer(self) -> str:
        if not self._token:
            self._token = _tenant_access_token()
        return self._token

    def _url(self, suffix: str, query: dict | None = None) -> str:
        base = (
            f"{BITABLE_API}/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}{suffix}"
        )
        if not query:
            return base
        return base + "?" + urlencode(query)

    def _get_data(self, url: str) -> dict:
        body = _request(url, "GET", token=self._bearer())
        data = body.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("飞书响应缺少 data")
        return data

    def list_fields(self) -> list[str]:
        names: list[str] = []
        page_token = ""
        for _ in range(100):
            query = {"page_size": 100}
            if page_token:
                query["page_token"] = page_token
            data = self._get_data(self._url("/fields", query))
            for item in data.get("items") or []:
                name = item.get("field_name")
                if isinstance(name, str) and name:
                    names.append(name)
            if not data.get("has_more"):
                return names
            page_token = str(data.get("page_token") or "")
            if not page_token:
                return names
        raise RuntimeError("字段分页没有结束")

    def list_records(self) -> list[dict]:
        records: list[dict] = []
        page_token = ""
        for _ in range(1000):
            query = {"page_size": BITABLE_BATCH}
            if page_token:
                query["page_token"] = page_token
            data = self._get_data(self._url("/records", query))
            items = data.get("items")
            if items is None:
                items = data.get("records") or []
            if not isinstance(items, list):
                raise RuntimeError("记录列表不是数组")
            records.extend(item for item in items if isinstance(item, dict))
            if not data.get("has_more"):
                return records
            page_token = str(data.get("page_token") or "")
            if not page_token:
                return records
        raise RuntimeError("记录分页没有结束")

    def create_field(self, name: str) -> None:
        _request(
            self._url("/fields"),
            "POST",
            {"field_name": name, "type": 1},
            token=self._bearer(),
        )

    def ensure_name(self) -> None:
        page_token = ""
        found = False
        current = ""
        for _ in range(100):
            query = {"page_size": 100}
            if page_token:
                query["page_token"] = page_token
            data = self._get_data(
                f"{BITABLE_API}/apps/{BITABLE_APP_TOKEN}/tables?{urlencode(query)}"
            )
            for item in data.get("items") or []:
                if (
                    not isinstance(item, dict)
                    or item.get("table_id") != BITABLE_TABLE_ID
                ):
                    continue
                found = True
                current = str(item.get("name") or "")
                break
            if found or not data.get("has_more"):
                break
            page_token = str(data.get("page_token") or "")
            if not page_token:
                break
        if not found:
            raise RuntimeError("写死的 table id 不在该多维表格里")
        if current == BITABLE_TABLE_NAME:
            return
        # 更新数据表只有 PATCH。PUT 同一路径会返回 HTTP 404，正文是「404 page not found」。
        _request(
            self._url(""), "PATCH", {"name": BITABLE_TABLE_NAME}, token=self._bearer()
        )

    def delete_records(self, record_ids: list[str]) -> None:
        for start in range(0, len(record_ids), BITABLE_BATCH):
            chunk = record_ids[start : start + BITABLE_BATCH]
            _request(
                self._url("/records/batch_delete"),
                "POST",
                {"records": chunk},
                token=self._bearer(),
            )

    def create_records(self, field_rows: list[dict]) -> None:
        for start in range(0, len(field_rows), BITABLE_BATCH):
            chunk = [
                {"fields": fields}
                for fields in field_rows[start : start + BITABLE_BATCH]
            ]
            _request(
                self._url("/records/batch_create"),
                "POST",
                {"records": chunk},
                token=self._bearer(),
            )


def _previous_ids(field_names: list[str], records: list[dict]) -> set[str]:
    if "id" not in field_names:
        return set()
    found: set[str] = set()
    for record in records:
        text = cell_text((record.get("fields") or {}).get("id"))
        if text:
            found.add(text)
    return found


def _field_rows(header: list[str], rows: list[list[str]]) -> list[dict]:
    payloads: list[dict] = []
    for row in rows:
        fields: dict[str, str] = {}
        for index, name in enumerate(header):
            if not name:
                continue
            raw = row[index] if index < len(row) else ""
            fields[name] = "" if raw is None else str(raw)
        payloads.append(fields)
    return payloads


def sync_1017610_baseline(
    header: list[str],
    rows: list[list[str]],
    delta_path: Path,
    summary: dict,
    client=None,
    push=None,
) -> dict:
    """先读 id。读失败则不删除。再删光表，写入本次全量，最后才推增量 CSV。"""
    import cision_lib

    if "id" not in header:
        raise RuntimeError("CSV 缺少 id 列，未删除任何记录")
    if client is None:
        if not credentials_present():
            raise RuntimeError(missing_credentials_message())
        client = FeishuBitable()
    if push is None:
        push = push_delta

    try:
        field_names = list(client.list_fields())
    except Exception as error:
        raise RuntimeError(f"读取多维表格字段失败，未删除任何记录：{error}") from None
    try:
        records = list(client.list_records())
    except Exception as error:
        raise RuntimeError(f"读取多维表格记录失败，未删除任何记录：{error}") from None

    previous = _previous_ids(field_names, records)
    delta = cision_lib.select_delta(header, rows, previous)
    cision_lib.write_csv(delta_path, header, delta)

    try:
        for name in header:
            if name and name not in field_names:
                client.create_field(name)
                field_names.append(name)
        client.ensure_name()
    except Exception as error:
        raise RuntimeError(f"准备多维表格字段失败，未删除任何记录：{error}") from None

    record_ids = [
        str(record.get("record_id")) for record in records if record.get("record_id")
    ]
    try:
        client.delete_records(record_ids)
    except Exception as error:
        raise RuntimeError(
            f"删除多维表格记录失败，未写入新记录，也未推送：{error}"
        ) from None
    try:
        client.create_records(_field_rows(header, rows))
    except Exception as error:
        raise RuntimeError(f"写入多维表格失败，未推送增量：{error}") from None

    updated = dict(summary)
    updated["previous_exists"] = bool(previous)
    updated["previous_ids"] = len(previous)
    updated["delta_rows"] = len(delta)
    updated["dedup"] = "bitable"
    updated["bitable_deleted"] = len(record_ids)
    updated["bitable_written"] = len(rows)
    updated["latest_csv"] = "unused"
    push(delta_path, updated)
    updated["feishu"] = "sent" if delta else "sent_text"
    return updated
