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
"""Local credential store for Feishu user tokens. Never commit this file."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_RELATIVE = Path(".config") / "feishu-cli" / "credentials.json"


def credential_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.getenv("FEISHU_CLI_CREDENTIALS")
    if env:
        return Path(env).expanduser()
    return Path.home() / DEFAULT_RELATIVE


def load_credentials(path: Optional[str] = None) -> Dict[str, Any]:
    target = credential_path(path)
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_credentials(data: Dict[str, Any], path: Optional[str] = None) -> Path:
    target = credential_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["updated_at"] = int(time.time())
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def clear_credentials(path: Optional[str] = None) -> bool:
    target = credential_path(path)
    if not target.exists():
        return False
    target.unlink()
    return True


def token_expired(data: Dict[str, Any], *, skew_seconds: int = 60) -> bool:
    expires_at = data.get("expires_at")
    if not expires_at:
        return False
    try:
        return time.time() >= float(expires_at) - skew_seconds
    except (TypeError, ValueError):
        return False
