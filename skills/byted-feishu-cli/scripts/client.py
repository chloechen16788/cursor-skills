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
"""Feishu / Lark OpenAPI HTTP client."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Mapping, MutableMapping, Optional, Union
from urllib import error, parse, request

Params = Mapping[str, Any]
JsonBody = Union[Mapping[str, Any], list, str, bytes, None]

FEISHU_OPEN_API = "https://open.feishu.cn/open-apis"
LARK_OPEN_API = "https://open.larksuite.com/open-apis"
DEFAULT_TIMEOUT = 30.0

APP_ID_ENVS = ("FEISHU_APP_ID", "LARK_APP_ID")
APP_SECRET_ENVS = ("FEISHU_APP_SECRET", "LARK_APP_SECRET")
TENANT_TOKEN_ENVS = (
    "FEISHU_TENANT_ACCESS_TOKEN",
    "LARK_TENANT_ACCESS_TOKEN",
    "FEISHU_TENANT_TOKEN",
)
USER_TOKEN_ENVS = ("LARK_USER_ACCESS_TOKEN", "FEISHU_USER_ACCESS_TOKEN")


class FeishuApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: Optional[Union[int, str]] = None,
        http_status: Optional[int] = None,
        response: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.response = response


def _first_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def resolve_base_url(base_url: Optional[str] = None) -> str:
    if base_url:
        return base_url.rstrip("/")
    explicit = _first_env("FEISHU_BASE_URL", "LARK_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    domain = (_first_env("FEISHU_DOMAIN", "LARK_DOMAIN") or "feishu").lower()
    if domain in {"lark", "larksuite", "international"}:
        return LARK_OPEN_API
    return FEISHU_OPEN_API


class FeishuClient:
    """Minimal Feishu OpenAPI client with tenant/user token support."""

    def __init__(
        self,
        *,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        tenant_access_token: Optional[str] = None,
        user_access_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        prefer_user_token: bool = False,
    ) -> None:
        self.app_id = app_id or _first_env(*APP_ID_ENVS)
        self.app_secret = app_secret or _first_env(*APP_SECRET_ENVS)
        self._tenant_token_override = tenant_access_token or _first_env(*TENANT_TOKEN_ENVS)
        self._user_token = user_access_token or _first_env(*USER_TOKEN_ENVS)
        self.base_url = resolve_base_url(base_url)
        self.timeout = timeout
        self.prefer_user_token = prefer_user_token
        self._cached_tenant_token: Optional[str] = None
        self._cached_tenant_expire_at: float = 0.0

    def auth_status(self) -> Dict[str, Any]:
        return {
            "base_url": self.base_url,
            "has_app_id": bool(self.app_id),
            "has_app_secret": bool(self.app_secret),
            "has_tenant_access_token": bool(
                self._tenant_token_override or self._cached_tenant_token
            ),
            "has_user_access_token": bool(self._user_token),
            "prefer_user_token": self.prefer_user_token,
        }

    def get_tenant_access_token(self, *, force_refresh: bool = False) -> Dict[str, Any]:
        if self._tenant_token_override and not force_refresh:
            return {
                "tenant_access_token": self._tenant_token_override,
                "expire": None,
                "source": "env_or_override",
            }

        now = time.time()
        if (
            not force_refresh
            and self._cached_tenant_token
            and now < self._cached_tenant_expire_at - 60
        ):
            return {
                "tenant_access_token": self._cached_tenant_token,
                "expire": max(0, int(self._cached_tenant_expire_at - now)),
                "source": "cache",
            }

        if not self.app_id or not self.app_secret:
            raise FeishuApiError(
                "缺少 Bot 凭证：请设置 FEISHU_APP_ID / FEISHU_APP_SECRET"
                "（或 LARK_APP_ID / LARK_APP_SECRET），"
                "或直接提供 FEISHU_TENANT_ACCESS_TOKEN",
                code="missing_credentials",
            )

        payload = self.request(
            "POST",
            "/auth/v3/tenant_access_token/internal",
            body={"app_id": self.app_id, "app_secret": self.app_secret},
            auth=False,
        )
        token = payload.get("tenant_access_token")
        expire = int(payload.get("expire") or 0)
        if not token:
            raise FeishuApiError(
                "获取 tenant_access_token 失败：响应缺少 token",
                code=payload.get("code"),
                response=payload,
            )
        self._cached_tenant_token = str(token)
        self._cached_tenant_expire_at = time.time() + expire
        return {
            "tenant_access_token": self._cached_tenant_token,
            "expire": expire,
            "source": "app_credentials",
        }

    def _access_token(self) -> str:
        if self.prefer_user_token:
            if not self._user_token:
                raise FeishuApiError(
                    "已指定使用用户令牌，但未设置 LARK_USER_ACCESS_TOKEN / FEISHU_USER_ACCESS_TOKEN",
                    code="missing_user_token",
                )
            return self._user_token

        token_info = self.get_tenant_access_token()
        return str(token_info["tenant_access_token"])

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Params] = None,
        body: JsonBody = None,
        headers: Optional[Mapping[str, str]] = None,
        auth: bool = True,
        content_type: Optional[str] = "application/json; charset=utf-8",
    ) -> Dict[str, Any]:
        url = path if path.startswith("http://") or path.startswith("https://") else (
            f"{self.base_url}/{path.lstrip('/')}"
        )
        if params:
            query = parse.urlencode(
                {k: v for k, v in params.items() if v is not None},
                doseq=True,
            )
            url = f"{url}?{query}" if query else url

        req_headers: MutableMapping[str, str] = {"User-Agent": "byted-feishu-cli/1.0"}
        if headers:
            req_headers.update(headers)
        if auth:
            req_headers["Authorization"] = f"Bearer {self._access_token()}"

        data: Optional[bytes] = None
        if body is not None:
            if isinstance(body, (bytes, bytearray)):
                data = bytes(body)
            elif isinstance(body, str):
                data = body.encode("utf-8")
            else:
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            if content_type and "Content-Type" not in req_headers:
                req_headers["Content-Type"] = content_type

        req = request.Request(url, data=data, headers=req_headers, method=method.upper())
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                http_status = getattr(resp, "status", None) or resp.getcode()
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            http_status = exc.code
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw}
            raise FeishuApiError(
                f"HTTP {http_status}: {payload.get('msg') or payload.get('message') or raw}",
                code=payload.get("code"),
                http_status=http_status,
                response=payload,
            ) from exc
        except error.URLError as exc:
            raise FeishuApiError(f"网络错误: {exc.reason}", code="network_error") from exc

        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise FeishuApiError(
                f"响应不是合法 JSON: {raw[:200]}",
                code="invalid_json",
                http_status=http_status,
                response=raw,
            ) from exc

        if isinstance(payload, dict) and payload.get("code") not in (None, 0, "0"):
            raise FeishuApiError(
                str(payload.get("msg") or payload.get("message") or "飞书 API 返回错误"),
                code=payload.get("code"),
                http_status=http_status,
                response=payload,
            )
        if not isinstance(payload, dict):
            return {"data": payload}
        return payload

    # ---- convenience wrappers -------------------------------------------------

    def bot_info(self) -> Dict[str, Any]:
        return self.request("GET", "/bot/v3/info")

    def list_chats(
        self,
        *,
        page_size: int = 20,
        page_token: Optional[str] = None,
        sort_type: Optional[str] = None,
        user_id_type: str = "open_id",
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "page_size": page_size,
            "user_id_type": user_id_type,
        }
        if page_token:
            params["page_token"] = page_token
        if sort_type:
            params["sort_type"] = sort_type
        return self.request("GET", "/im/v1/chats", params=params)

    def get_chat(self, chat_id: str, *, user_id_type: str = "open_id") -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/im/v1/chats/{parse.quote(chat_id)}",
            params={"user_id_type": user_id_type},
        )

    def list_chat_members(
        self,
        chat_id: str,
        *,
        page_size: int = 50,
        page_token: Optional[str] = None,
        member_id_type: str = "open_id",
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "page_size": page_size,
            "member_id_type": member_id_type,
        }
        if page_token:
            params["page_token"] = page_token
        return self.request(
            "GET",
            f"/im/v1/chats/{parse.quote(chat_id)}/members",
            params=params,
        )

    def send_message(
        self,
        *,
        receive_id: str,
        receive_id_type: str,
        msg_type: str,
        content: Union[str, Mapping[str, Any]],
        uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        if isinstance(content, Mapping):
            content_str = json.dumps(content, ensure_ascii=False)
        else:
            content_str = content
        body: Dict[str, Any] = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content_str,
        }
        if uuid:
            body["uuid"] = uuid
        return self.request(
            "POST",
            "/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            body=body,
        )

    def reply_message(
        self,
        message_id: str,
        *,
        msg_type: str,
        content: Union[str, Mapping[str, Any]],
        uuid: Optional[str] = None,
        reply_in_thread: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if isinstance(content, Mapping):
            content_str = json.dumps(content, ensure_ascii=False)
        else:
            content_str = content
        body: Dict[str, Any] = {
            "msg_type": msg_type,
            "content": content_str,
        }
        if uuid:
            body["uuid"] = uuid
        if reply_in_thread is not None:
            body["reply_in_thread"] = reply_in_thread
        return self.request(
            "POST",
            f"/im/v1/messages/{parse.quote(message_id)}/reply",
            body=body,
        )

    def get_message(self, message_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/im/v1/messages/{parse.quote(message_id)}")

    def list_messages(
        self,
        *,
        container_id: str,
        container_id_type: str = "chat",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page_size: int = 20,
        page_token: Optional[str] = None,
        sort_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "container_id_type": container_id_type,
            "container_id": container_id,
            "page_size": page_size,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if page_token:
            params["page_token"] = page_token
        if sort_type:
            params["sort_type"] = sort_type
        return self.request("GET", "/im/v1/messages", params=params)

    def get_user(
        self,
        user_id: str,
        *,
        user_id_type: str = "open_id",
        department_id_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"user_id_type": user_id_type}
        if department_id_type:
            params["department_id_type"] = department_id_type
        return self.request(
            "GET",
            f"/contact/v3/users/{parse.quote(user_id)}",
            params=params,
        )

    def get_user_info(self) -> Dict[str, Any]:
        if not self._user_token:
            raise FeishuApiError(
                "获取当前用户信息需要 user_access_token，请先执行 auth login",
                code="missing_user_token",
            )
        previous = self.prefer_user_token
        self.prefer_user_token = True
        try:
            return self.request("GET", "/authen/v1/user_info")
        finally:
            self.prefer_user_token = previous

    def set_user_token(self, token: Optional[str]) -> None:
        self._user_token = token
