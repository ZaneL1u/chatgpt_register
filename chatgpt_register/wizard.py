"""简洁问答式配置向导（questionary 实现）。"""

from __future__ import annotations

from typing import Any

import questionary
from rich.console import Console

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.config.profile import ProfileManager

console = Console()


def run_wizard(profile_manager: ProfileManager) -> RegisterConfig | None:
    """运行交互式配置向导。"""
    console.print("\n[bold cyan]ChatGPT 批量注册工具配置向导[/bold cyan]\n")

    # 1. 选择操作模式
    profiles = profile_manager.list_profile_summaries()

    if profiles:
        choices = [
            "新建配置",
            "使用已保存的配置",
            "从已有配置派生",
        ]
    else:
        choices = ["新建配置"]

    action = questionary.select(
        "选择操作",
        choices=choices,
        default=choices[0],
    ).ask()

    if action is None:  # 用户取消
        return None

    if action == "使用已保存的配置":
        return _select_and_run(profile_manager, profiles)
    elif action == "从已有配置派生":
        return _derive_profile(profile_manager, profiles)

    # 新建配置流程
    return _create_new_config(profile_manager)


def _select_and_run(
    profile_manager: ProfileManager,
    profiles: list,
) -> RegisterConfig | None:
    """选择并运行已有 profile。"""
    choices = [
        f"{p.name} ({p.email_provider}, {','.join(p.upload_targets) or 'none'}, {p.total_accounts}账号)"
        for p in profiles
    ]

    selected = questionary.select(
        "选择 Profile",
        choices=choices,
    ).ask()

    if selected is None:
        return None

    # 提取 profile 名称
    profile_name = selected.split(" (")[0]
    config = profile_manager.load(profile_name)
    console.print(f"\n[green]✓[/green] 已加载 profile: {profile_name}\n")
    return config


def _derive_profile(
    profile_manager: ProfileManager,
    profiles: list,
) -> RegisterConfig | None:
    """从已有 profile 派生新配置。"""
    choices = [p.name for p in profiles]

    source_name = questionary.select(
        "选择要派生的 Profile",
        choices=choices,
    ).ask()

    if source_name is None:
        return None

    # 加载配置并重新走配置流程
    source_config = profile_manager.load(source_name)
    config_dict = source_config.model_dump(mode="json")

    console.print(f"\n[cyan]从 {source_name} 派生配置，可修改任意字段[/cyan]\n")

    return _create_new_config(profile_manager, prefill=config_dict)


def _create_new_config(
    profile_manager: ProfileManager,
    prefill: dict[str, Any] | None = None,
) -> RegisterConfig | None:
    """创建新配置。"""
    prefill = prefill or {}

    # 2. 邮箱配置
    email_config = _ask_email_config(prefill.get("email", {}))
    if email_config is None:
        return None

    # 3. 注册参数
    reg_config = _ask_registration_config(prefill.get("registration", {}))
    if reg_config is None:
        return None

    # 4. 上传配置
    upload_config = _ask_upload_config(prefill.get("upload", {}), reg_config.get("proxy", ""))
    if upload_config is None:
        return None

    # 5. OAuth 配置（使用默认值）
    oauth_config = prefill.get("oauth", {
        "enabled": True,
        "required": True,
        "issuer": "https://auth.openai.com",
        "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
        "redirect_uri": "http://localhost:1455/auth/callback",
    })

    # 6. 构建配置
    config_dict = {
        "email": email_config,
        "registration": reg_config,
        "upload": upload_config,
        "oauth": oauth_config,
    }

    try:
        config = RegisterConfig.model_validate(config_dict)
    except Exception as e:
        console.print(f"\n[red]配置验证失败: {e}[/red]\n")
        return None

    # 7. 保存?
    should_save = questionary.confirm(
        "保存为 profile?",
        default=True,
    ).ask()

    if should_save:
        profile_name = questionary.text(
            "Profile 名称",
            default=prefill.get("_profile_name", ""),
        ).ask()

        if profile_name:
            profile_manager.save(profile_name.strip(), config)
            console.print(f"\n[green]✓[/green] 配置已保存到 profile: {profile_name}\n")

    return config


