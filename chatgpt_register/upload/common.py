"""上传通用逻辑。"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from curl_cffi import requests as curl_requests

if TYPE_CHECKING:
    from chatgpt_register.config.model import UploadConfig


def new_upload_session(proxy: str = ""):
    """创建带代理的上传 HTTP 会话。"""
    session = curl_requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    return session


def upload_token_data(
    email: str,
    token_data: dict,
    filepath: str,
    config: UploadConfig,
    proxy: str = "",
    print_lock: threading.Lock | None = None,
) -> None:
    """根据上传配置分发到各目标。"""
    if not config.targets:
        return

    if "cpa" in config.targets and config.cpa is not None:
        from chatgpt_register.upload.cpa import upload_token_json_to_cpa
        upload_token_json_to_cpa(filepath, config.cpa, proxy=proxy, print_lock=print_lock)

    if "sub2api" in config.targets and config.sub2api is not None:
        from chatgpt_register.upload.sub2api import upload_token_to_sub2api
        upload_token_to_sub2api(email=email, token_data=token_data, config=config.sub2api, proxy=proxy, print_lock=print_lock)
