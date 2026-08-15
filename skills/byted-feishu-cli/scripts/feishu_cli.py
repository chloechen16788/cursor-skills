#!/usr/bin/env python3
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
"""Feishu / Lark OpenAPI CLI entry point."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from client import FeishuApiError, FeishuClient  # noqa: E402
from credentials import (  # noqa: E402
    clear_credentials,
    credential_path,
    load_credentials,
    save_credentials,
    token_expired,
)
from oauth import (  # noqa: E402
    DEFAULT_REDIRECT_URI,
    DEFAULT_SCOPES,
    build_authorize_url,
    exchange_code,
    refresh_user_token,
)
from summary import collect_unread_window, render_markdown  # noqa: E402

CLI_VERSION = "1.1.0"


class CliError(ValueError):
    def __init__(self, message: str, code: str = "validation_error") -> None:
        super().__init__(message)
        self.code = code


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliError(message, "argument_error")


def emit_json(payload: Mapping[str, Any], *, exit_code: int = 0) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return exit_code


def success(action: str, result: Any, *, request_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "success": True,
        "action": action,
        "request_id": request_id,
        "result": result,
        "error": None,
    }


def failure(
    action: str,
    *,
    code: Any,
    message: str,
    response: Any = None,
    retryable: bool = False,
) -> Dict[str, Any]:
    return {
        "success": False,
        "action": action,
        "request_id": None,
        "result": None,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "response": response,
        },
    }


def _mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _load_json_value(raw: Optional[str], *, flag: str) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(f"{flag} 不是合法 JSON: {exc}") from exc


def _load_content(args: argparse.Namespace) -> Any:
    if getattr(args, "text", None) is not None:
        if args.msg_type and args.msg_type != "text":
            raise CliError("--text 仅适用于 msg_type=text；其他类型请用 --content/--content-file")
        return {"text": args.text}
    if getattr(args, "content_file", None):
        path = pathlib.Path(args.content_file)
        if not path.exists():
            raise CliError(f"content 文件不存在: {path}")
        text = path.read_text(encoding="utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text.strip()
    if getattr(args, "content", None) is not None:
        parsed = _load_json_value(args.content, flag="--content")
        return parsed
    raise CliError("请提供 --text、--content 或 --content-file")


def _stored_user_token(args: argparse.Namespace) -> Optional[str]:
    if getattr(args, "user_token", None):
        return args.user_token
    creds = load_credentials(getattr(args, "credentials", None))
    token = creds.get("user_access_token")
    return str(token) if token else None


def _maybe_refresh_stored_token(args: argparse.Namespace, client: FeishuClient) -> None:
    creds = load_credentials(getattr(args, "credentials", None))
    if not creds.get("user_access_token"):
        return
    if not token_expired(creds):
        client.set_user_token(str(creds["user_access_token"]))
        return
    refresh = creds.get("refresh_token")
    if not refresh:
        return
    try:
        token_info = refresh_user_token(client, str(refresh))
    except FeishuApiError:
        return
    creds.update(token_info)
    save_credentials(creds, getattr(args, "credentials", None))
    client.set_user_token(str(token_info["user_access_token"]))


def build_client(args: argparse.Namespace) -> FeishuClient:
    client = FeishuClient(
        app_id=getattr(args, "app_id", None),
        app_secret=getattr(args, "app_secret", None),
        tenant_access_token=getattr(args, "tenant_token", None),
        user_access_token=_stored_user_token(args),
        base_url=getattr(args, "base_url", None),
        timeout=float(getattr(args, "timeout", 30.0)),
        prefer_user_token=bool(getattr(args, "use_user_token", False)),
    )
    _maybe_refresh_stored_token(args, client)
    return client


def _public_user_profile(payload: Mapping[str, Any]) -> Dict[str, Any]:
    data = payload.get("data") or payload
    return {
        "name": data.get("name"),
        "en_name": data.get("en_name"),
        "open_id": data.get("open_id"),
        "union_id": data.get("union_id"),
        "tenant_key": data.get("tenant_key"),
    }


def cmd_version(_: argparse.Namespace) -> Dict[str, Any]:
    return success(
        "version",
        {
            "name": "byted-feishu-cli",
            "version": CLI_VERSION,
        },
    )


def cmd_auth_status(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    status = client.auth_status()
    status["app_id_masked"] = _mask_secret(client.app_id)
    creds = load_credentials(getattr(args, "credentials", None))
    status["has_stored_user_token"] = bool(creds.get("user_access_token"))
    status["stored_user_expired"] = token_expired(creds) if creds else False
    status["credentials_path"] = str(credential_path(getattr(args, "credentials", None)))
    return success("auth.status", status)


def cmd_auth_login_url(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    if not client.app_id:
        raise CliError("生成登录链接需要 FEISHU_APP_ID / --app-id")
    info = build_authorize_url(
        app_id=client.app_id,
        redirect_uri=args.redirect_uri,
        scope=args.scope or DEFAULT_SCOPES,
    )
    info["setup"] = [
        "在飞书开放平台「安全设置」添加重定向 URL: " + args.redirect_uri,
        "开通并发布权限: im:chat:readonly, im:message:readonly, "
        "im:message.p2p_msg:get_as_user, im:message.group_msg:get_as_user, offline_access",
        "浏览器打开 authorize_url 并登录授权",
        "从回调地址栏复制 code，执行: feishu_cli.py auth login --code <CODE>",
    ]
    return success("auth.login_url", info)


def cmd_auth_login(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    creds = load_credentials(getattr(args, "credentials", None))
    if args.user_token:
        creds["user_access_token"] = args.user_token
        creds.pop("expires_at", None)
    elif args.code:
        token_info = exchange_code(
            client, code=args.code, redirect_uri=args.redirect_uri
        )
        creds.update(token_info)
        client.set_user_token(str(token_info["user_access_token"]))
    else:
        raise CliError("请提供 --code 或 --user-token；需要登录链接时用 auth login-url")

    client.set_user_token(str(creds.get("user_access_token") or ""))
    profile = {}
    try:
        profile = _public_user_profile(client.get_user_info())
        creds.update({k: v for k, v in profile.items() if v})
    except FeishuApiError as exc:
        profile = {"warning": str(exc)}
    path = save_credentials(creds, getattr(args, "credentials", None))
    return success(
        "auth.login",
        {
            "saved_to": str(path),
            "user": profile,
            "scope": creds.get("scope"),
            "expires_at": creds.get("expires_at"),
        },
    )


def cmd_auth_whoami(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    if not client.auth_status().get("has_user_access_token"):
        raise CliError("尚未登录，请先 auth login-url / auth login", "missing_user_token")
    payload = client.get_user_info()
    return success("auth.whoami", _public_user_profile(payload))


def cmd_auth_logout(args: argparse.Namespace) -> Dict[str, Any]:
    removed = clear_credentials(getattr(args, "credentials", None))
    return success(
        "auth.logout",
        {
            "removed": removed,
            "credentials_path": str(credential_path(getattr(args, "credentials", None))),
        },
    )


def cmd_auth_token(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    token_info = client.get_tenant_access_token(force_refresh=bool(args.refresh))
    result = {
        "expire": token_info.get("expire"),
        "source": token_info.get("source"),
        "tenant_access_token": token_info.get("tenant_access_token"),
    }
    if args.mask:
        result["tenant_access_token"] = _mask_secret(result.get("tenant_access_token"))
    return success("auth.token", result)


def cmd_bot_info(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    payload = client.bot_info()
    return success("bot.info", payload.get("bot") or payload.get("data") or payload)


def cmd_chat_list(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    payload = client.list_chats(
        page_size=args.page_size,
        page_token=args.page_token,
        sort_type=args.sort_type,
        user_id_type=args.user_id_type,
    )
    return success("chat.list", payload.get("data") or payload)


def cmd_chat_get(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    payload = client.get_chat(args.chat_id, user_id_type=args.user_id_type)
    return success("chat.get", payload.get("data") or payload)


def cmd_chat_members(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    payload = client.list_chat_members(
        args.chat_id,
        page_size=args.page_size,
        page_token=args.page_token,
        member_id_type=args.member_id_type,
    )
    return success("chat.members", payload.get("data") or payload)


def cmd_message_send(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    content = _load_content(args)
    payload = client.send_message(
        receive_id=args.receive_id,
        receive_id_type=args.receive_id_type,
        msg_type=args.msg_type,
        content=content,
        uuid=args.uuid,
    )
    return success("message.send", payload.get("data") or payload)


def cmd_message_reply(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    content = _load_content(args)
    payload = client.reply_message(
        args.message_id,
        msg_type=args.msg_type,
        content=content,
        uuid=args.uuid,
        reply_in_thread=args.reply_in_thread,
    )
    return success("message.reply", payload.get("data") or payload)


def cmd_message_get(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    payload = client.get_message(args.message_id)
    return success("message.get", payload.get("data") or payload)


def cmd_message_list(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    container_id = args.chat_id or args.container_id
    if not container_id:
        raise CliError("请提供 --chat-id 或 --container-id")
    payload = client.list_messages(
        container_id=container_id,
        container_id_type=args.container_id_type,
        start_time=args.start_time,
        end_time=args.end_time,
        page_size=args.page_size,
        page_token=args.page_token,
        sort_type=args.sort_type,
    )
    return success("message.list", payload.get("data") or payload)


def cmd_user_get(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    payload = client.get_user(
        args.user_id,
        user_id_type=args.user_id_type,
        department_id_type=args.department_id_type,
    )
    return success("user.get", payload.get("data") or payload)


def cmd_summary_unread(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    use_user = not bool(getattr(args, "allow_bot", False))
    if use_user and not client.auth_status().get("has_user_access_token"):
        raise CliError(
            "总结未读需要用户登录。请先执行 auth login-url，授权后 auth login --code <CODE>",
            "missing_user_token",
        )
    client.prefer_user_token = use_user

    me_ids = set()
    me_profile: Dict[str, Any] = {}
    if use_user:
        me_profile = _public_user_profile(client.get_user_info())
        if me_profile.get("open_id"):
            me_ids.add(str(me_profile["open_id"]))
        if me_profile.get("union_id"):
            me_ids.add(str(me_profile["union_id"]))
    else:
        bot = client.bot_info()
        bot_data = bot.get("bot") or bot.get("data") or bot
        me_profile = {
            "name": bot_data.get("app_name"),
            "open_id": bot_data.get("open_id"),
            "mode": "bot",
        }
        if bot_data.get("open_id"):
            me_ids.add(str(bot_data["open_id"]))

    collected = collect_unread_window(
        client,
        me_ids=me_ids,
        hours=args.hours,
        max_chats=args.max_chats,
        max_messages_per_chat=args.max_messages_per_chat,
    )
    collected["me"] = me_profile
    collected["identity"] = "user" if use_user else "bot"
    collected["related_count"] = len(collected.get("related") or [])
    collected["others_count"] = len(collected.get("others") or [])
    collected["markdown"] = render_markdown(collected)
    if args.format == "markdown":
        return success("summary.unread", {"markdown": collected["markdown"], "me": me_profile})
    return success("summary.unread", collected)


def cmd_api_call(args: argparse.Namespace) -> Dict[str, Any]:
    client = build_client(args)
    params = _load_json_value(args.params, flag="--params") if args.params else None
    body: Any = None
    if args.body_file:
        text = pathlib.Path(args.body_file).read_text(encoding="utf-8")
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = text
    elif args.body is not None:
        body = _load_json_value(args.body, flag="--body")
    payload = client.request(
        args.method,
        args.path,
        params=params if isinstance(params, Mapping) else None,
        body=body,
        auth=not args.no_auth,
    )
    return success("api.call", payload)


HANDLERS = {
    "version": cmd_version,
    "auth.status": cmd_auth_status,
    "auth.token": cmd_auth_token,
    "auth.login_url": cmd_auth_login_url,
    "auth.login": cmd_auth_login,
    "auth.whoami": cmd_auth_whoami,
    "auth.logout": cmd_auth_logout,
    "summary.unread": cmd_summary_unread,
    "bot.info": cmd_bot_info,
    "chat.list": cmd_chat_list,
    "chat.get": cmd_chat_get,
    "chat.members": cmd_chat_members,
    "message.send": cmd_message_send,
    "message.reply": cmd_message_reply,
    "message.get": cmd_message_get,
    "message.list": cmd_message_list,
    "user.get": cmd_user_get,
    "api.call": cmd_api_call,
}


def add_global_auth_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--app-id", help="覆盖 FEISHU_APP_ID / LARK_APP_ID")
    parser.add_argument("--app-secret", help="覆盖 FEISHU_APP_SECRET / LARK_APP_SECRET")
    parser.add_argument("--tenant-token", help="直接使用 tenant_access_token")
    parser.add_argument("--user-token", help="直接使用 user_access_token")
    parser.add_argument(
        "--use-user-token",
        action="store_true",
        help="优先使用用户访问令牌（默认使用 bot tenant token）",
    )
    parser.add_argument("--base-url", help="覆盖 OpenAPI Base URL")
    parser.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数")
    parser.add_argument("--credentials", help="用户令牌存储路径，默认 ~/.config/feishu-cli/credentials.json")


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="feishu_cli.py",
        description="飞书 / Lark OpenAPI CLI（Bot + 用户登录，支持 24 小时消息总结）",
    )
    add_global_auth_flags(parser)

    common = JsonArgumentParser(add_help=False)
    add_global_auth_flags(common)

    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", parents=[common], help="显示 CLI 版本")
    p_version.set_defaults(action="version")

    auth = sub.add_parser("auth", parents=[common], help="鉴权相关")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    p_auth_status = auth_sub.add_parser(
        "status", parents=[common], help="查看当前凭证配置状态（不泄露密钥）"
    )
    p_auth_status.set_defaults(action="auth.status")
    p_auth_token = auth_sub.add_parser(
        "token", parents=[common], help="获取 tenant_access_token"
    )
    p_auth_token.add_argument("--refresh", action="store_true", help="强制刷新")
    p_auth_token.add_argument(
        "--mask",
        action="store_true",
        help="输出时遮蔽 token",
    )
    p_auth_token.set_defaults(action="auth.token")
    p_login_url = auth_sub.add_parser(
        "login-url", parents=[common], help="生成用户 OAuth 登录链接"
    )
    p_login_url.add_argument("--redirect-uri", default=DEFAULT_REDIRECT_URI)
    p_login_url.add_argument("--scope", help="覆盖默认 OAuth scope")
    p_login_url.set_defaults(action="auth.login_url")
    p_login = auth_sub.add_parser(
        "login", parents=[common], help="用授权码或用户令牌完成登录"
    )
    p_login.add_argument("--code", help="OAuth 回调中的 code")
    p_login.add_argument("--redirect-uri", default=DEFAULT_REDIRECT_URI)
    p_login.set_defaults(action="auth.login")
    p_whoami = auth_sub.add_parser("whoami", parents=[common], help="查看当前登录用户")
    p_whoami.set_defaults(action="auth.whoami")
    p_logout = auth_sub.add_parser("logout", parents=[common], help="清除本地用户令牌")
    p_logout.set_defaults(action="auth.logout")

    summary = sub.add_parser("summary", parents=[common], help="消息总结")
    summary_sub = summary.add_subparsers(dest="summary_command", required=True)
    p_unread = summary_sub.add_parser(
        "unread", parents=[common], help="总结近 N 小时未读/待处理消息"
    )
    p_unread.add_argument("--hours", type=int, default=24)
    p_unread.add_argument("--max-chats", type=int, default=40)
    p_unread.add_argument("--max-messages-per-chat", type=int, default=40)
    p_unread.add_argument("--format", choices=["json", "markdown"], default="json")
    p_unread.add_argument(
        "--allow-bot",
        action="store_true",
        help="无用户登录时退化为总结机器人所在群（不是个人未读）",
    )
    p_unread.set_defaults(action="summary.unread")

    bot = sub.add_parser("bot", parents=[common], help="机器人信息")
    bot_sub = bot.add_subparsers(dest="bot_command", required=True)
    p_bot_info = bot_sub.add_parser(
        "info", parents=[common], help="获取机器人基础信息"
    )
    p_bot_info.set_defaults(action="bot.info")

    chat = sub.add_parser("chat", parents=[common], help="群聊相关")
    chat_sub = chat.add_subparsers(dest="chat_command", required=True)
    p_chat_list = chat_sub.add_parser(
        "list", parents=[common], help="列出机器人所在群"
    )
    p_chat_list.add_argument("--page-size", type=int, default=20)
    p_chat_list.add_argument("--page-token")
    p_chat_list.add_argument("--sort-type")
    p_chat_list.add_argument("--user-id-type", default="open_id")
    p_chat_list.set_defaults(action="chat.list")
    p_chat_get = chat_sub.add_parser("get", parents=[common], help="获取群详情")
    p_chat_get.add_argument("--chat-id", required=True)
    p_chat_get.add_argument("--user-id-type", default="open_id")
    p_chat_get.set_defaults(action="chat.get")
    p_chat_members = chat_sub.add_parser(
        "members", parents=[common], help="获取群成员"
    )
    p_chat_members.add_argument("--chat-id", required=True)
    p_chat_members.add_argument("--page-size", type=int, default=50)
    p_chat_members.add_argument("--page-token")
    p_chat_members.add_argument("--member-id-type", default="open_id")
    p_chat_members.set_defaults(action="chat.members")

    message = sub.add_parser("message", parents=[common], help="消息相关")
    message_sub = message.add_subparsers(dest="message_command", required=True)

    p_send = message_sub.add_parser("send", parents=[common], help="发送消息")
    p_send.add_argument("--receive-id", required=True)
    p_send.add_argument(
        "--receive-id-type",
        required=True,
        choices=["open_id", "user_id", "union_id", "email", "chat_id"],
    )
    p_send.add_argument("--msg-type", default="text")
    p_send.add_argument("--text", help="文本消息内容（msg_type=text）")
    p_send.add_argument("--content", help="消息 content JSON 字符串")
    p_send.add_argument("--content-file", help="从文件读取 content")
    p_send.add_argument("--uuid", help="幂等 uuid")
    p_send.set_defaults(action="message.send")

    p_reply = message_sub.add_parser("reply", parents=[common], help="回复消息")
    p_reply.add_argument("--message-id", required=True)
    p_reply.add_argument("--msg-type", default="text")
    p_reply.add_argument("--text")
    p_reply.add_argument("--content")
    p_reply.add_argument("--content-file")
    p_reply.add_argument("--uuid")
    p_reply.add_argument("--reply-in-thread", action="store_true")
    p_reply.set_defaults(action="message.reply")

    p_get = message_sub.add_parser("get", parents=[common], help="获取单条消息")
    p_get.add_argument("--message-id", required=True)
    p_get.set_defaults(action="message.get")

    p_list = message_sub.add_parser("list", parents=[common], help="拉取会话消息")
    p_list.add_argument("--chat-id", help="群 chat_id（等价 container_id）")
    p_list.add_argument("--container-id")
    p_list.add_argument("--container-id-type", default="chat")
    p_list.add_argument("--start-time", help="秒级时间戳")
    p_list.add_argument("--end-time", help="秒级时间戳")
    p_list.add_argument("--page-size", type=int, default=20)
    p_list.add_argument("--page-token")
    p_list.add_argument("--sort-type")
    p_list.set_defaults(action="message.list")

    user = sub.add_parser("user", parents=[common], help="通讯录用户")
    user_sub = user.add_subparsers(dest="user_command", required=True)
    p_user_get = user_sub.add_parser("get", parents=[common], help="获取用户信息")
    p_user_get.add_argument("--user-id", required=True)
    p_user_get.add_argument("--user-id-type", default="open_id")
    p_user_get.add_argument("--department-id-type")
    p_user_get.set_defaults(action="user.get")

    api = sub.add_parser("api", parents=[common], help="通用 OpenAPI 调用")
    api_sub = api.add_subparsers(dest="api_command", required=True)
    p_call = api_sub.add_parser("call", parents=[common], help="调用任意 path")
    p_call.add_argument("--method", default="GET", help="HTTP 方法")
    p_call.add_argument("--path", required=True, help="如 /im/v1/chats")
    p_call.add_argument("--params", help="query JSON 对象")
    p_call.add_argument("--body", help="JSON body 字符串")
    p_call.add_argument("--body-file", help="从文件读取 body")
    p_call.add_argument("--no-auth", action="store_true", help="不附加 Authorization")
    p_call.set_defaults(action="api.call")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    action = "unknown"
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        action = getattr(args, "action", args.command)
        handler = HANDLERS.get(action)
        if handler is None:
            raise CliError(f"未知命令: {action}", "unknown_command")
        payload = handler(args)
        return emit_json(payload, exit_code=0 if payload.get("success") else 1)
    except CliError as exc:
        return emit_json(failure(action, code=exc.code, message=str(exc)), exit_code=2)
    except FeishuApiError as exc:
        return emit_json(
            failure(
                action,
                code=exc.code or "feishu_api_error",
                message=str(exc),
                response=exc.response,
                retryable=exc.http_status in {408, 429, 500, 502, 503, 504}
                if exc.http_status
                else False,
            ),
            exit_code=1,
        )
    except KeyboardInterrupt:
        return emit_json(
            failure(action, code="interrupted", message="interrupted"),
            exit_code=130,
        )
    except Exception as exc:  # noqa: BLE001 - CLI top-level guard
        return emit_json(
            failure(action, code="internal_error", message=str(exc)),
            exit_code=1,
        )


if __name__ == "__main__":
    raise SystemExit(main())