def _ask_email_config(prefill: dict[str, Any]) -> dict[str, Any] | None:
    """询问邮箱配置。"""
    provider = questionary.select(
        "邮箱平台",
        choices=["DuckMail", "Mailcow", "Mail.tm"],
        default=_provider_display_name(prefill.get("provider", "mailtm")),
    ).ask()

    if provider is None:
        return None

    provider_key = provider.lower().replace(".", "")
    provider_prefill = prefill.get(provider_key, {})

    if provider == "DuckMail":
        api_base = questionary.text(
            "DuckMail API Base",
            default=provider_prefill.get("api_base", "https://api.duckmail.sbs"),
        ).ask()

        bearer = questionary.password(
            "Bearer Token",
            default=provider_prefill.get("bearer", ""),
        ).ask()

        if api_base is None or bearer is None:
            return None

        return {
            "provider": "duckmail",
            "duckmail": {"api_base": api_base.strip(), "bearer": bearer},
        }

    elif provider == "Mailcow":
        api_url = questionary.text(
            "Mailcow API URL",
            default=provider_prefill.get("api_url", ""),
        ).ask()

        api_key = questionary.password(
            "API Key",
            default=provider_prefill.get("api_key", ""),
        ).ask()

        domain = questionary.text(
            "Domain",
            default=provider_prefill.get("domain", ""),
        ).ask()

        imap_host = questionary.text(
            "IMAP Host",
            default=provider_prefill.get("imap_host", ""),
        ).ask()

        imap_port = questionary.text(
            "IMAP Port",
            default=str(provider_prefill.get("imap_port", "993")),
        ).ask()

        if None in (api_url, api_key, domain, imap_host, imap_port):
            return None

        return {
            "provider": "mailcow",
            "mailcow": {
                "api_url": api_url.strip(),
                "api_key": api_key,
                "domain": domain.strip(),
                "imap_host": imap_host.strip(),
                "imap_port": int(imap_port),
            },
        }

    else:  # Mail.tm
        api_base = questionary.text(
            "Mail.tm API Base",
            default=provider_prefill.get("api_base", "https://api.mail.tm"),
        ).ask()

        if api_base is None:
            return None

        return {
            "provider": "mailtm",
            "mailtm": {"api_base": api_base.strip()},
        }


