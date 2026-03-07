"""CPA 上传逻辑。"""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatgpt_register.config.model import CpaConfig


def upload_token_json_to_cpa(
    filepath: str,
    cpa_config: CpaConfig,
    proxy: str = "",
    print_lock: threading.Lock | None = None,
) -> None:
    """上传 Token JSON 文件到 CPA 管理平台。"""
    if not cpa_config.api_url:
        return
    if not cpa_config.api_token:
        if print_lock:
            with print_lock:
                print("  [CPA] upload_api_token 未设置，跳过上传")
        return

    from chatgpt_register.upload.common import new_upload_session

    mp = None
    try:
        from curl_cffi import CurlMime

        filename = os.path.basename(filepath)
        mp = CurlMime()
        mp.addpart(
            name="file",
            content_type="application/json",
            filename=filename,
            local_path=filepath,
        )

        session = new_upload_session(proxy)

        resp = session.post(
            cpa_config.api_url,
            multipart=mp,
            headers={"Authorization": f"Bearer {cpa_config.api_token}"},
            verify=False,
            timeout=30,
        )

        if 200 <= resp.status_code < 300:
            if print_lock:
                with print_lock:
                    print("  [CPA] Token JSON 已上传到 CPA 管理平台")
        else:
            if print_lock:
                with print_lock:
                    print(f"  [CPA] 上传失败: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        if print_lock:
            with print_lock:
                print(f"  [CPA] 上传异常: {e}")
    finally:
        if mp:
            mp.close()
