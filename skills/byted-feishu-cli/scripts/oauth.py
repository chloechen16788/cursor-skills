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
"""Feishu user OAuth helpers (Device Flow first, no redirect URL required)."""

from __future__ import annotations

import base64
import json
import secrets
import time
from typing import Any, Dict, Optional
from urllib import error, parse, request

from client import FeishuApiError, FeishuClient, resolve_base_url

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/callback"
DEFAULT_SCOPES = (
    "offline_access "
    "im:chat:read "
    "im:message:readonly "
    "im:message.p2p_msg:get_as_user "
    "im:message.group_msg:get_as_user "
    "contact:user.base:readonly"
)
AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
DEVICE_AUTHORIZATION_URL = "https://accounts.feishu.cn/oauth/v1/device_authorization"
TOKEN_PATH = "/authen/v2/oauth/token"
DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


def build_authorize_url(
    *,
    app_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scope: str = DEFAULT_SCOPES,
    state: Optional[str] = None,
) -> Dict[str, str]:
    state = state or secrets.token_urlsafe(16)
    query = parse.urlencode(
        {
            "client_id": app_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "prompt": "consent",
        }
    )
    return {
        "authorize_url": f"{AUTHORIZE_URL}?{query}",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }


def _token_endpoint(base_url: Optional[str] = None) -> str:
    return f"{resolve_base_url(base_url)}{TOKEN_PATH}"


def _form_post(
    url: str,
    fields: Dict[str, str],
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    data = parse.urlencode(fields).encode("utf-8")
    req_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "byted-feishu-cli/1.1",
    }
    if headers:
        req_headers.update(headers)
    req = request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
    except error.URLError as exc:
        raise FeishuApiError(f"网络错误: {exc.reason}", code="network_error") from exc
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise FeishuApiError(f"响应不是合法 JSON: {raw[:200]}", code="invalid_json") from exc
    return payload if isinstance(payload, dict) else {"data": payload}


def _basic_auth(app_id: str, app_secret: str) -> str:
    token = base64.b64encode(f"{app_id}:{app_secret}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def start_device_login(
    client: FeishuClient,
    *,
    scope: str = DEFAULT_SCOPES,
) -> Dict[str, Any]:
    if not client.app_id or not client.app_secret:
        raise FeishuApiError(
            "Device Flow 登录需要 FEISHU_APP_ID 与 FEISHU_APP_SECRET",
            code="missing_credentials",
        )
    scopes = scope.strip()
    if "offline_access" not in scopes.split():
        scopes = f"{scopes} offline_access".strip()
    payload = _form_post(
        DEVICE_AUTHORIZATION_URL,
        {"client_id": client.app_id, "scope": scopes},
        headers={"Authorization": _basic_auth(client.app_id, client.app_secret)},
    )
    if payload.get("error") or not payload.get("device_code"):
        raise FeishuApiError(
            str(payload.get("error_description") or payload.get("error") or "发起 Device Flow 失败"),
            code=payload.get("error") or payload.get("code") or "device_auth_error",
            response=payload,
        )
    verification = (
        payload.get("verification_uri_complete")
        or payload.get("verification_uri")
        or ""
    )
    return {
        "device_code": payload.get("device_code"),
        "user_code": payload.get("user_code"),
        "verification_uri": payload.get("verification_uri"),
        "verification_uri_complete": verification,
        "expires_in": int(payload.get("expires_in") or 600),
        "interval": int(payload.get("interval") or 5),
        "scope": scopes,
    }


def poll_device_token(
    client: FeishuClient,
    *,
    device_code: str,
    interval: int = 5,
    expires_in: int = 600,
    wait: bool = True,
    max_wait_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    if not client.app_id or not client.app_secret:
        raise FeishuApiError(
            "轮询用户令牌需要 FEISHU_APP_ID 与 FEISHU_APP_SECRET",
            code="missing_credentials",
        )
    interval = max(1, int(interval or 5))
    deadline = time.time() + int(max_wait_seconds or expires_in or 600)
    token_url = _token_endpoint(client.base_url)
    last_error = "authorization_pending"
    while True:
        payload = _form_post(
            token_url,
            {
                "grant_type": DEVICE_GRANT_TYPE,
                "device_code": device_code,
                "client_id": client.app_id,
                "client_secret": client.app_secret,
            },
        )
        if payload.get("access_token") or payload.get("user_access_token"):
            return _normalize_token_payload(payload)
        err = str(payload.get("error") or "")
        last_error = err or str(payload.get("error_description") or "unknown")
        if err in {"authorization_pending", "slow_down"}:
            if err == "slow_down":
                interval = min(interval + 5, 60)
            if not wait or time.time() + interval >= deadline:
                raise FeishuApiError(
                    "用户尚未完成飞书授权，请打开验证链接确认后重试 auth login --device-code",
                    code="authorization_pending",
                    response={"error": last_error or "authorization_pending", "device_code": device_code},
                )
            time.sleep(interval)
            continue
        if err in {"access_denied", "expired_token", "invalid_grant"}:
            raise FeishuApiError(
                str(payload.get("error_description") or err),
                code=err,
                response=payload,
            )
        raise FeishuApiError(
            str(payload.get("error_description") or payload.get("msg") or last_error),
            code=err or payload.get("code") or "oauth_error",
            response=payload,
        )


def exchange_code(
    client: FeishuClient,
    *,
    code: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
) -> Dict[str, Any]:
    if not client.app_id or not client.app_secret:
        raise FeishuApiError(
            "换取用户令牌需要 FEISHU_APP_ID 与 FEISHU_APP_SECRET",
            code="missing_credentials",
        )
    payload = client.request(
        "POST",
        _token_endpoint(client.base_url),
        body={
            "grant_type": "authorization_code",
            "client_id": client.app_id,
            "client_secret": client.app_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        auth=False,
    )
    return _normalize_token_payload(payload)


def refresh_user_token(client: FeishuClient, refresh_token: str) -> Dict[str, Any]:
    if not client.app_id or not client.app_secret:
        raise FeishuApiError(
            "刷新用户令牌需要 FEISHU_APP_ID 与 FEISHU_APP_SECRET",
            code="missing_credentials",
        )
    payload = client.request(
        "POST",
        _token_endpoint(client.base_url),
        body={
            "grant_type": "refresh_token",
            "client_id": client.app_id,
            "client_secret": client.app_secret,
            "refresh_token": refresh_token,
        },
        auth=False,
    )
    return _normalize_token_payload(payload)


def _normalize_token_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    access = payload.get("access_token") or payload.get("user_access_token")
    if not access:
        raise FeishuApiError(
            payload.get("error_description") or payload.get("msg") or "换取 user_access_token 失败",
            code=payload.get("code") or payload.get("error") or "oauth_error",
            response=payload,
        )
    expires_in = int(payload.get("expires_in") or 7200)
    now = int(time.time())
    return {
        "user_access_token": access,
        "refresh_token": payload.get("refresh_token"),
        "expires_in": expires_in,
        "expires_at": now + expires_in,
        "scope": payload.get("scope"),
        "token_type": payload.get("token_type") or "Bearer",
    }