def _ask_registration_config(prefill: dict[str, Any]) -> dict[str, Any] | None:
    """询问注册参数。"""
    total_accounts = questionary.text(
        "注册账号数量",
        default=str(prefill.get("total_accounts", "3")),
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()

    workers = questionary.text(
        "并发数",
        default=str(prefill.get("workers", "3")),
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()

    proxy = questionary.text(
        "代理地址 (留空跳过)",
        default=prefill.get("proxy", ""),
    ).ask()

    if None in (total_accounts, workers, proxy):
        return None

    return {
        "total_accounts": int(total_accounts),
        "workers": int(workers),
        "proxy": proxy.strip(),
        "output_file": prefill.get("output_file", "registered_accounts.txt"),
        "ak_file": prefill.get("ak_file", "ak.txt"),
        "rk_file": prefill.get("rk_file", "rk.txt"),
        "token_json_dir": prefill.get("token_json_dir", "codex_tokens"),
    }


def _ask_upload_config(prefill: dict[str, Any], proxy: str) -> dict[str, Any] | None:
    """询问上传配置。"""
    targets = prefill.get("targets", [])
    default_target = "none"
    if set(targets) == {"cpa", "sub2api"}:
        default_target = "both"
    elif "sub2api" in targets:
        default_target = "sub2api"
    elif "cpa" in targets:
        default_target = "cpa"

    target = questionary.select(
        "上传目标",
        choices=["none", "cpa", "sub2api", "both"],
        default=default_target,
    ).ask()

    if target is None:
        return None

    cpa_config = None
    sub2api_config = None

    if target in ("cpa", "both"):
        cpa_prefill = prefill.get("cpa", {})
        cpa_api_url = questionary.text(
            "CPA API URL",
            default=cpa_prefill.get("api_url", ""),
        ).ask()

        cpa_api_token = questionary.password(
            "CPA API Token",
            default=cpa_prefill.get("api_token", ""),
        ).ask()

        if None in (cpa_api_url, cpa_api_token):
            return None

        cpa_config = {
            "api_url": cpa_api_url.strip(),
            "api_token": cpa_api_token,
        }

    if target in ("sub2api", "both"):
        sub2api_prefill = prefill.get("sub2api", {})

        api_base = questionary.text(
            "Sub2API Base",
            default=sub2api_prefill.get("api_base", ""),
        ).ask()

        admin_api_key = questionary.password(
            "Admin API Key (留空则使用 Bearer Token)",
            default=sub2api_prefill.get("admin_api_key", ""),
        ).ask()

        bearer_token = ""
        if not admin_api_key:
            bearer_token = questionary.password(
                "Bearer Token",
                default=sub2api_prefill.get("bearer_token", ""),
            ).ask()

        if None in (api_base, admin_api_key, bearer_token):
            return None

        # 加载分组
        group_ids = sub2api_prefill.get("group_ids", [])
        if not group_ids and api_base and (admin_api_key or bearer_token):
            should_load = questionary.confirm(
                "是否加载 Sub2API 分组列表?",
                default=True,
            ).ask()

            if should_load:
                group_ids = _load_sub2api_groups(api_base, admin_api_key, bearer_token, proxy)

        if not group_ids:
            console.print("[yellow]警告: 未选择 Sub2API 分组，运行时可能失败[/yellow]")

        sub2api_config = {
            "api_base": api_base.strip(),
            "admin_api_key": admin_api_key,
            "bearer_token": bearer_token,
            "group_ids": group_ids,
            "account_concurrency": sub2api_prefill.get("account_concurrency", 1),
            "account_priority": sub2api_prefill.get("account_priority", 1),
        }

    # 构建 targets 列表
    targets_list = []
    if target == "both":
        targets_list = ["cpa", "sub2api"]
    elif target in ("cpa", "sub2api"):
        targets_list = [target]

    return {
        "targets": targets_list,
        "cpa": cpa_config,
        "sub2api": sub2api_config,
    }


def _load_sub2api_groups(
    api_base: str,
    admin_api_key: str,
    bearer_token: str,
    proxy: str,
) -> list[int]:
    """加载 Sub2API 分组列表。"""
    from chatgpt_register.config.model import Sub2ApiConfig
    from chatgpt_register.upload.sub2api import fetch_sub2api_openai_groups

    try:
        config = Sub2ApiConfig(
            api_base=api_base,
            admin_api_key=admin_api_key,
            bearer_token=bearer_token,
            group_ids=[],
        )

        console.print("\n[cyan]正在加载分组列表...[/cyan]")
        groups = fetch_sub2api_openai_groups(config, proxy)

        if not groups:
            console.print("[yellow]未找到任何分组[/yellow]\n")
            return []

        # 让用户选择分组
        choices = [f"{g['name']} (ID: {g['id']})" for g in groups]
        selected = questionary.select(
            "选择分组",
            choices=choices,
        ).ask()

        if selected is None:
            return []

        # 提取 group_id
        group_id = int(selected.split("ID: ")[1].rstrip(")"))
        console.print(f"[green]✓[/green] 已选择分组: {selected}\n")
        return [group_id]

    except Exception as e:
        console.print(f"[red]加载分组失败: {e}[/red]\n")
        return []


def _provider_display_name(provider: str) -> str:
    """转换 provider 为显示名称。"""
    mapping = {
        "duckmail": "DuckMail",
        "mailcow": "Mailcow",
        "mailtm": "Mail.tm",
    }
    return mapping.get(provider.lower(), "Mail.tm")
