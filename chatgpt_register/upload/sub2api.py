"""Sub2API 上传 + 分组管理。"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

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


def prepare_sub2api_group_binding(
    config: Sub2ApiConfig,
    interactive: bool = True,
    selected_group_id: Optional[int] = None,
    auto_select_first: bool = False,
    proxy: str = "",
) -> tuple[bool, list[int]]:
    """准备 Sub2API 分组绑定，返回 (成功, group_ids)。

    与旧版不同，此函数不修改全局变量，而是返回选中的 group_ids。
    """
    api_base = config.api_base
    if not api_base:
        if interactive:
            api_base = input("Sub2API 地址 (例如 https://sub2api.example.com): ").strip().rstrip("/")
        else:
            print("未设置 sub2api_api_base，无法继续 Sub2API 上传")
            return False, []
    if not api_base:
        print("未设置 Sub2API 地址，无法继续 Sub2API 上传")
        return False, []

    admin_key = config.admin_api_key
    bearer = config.bearer_token
    if not admin_key and not bearer:
        if interactive:
            key = input("Sub2API Admin API Key (推荐，留空则输入 Bearer Token): ").strip()
            if key:
                admin_key = key
            else:
                bearer = input("Sub2API Bearer Token: ").strip()
        else:
            print("未设置 sub2api_admin_api_key 或 sub2api_bearer_token，无法继续 Sub2API 上传")
            return False, []

    if not admin_key and not bearer:
        print("未设置 Sub2API 凭证，无法继续 Sub2API 上传")
        return False, []

    # 创建临时 config 用于 API 调用（可能含交互输入的值）
    temp_config = config.model_copy(update={
        "api_base": api_base,
        "admin_api_key": admin_key,
        "bearer_token": bearer,
    })

    print("[Sub2API] 正在获取 openai 分组...")
    try:
        groups = fetch_sub2api_openai_groups(temp_config, proxy=proxy)
    except Exception as e:
        print(f"{e}")
        return False, []

    if not groups:
        print("Sub2API 中未找到 openai 平台分组。请先在管理后台新建分组后重试。")
        return False, []

    selected = None
    if selected_group_id is None and config.group_ids:
        try:
            selected_group_id = int(config.group_ids[0])
        except Exception:
            selected_group_id = None

    if selected_group_id is not None:
        for group in groups:
            if group["id"] == selected_group_id:
                selected = group
                break
        if not selected:
            print(f"指定的 Sub2API 分组不存在或非 openai 平台: id={selected_group_id}")
            return False, []

    if selected is None and not interactive:
        if auto_select_first:
            selected = groups[0]
        else:
            print("非交互模式下请提供 --sub2api-group-id，或使用 --sub2api-auto-select-first-group")
            return False, []

    if selected is None:
        # 交互选择
        import sys
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print("当前环境不是可交互终端")
            return False, []

        try:
            import questionary
        except Exception:
            print("缺少依赖 questionary")
            return False, []

        tui_choices = []
        for group in groups:
            status = group.get("status") or "-"
            title = f"{group['name']} (ID={group['id']}, status={status})"
            tui_choices.append(questionary.Choice(title=title, value=group["id"]))

        selected_group_id = questionary.select(
            "选择 Sub2API openai 分组（上下选择，Enter 确认）",
            choices=tui_choices,
            default=groups[0]["id"],
            qmark=">",
            pointer="->",
        ).ask()
        if selected_group_id is None:
            raise KeyboardInterrupt
        for group in groups:
            if group["id"] == selected_group_id:
                selected = group
                break

    if selected is None:
        raise RuntimeError("分组选择失败。")

    print(f"[Sub2API] 已选择分组: {selected['name']} (ID={selected['id']})")
    return True, [selected["id"]]
