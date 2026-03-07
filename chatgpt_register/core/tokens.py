"""Token 保存 — 将 OAuth tokens 写入文件并触发上传。"""

from __future__ import annotations

import json
import os
import threading
from typing import TYPE_CHECKING, Callable

from chatgpt_register.core.utils import decode_jwt_payload

if TYPE_CHECKING:
    pass


def save_codex_tokens(
    email: str,
    tokens: dict,
    *,
    ak_file: str,
    rk_file: str,
    token_json_dir: str,
    upload_fn: Callable[[str, dict, str], None] | None = None,
    file_lock: threading.Lock,
    print_lock: threading.Lock,
) -> None:
    """保存 Codex tokens 到文件，并可选触发上传。

    Args:
        email: 注册邮箱
        tokens: OAuth token 响应 dict
        ak_file: access_token 追加目标文件
        rk_file: refresh_token 追加目标文件
        token_json_dir: token JSON 文件输出目录
        upload_fn: 可选的上传回调 (email, token_data, filepath)
        file_lock: 文件写入锁
        print_lock: 打印锁
    """
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    id_token = tokens.get("id_token", "")

    if access_token:
        with file_lock:
            with open(ak_file, "a", encoding="utf-8") as f:
                f.write(f"{access_token}\n")

    if refresh_token:
        with file_lock:
            with open(rk_file, "a", encoding="utf-8") as f:
                f.write(f"{refresh_token}\n")

    if not access_token:
        return

    payload = decode_jwt_payload(access_token)
    auth_info = payload.get("https://api.openai.com/auth", {})
    account_id = auth_info.get("chatgpt_account_id", "")

    exp_timestamp = payload.get("exp")
    expired_str = ""
    if isinstance(exp_timestamp, int) and exp_timestamp > 0:
        from datetime import datetime, timedelta, timezone

        exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone(timedelta(hours=8)))
        expired_str = exp_dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    from datetime import datetime, timedelta, timezone

    now = datetime.now(tz=timezone(timedelta(hours=8)))
    token_data = {
        "type": "codex",
        "email": email,
        "expired": expired_str,
        "id_token": id_token,
        "account_id": account_id,
        "access_token": access_token,
        "last_refresh": now.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "refresh_token": refresh_token,
    }

    token_dir = token_json_dir if os.path.isabs(token_json_dir) else os.path.join(os.getcwd(), token_json_dir)
    os.makedirs(token_dir, exist_ok=True)

    token_path = os.path.join(token_dir, f"{email}.json")
    with file_lock:
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, ensure_ascii=False)

    if upload_fn is not None:
        upload_fn(email, token_data, token_path)
