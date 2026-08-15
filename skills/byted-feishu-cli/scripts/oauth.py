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
"""Feishu user OAuth helpers."""

from __future__ import annotations

import secrets
import time
from typing import Any, Dict, Optional
from urllib import parse

from client import FeishuApiError, FeishuClient, resolve_base_url

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/callback"
DEFAULT_SCOPES = (
    "offline_access "
    "im:chat:readonly "
    "im:message:readonly "
    "im:message.p2p_msg:get_as_user "
    "im:message.group_msg:get_as_user "
    "auth:user.id:read"
)
AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
TOKEN_PATH = "/authen/v2/oauth/token"


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
