# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Collect last-N-hour Feishu messages and split related / other."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

from client import FeishuApiError, FeishuClient

BJ = timezone(timedelta(hours=8))


def extract_text(message: Mapping[str, Any], *, limit: int = 500) -> str:
    body = message.get("body") or {}
    raw = body.get("content")
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=False)
    text = _content_to_text(raw)
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _content_to_text(raw: str) -> str:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return raw
    if obj.get("text"):
        return str(obj["text"])
    if obj.get("title"):
        return str(obj["title"])
    chunks: List[str] = []
    content = obj.get("content")
    if isinstance(content, list):
        for paragraph in content:
            if not isinstance(paragraph, list):
                continue
            for node in paragraph:
                if not isinstance(node, dict):
                    continue
                if node.get("text"):
                    chunks.append(str(node["text"]))
                elif node.get("content"):
                    chunks.append(str(node["content"]))
    if chunks:
        return " ".join(chunks)
    return raw


def sender_id(message: Mapping[str, Any]) -> str:
    sender = message.get("sender") or {}
    return str(sender.get("id") or "")


def mention_ids(message: Mapping[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    for item in message.get("mentions") or []:
        if isinstance(item, Mapping) and item.get("id"):
            ids.add(str(item["id"]))
    return ids


def is_from_me(message: Mapping[str, Any], me_ids: Set[str]) -> bool:
    return sender_id(message) in me_ids


def is_related_to_me(
    message: Mapping[str, Any],
    *,
    me_ids: Set[str],
    chat_mode: str,
    my_message_ids: Set[str],
) -> bool:
    if (chat_mode or "").lower() == "p2p":
        return True
    if mention_ids(message) & me_ids:
        return True
    parent = str(message.get("parent_id") or "")
    root = str(message.get("root_id") or "")
    if parent and parent in my_message_ids:
        return True
    if root and root in my_message_ids:
        return True
    return False


def related_reasons(
    message: Mapping[str, Any],
    *,
    me_ids: Set[str],
    chat_mode: str,
    my_message_ids: Set[str],
) -> List[str]:
    reasons: List[str] = []
    if (chat_mode or "").lower() == "p2p":
        reasons.append("p2p")
    if mention_ids(message) & me_ids:
        reasons.append("mention")
    parent = str(message.get("parent_id") or "")
    root = str(message.get("root_id") or "")
    if (parent and parent in my_message_ids) or (root and root in my_message_ids):
        reasons.append("reply_to_me")
    return reasons


def _message_time(message: Mapping[str, Any]) -> Optional[int]:
    raw = message.get("create_time")
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value > 10**12:
        value //= 1000
    return value


def format_time(ts: Optional[int]) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, BJ).strftime("%Y-%m-%d %H:%M")


def paginate_chats(
    client: FeishuClient,
    *,
    page_size: int = 50,
    max_chats: int = 80,
    user_id_type: str = "open_id",
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    while len(items) < max_chats:
        payload = client.list_chats(
            page_size=min(page_size, max_chats - len(items)),
            page_token=page_token,
            sort_type="ByActiveTimeDesc",
            user_id_type=user_id_type,
        )
        data = payload.get("data") or payload
        batch = [item for item in (data.get("items") or []) if isinstance(item, dict)]
        items.extend(batch)
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        if not page_token:
            break
    return items[:max_chats]


def paginate_messages(
    client: FeishuClient,
    chat_id: str,
    *,
    start_time: int,
    end_time: int,
    page_size: int = 50,
    max_messages: int = 80,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    while len(items) < max_messages:
        payload = client.list_messages(
            container_id=chat_id,
            container_id_type="chat",
            start_time=str(start_time),
            end_time=str(end_time),
            page_size=min(page_size, 50),
            page_token=page_token,
            sort_type="ByCreateTimeDesc",
        )
        data = payload.get("data") or payload
        batch = [item for item in (data.get("items") or []) if isinstance(item, dict)]
        items.extend(batch)
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        if not page_token:
            break
    return items[:max_messages]


def collect_unread_window(
    client: FeishuClient,
    *,
    me_ids: Set[str],
    hours: int = 24,
    max_chats: int = 40,
    max_messages_per_chat: int = 40,
) -> Dict[str, Any]:
    end_time = int(time.time())
    start_time = end_time - hours * 3600
    chats = paginate_chats(client, max_chats=max_chats)
    related: List[Dict[str, Any]] = []
    others: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for chat in chats:
        chat_id = str(chat.get("chat_id") or "")
        if not chat_id:
            continue
        chat_mode = str(chat.get("chat_mode") or "group")
        chat_name = str(chat.get("name") or ("单聊" if chat_mode == "p2p" else chat_id))
        try:
            messages = paginate_messages(
                client,
                chat_id,
                start_time=start_time,
                end_time=end_time,
                max_messages=max_messages_per_chat,
            )
        except FeishuApiError as exc:
            skipped.append(
                {
                    "chat_id": chat_id,
                    "chat_name": chat_name,
                    "error": str(exc),
                    "code": exc.code,
                }
            )
            continue

        my_ids = {
            str(msg.get("message_id"))
            for msg in messages
            if msg.get("message_id") and is_from_me(msg, me_ids)
        }
        incoming = [
            msg
            for msg in messages
            if not msg.get("deleted") and not is_from_me(msg, me_ids)
        ]
        for msg in incoming:
            item = {
                "chat_id": chat_id,
                "chat_name": chat_name,
                "chat_mode": chat_mode,
                "message_id": msg.get("message_id"),
                "msg_type": msg.get("msg_type"),
                "create_time": _message_time(msg),
                "create_time_text": format_time(_message_time(msg)),
                "sender_id": sender_id(msg),
                "sender_type": (msg.get("sender") or {}).get("sender_type"),
                "text": extract_text(msg),
                "reasons": related_reasons(
                    msg,
                    me_ids=me_ids,
                    chat_mode=chat_mode,
                    my_message_ids=my_ids,
                ),
            }
            if is_related_to_me(
                msg, me_ids=me_ids, chat_mode=chat_mode, my_message_ids=my_ids
            ):
                related.append(item)
            else:
                others.append(item)

    related.sort(key=lambda x: x.get("create_time") or 0, reverse=True)
    others.sort(key=lambda x: x.get("create_time") or 0, reverse=True)
    return {
        "window": {
            "hours": hours,
            "start_time": start_time,
            "end_time": end_time,
            "start_time_text": format_time(start_time),
            "end_time_text": format_time(end_time),
            "timezone": "Asia/Shanghai",
        },
        "chats_scanned": len(chats),
        "related": related,
        "others": others,
        "skipped_chats": skipped,
        "note": (
            "飞书开放平台不提供精确未读状态；本结果为近 N 小时内、非本人发送的消息，"
            "按「与我相关 / 其他」分类，作为未读待办的近似。"
        ),
    }


def group_by_chat(items: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for item in items:
        chat_id = str(item.get("chat_id") or "")
        if chat_id not in grouped:
            grouped[chat_id] = {
                "chat_id": chat_id,
                "chat_name": item.get("chat_name"),
                "chat_mode": item.get("chat_mode"),
                "count": 0,
                "messages": [],
            }
            order.append(chat_id)
        grouped[chat_id]["count"] += 1
        grouped[chat_id]["messages"].append(item)
    return [grouped[key] for key in order]


def render_markdown(result: Mapping[str, Any]) -> str:
    window = result.get("window") or {}
    related = list(result.get("related") or [])
    others = list(result.get("others") or [])
    lines = [
        f"# 飞书近 {window.get('hours', 24)} 小时消息总结",
        "",
        f"- 时间范围：{window.get('start_time_text')} ~ {window.get('end_time_text')}（北京时间）",
        f"- 扫描会话：{result.get('chats_scanned', 0)}",
        f"- 与我相关：{len(related)} 条",
        f"- 其他消息：{len(others)} 条",
        "",
        "## 与我相关",
        "",
    ]
    if not related:
        lines.append("近窗口内没有 @我、单聊或回复我的消息。")
        lines.append("")
    else:
        for chat in group_by_chat(related):
            lines.append(f"### {chat['chat_name']}（{chat['count']}）")
            for msg in chat["messages"][:20]:
                reasons = ",".join(msg.get("reasons") or []) or "related"
                lines.append(
                    f"- [{msg.get('create_time_text')}] ({reasons}) {msg.get('text') or '(非文本)'}"
                )
            lines.append("")

    lines.extend(["## 其他消息", ""])
    if not others:
        lines.append("近窗口内没有其他群消息。")
        lines.append("")
    else:
        for chat in group_by_chat(others):
            lines.append(f"### {chat['chat_name']}（{chat['count']}）")
            for msg in chat["messages"][:8]:
                text = msg.get("text") or "(非文本)"
                lines.append(f"- [{msg.get('create_time_text')}] {text}")
            if chat["count"] > 8:
                lines.append(f"- … 另有 {chat['count'] - 8} 条")
            lines.append("")

    skipped = list(result.get("skipped_chats") or [])
    if skipped:
        lines.extend(["## 未能读取的会话", ""])
        for item in skipped:
            lines.append(f"- {item.get('chat_name')}: {item.get('error')}")
        lines.append("")

    if result.get("note"):
        lines.extend(["> " + str(result["note"]), ""])
    return "\n".join(lines).rstrip() + "\n"
