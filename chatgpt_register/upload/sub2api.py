"""Sub2API 上传 + 分组管理。"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatgpt_register.config.model import Sub2ApiConfig


def sub2api_auth_headers(config: Sub2ApiConfig) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if config.admin_api_key:
        headers["x-api-key"] = config.admin_api_key
    elif config.bearer_token:
        headers["Authorization"] = f"Bearer {config.bearer_token}"
    return headers


def fetch_sub2api_openai_groups(config: Sub2ApiConfig, proxy: str = "") -> list[dict]:
    """获取 Sub2API 中 openai 平台的分组列表。"""
    from chatgpt_register.upload.common import new_upload_session

    if not config.api_base:
        raise Exception("sub2api_api_base 未设置")
    if not config.admin_api_key and not config.bearer_token:
        raise Exception("未设置 sub2api_admin_api_key 或 sub2api_bearer_token")

    api_base = config.api_base.rstrip("/")
    session = new_upload_session(proxy)
    groups: list[dict] = []
    page = 1
    page_size = 100

    while True:
        resp = session.get(
            f"{api_base}/api/v1/admin/groups",
            params={"platform": "openai", "page": page, "page_size": page_size},
            headers=sub2api_auth_headers(config),
            verify=False,
            timeout=30,
        )
        if resp.status_code != 200:
            raise Exception(f"获取分组失败: {resp.status_code} - {resp.text[:200]}")

        body = {}
        try:
            body = resp.json() or {}
        except Exception:
            raise Exception("获取分组失败: 响应不是 JSON")

        data = body.get("data") or {}
        items = data.get("items") or []
        for item in items:
            if str(item.get("platform", "")).lower() != "openai":
                continue
            gid = item.get("id")
            try:
                gid = int(gid)
            except Exception:
                continue
            groups.append({
                "id": gid,
                "name": str(item.get("name") or f"group-{gid}"),
                "status": str(item.get("status") or ""),
            })

        pages = data.get("pages")
        current_page = data.get("page", page)
        if isinstance(pages, int) and pages > 0 and current_page >= pages:
            break
        if len(items) < page_size:
            break
        page += 1

    # 去重（按 ID）
    unique: dict[int, dict] = {}
    for group in groups:
        unique[group["id"]] = group
    return list(unique.values())


def upload_token_to_sub2api(
    email: str,
    token_data: dict,
    config: Sub2ApiConfig,
    proxy: str = "",
    print_lock: threading.Lock | None = None,
) -> None:
    """上传 OAuth 账号到 Sub2API。"""
    from chatgpt_register.upload.common import new_upload_session

    api_base = config.api_base.rstrip("/")
    if not api_base:
        return
    if not config.admin_api_key and not config.bearer_token:
        if print_lock:
            with print_lock:
                print("  [Sub2API] 未设置 sub2api_admin_api_key 或 sub2api_bearer_token，跳过上传")
        return

    access_token = token_data.get("access_token") or ""
    if not access_token:
        if print_lock:
            with print_lock:
                print("  [Sub2API] 缺少 access_token，跳过上传")
        return

    credentials = {
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token") or "",
        "id_token": token_data.get("id_token") or "",
        "email": email,
        "chatgpt_account_id": token_data.get("account_id") or "",
        "expires_at": token_data.get("expired") or "",
    }
    credentials = {k: v for k, v in credentials.items() if v not in (None, "")}

    payload = {
        "name": email,
        "platform": "openai",
        "type": "oauth",
        "credentials": credentials,
        "concurrency": config.account_concurrency,
        "priority": config.account_priority,
    }
    if config.group_ids:
        payload["group_ids"] = config.group_ids

    headers = sub2api_auth_headers(config)
    headers["Content-Type"] = "application/json"

    session = new_upload_session(proxy)
    endpoint = f"{api_base}/api/v1/admin/accounts"
    try:
        resp = session.post(
            endpoint,
            json=payload,
            headers=headers,
            verify=False,
            timeout=30,
        )
        if 200 <= resp.status_code < 300:
            if print_lock:
                with print_lock:
                    print("  [Sub2API] OAuth 账号已创建")
        else:
            if print_lock:
                with print_lock:
                    print(f"  [Sub2API] 上传失败: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        if print_lock:
            with print_lock:
                print(f"  [Sub2API] 上传异常: {e}")


def validate_sub2api_group_binding(
    config: Sub2ApiConfig,
) -> tuple[bool, list[int], str | None]:
    """校验运行阶段的 Sub2API 绑定是否完整。"""
    api_base = config.api_base.strip().rstrip("/")
    if not api_base:
        return False, [], "Sub2API 配置缺少 `api_base`。"

    admin_key = config.admin_api_key.strip()
    bearer = config.bearer_token.strip()
    if not admin_key and not bearer:
        return False, [], "Sub2API 配置缺少凭证；请补齐 `admin_api_key` 或 `bearer_token`。"

    if not config.group_ids:
        return False, [], "Sub2API 配置缺少 `group_ids`；请回到向导重新选择 openai 分组。"

    normalized_group_ids: list[int] = []
    for group_id in config.group_ids:
        try:
            normalized = int(group_id)
        except (TypeError, ValueError):
            return False, [], "Sub2API `group_ids` 必须全部为整数。"
        if normalized <= 0:
            return False, [], "Sub2API `group_ids` 必须全部大于 0。"
        normalized_group_ids.append(normalized)

    return True, normalized_group_ids, None


def prepare_sub2api_group_binding(
    config: Sub2ApiConfig,
) -> tuple[bool, list[int]]:
    """运行阶段 Sub2API 分组绑定校验。"""
    ok, group_ids, error = validate_sub2api_group_binding(config)
    if not ok:
        print(error or "Sub2API 分组绑定校验失败。")
        return False, []
    return True, group_ids
