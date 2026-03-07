"""CLI 入口 — 构造 RegisterConfig 后调用 run_batch。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.core.utils import as_bool, as_int, parse_int_list
from chatgpt_register.upload.sub2api import prepare_sub2api_group_binding
from chatgpt_register.core.batch import run_batch


def _build_cli_parser():
    parser = argparse.ArgumentParser(
        prog="chatgpt-register",
        description="ChatGPT 批量自动注册工具",
    )
    parser.add_argument("--non-interactive", action="store_true", help="非交互模式；不进行 input() 询问。")
    parser.add_argument("--upload-targets", help="上传目标: none/cpa/sub2api/both（也支持 cpa,sub2api）")
    parser.add_argument("--proxy", help="代理地址；传空字符串可强制不使用代理。")
    parser.add_argument("--total-accounts", type=int, help="注册账号数量（>0）。")
    parser.add_argument("--workers", type=int, help="并发数（>0）。")
    parser.add_argument("--sub2api-api-base", help="Sub2API 地址，例如 https://sub2api.example.com")
    parser.add_argument("--sub2api-admin-api-key", help="Sub2API Admin API Key（x-api-key）。")
    parser.add_argument("--sub2api-bearer-token", help="Sub2API Bearer Token（Authorization）。")
    parser.add_argument("--sub2api-group-id", type=int, help="Sub2API 分组 ID（openai 平台）。")
    parser.add_argument("--sub2api-auto-select-first-group", action="store_true", help="非交互模式下，若未提供 group-id，则自动选择第一个 openai 分组。")
    return parser


def _parse_upload_targets(value):
    alias = {"cpa": "cpa", "sub2api": "sub2api", "sub2": "sub2api", "s2a": "sub2api"}
    tokens = []
    if isinstance(value, (list, tuple, set)):
        for item in value:
            tokens.extend(str(item).split(","))
    else:
        import re
        tokens = re.split(r"[,|/\s]+", str(value or ""))

    targets = set()
    unknown = []
    for token in tokens:
        t = token.strip().lower()
        if not t:
            continue
        if t in {"both", "all"}:
            targets.update({"cpa", "sub2api"})
            continue
        if t in {"none", "off", "no", "disable", "disabled"}:
            continue
        mapped = alias.get(t)
        if mapped:
            targets.add(mapped)
        else:
            unknown.append(t)
    return sorted(targets), unknown


def _load_legacy_config() -> dict:
    config = {
        "total_accounts": 3,
        "email_provider": "mailtm",
        "duckmail_api_base": "https://api.duckmail.sbs",
        "duckmail_bearer": "",
        "mailcow_api_url": "",
        "mailcow_api_key": "",
        "mailcow_domain": "",
        "mailcow_imap_host": "",
        "mailcow_imap_port": 993,
        "mailtm_api_base": "https://api.mail.tm",
        "proxy": "",
        "output_file": "registered_accounts.txt",
        "enable_oauth": True,
        "oauth_required": True,
        "oauth_issuer": "https://auth.openai.com",
        "oauth_client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
        "oauth_redirect_uri": "http://localhost:1455/auth/callback",
        "ak_file": "ak.txt",
        "rk_file": "rk.txt",
        "token_json_dir": "codex_tokens",
        "upload_targets": "cpa",
        "upload_api_url": "",
        "upload_api_token": "",
        "sub2api_api_base": "",
        "sub2api_admin_api_key": "",
        "sub2api_bearer_token": "",
        "sub2api_group_ids": [],
        "sub2api_account_concurrency": 1,
        "sub2api_account_priority": 1,
    }

    root = Path.cwd()
    config_path = root / "config.json"
    if config_path.exists():
        try:
            config.update(json.loads(config_path.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"加载 config.json 失败: {e}")

    config["email_provider"] = os.environ.get("EMAIL_PROVIDER", config["email_provider"])
    config["duckmail_api_base"] = os.environ.get("DUCKMAIL_API_BASE", config["duckmail_api_base"])
    config["duckmail_bearer"] = os.environ.get("DUCKMAIL_BEARER", config["duckmail_bearer"])
    config["mailcow_api_url"] = os.environ.get("MAILCOW_API_URL", config["mailcow_api_url"])
    config["mailcow_api_key"] = os.environ.get("MAILCOW_API_KEY", config["mailcow_api_key"])
    config["mailcow_domain"] = os.environ.get("MAILCOW_DOMAIN", config["mailcow_domain"])
    config["mailcow_imap_host"] = os.environ.get("MAILCOW_IMAP_HOST", config["mailcow_imap_host"])
    config["mailcow_imap_port"] = int(os.environ.get("MAILCOW_IMAP_PORT", config["mailcow_imap_port"]))
    config["mailtm_api_base"] = os.environ.get("MAILTM_API_BASE", config["mailtm_api_base"])
    config["proxy"] = os.environ.get("PROXY", config["proxy"])
    config["total_accounts"] = int(os.environ.get("TOTAL_ACCOUNTS", config["total_accounts"]))
    config["enable_oauth"] = as_bool(os.environ.get("ENABLE_OAUTH", config["enable_oauth"]))
    config["oauth_required"] = as_bool(os.environ.get("OAUTH_REQUIRED", config["oauth_required"]))
    config["oauth_issuer"] = os.environ.get("OAUTH_ISSUER", config["oauth_issuer"])
    config["oauth_client_id"] = os.environ.get("OAUTH_CLIENT_ID", config["oauth_client_id"])
    config["oauth_redirect_uri"] = os.environ.get("OAUTH_REDIRECT_URI", config["oauth_redirect_uri"])
    config["ak_file"] = os.environ.get("AK_FILE", config["ak_file"])
    config["rk_file"] = os.environ.get("RK_FILE", config["rk_file"])
    config["token_json_dir"] = os.environ.get("TOKEN_JSON_DIR", config["token_json_dir"])
    config["upload_targets"] = os.environ.get("UPLOAD_TARGETS", config["upload_targets"])
    config["upload_api_url"] = os.environ.get("UPLOAD_API_URL", config["upload_api_url"])
    config["upload_api_token"] = os.environ.get("UPLOAD_API_TOKEN", config["upload_api_token"])
    config["sub2api_api_base"] = os.environ.get("SUB2API_API_BASE", config["sub2api_api_base"])
    config["sub2api_admin_api_key"] = os.environ.get("SUB2API_ADMIN_API_KEY", config["sub2api_admin_api_key"])
    config["sub2api_bearer_token"] = os.environ.get("SUB2API_BEARER_TOKEN", config["sub2api_bearer_token"])
    group_ids_env = os.environ.get("SUB2API_GROUP_IDS")
    config["sub2api_group_ids"] = parse_int_list(group_ids_env if group_ids_env is not None else config.get("sub2api_group_ids"))
    config["sub2api_account_concurrency"] = max(0, as_int(os.environ.get("SUB2API_ACCOUNT_CONCURRENCY", config["sub2api_account_concurrency"]), 1))
    config["sub2api_account_priority"] = as_int(os.environ.get("SUB2API_ACCOUNT_PRIORITY", config["sub2api_account_priority"]), 1)
    return config


def _legacy_to_register_config_dict(raw: dict) -> dict:
    provider = str(raw.get("email_provider", "mailtm")).strip().lower()
    upload_targets, _ = _parse_upload_targets(raw.get("upload_targets", ""))

    data = {
        "email": {
            "provider": provider,
        },
        "registration": {
            "total_accounts": int(raw.get("total_accounts", 3)),
            "proxy": raw.get("proxy", "") or "",
            "output_file": raw.get("output_file", "registered_accounts.txt"),
            "ak_file": raw.get("ak_file", "ak.txt"),
            "rk_file": raw.get("rk_file", "rk.txt"),
            "token_json_dir": raw.get("token_json_dir", "codex_tokens"),
        },
        "oauth": {
            "enabled": as_bool(raw.get("enable_oauth", True)),
            "required": as_bool(raw.get("oauth_required", True)),
            "issuer": str(raw.get("oauth_issuer", "https://auth.openai.com")).rstrip("/"),
            "client_id": raw.get("oauth_client_id", "app_EMoamEEZ73f0CkXaXp7hrann"),
            "redirect_uri": raw.get("oauth_redirect_uri", "http://localhost:1455/auth/callback"),
        },
        "upload": {
            "targets": upload_targets,
        },
    }

    if provider == "duckmail":
        data["email"]["duckmail"] = {
            "api_base": str(raw.get("duckmail_api_base", "https://api.duckmail.sbs")).rstrip("/"),
            "bearer": raw.get("duckmail_bearer", ""),
        }
    elif provider == "mailcow":
        data["email"]["mailcow"] = {
            "api_url": str(raw.get("mailcow_api_url", "")).rstrip("/"),
            "api_key": raw.get("mailcow_api_key", ""),
            "domain": raw.get("mailcow_domain", ""),
            "imap_host": raw.get("mailcow_imap_host", ""),
            "imap_port": int(raw.get("mailcow_imap_port", 993)),
        }
    elif provider == "mailtm":
        data["email"]["mailtm"] = {
            "api_base": str(raw.get("mailtm_api_base", "https://api.mail.tm")).rstrip("/"),
        }

    if "cpa" in upload_targets:
        data["upload"]["cpa"] = {
            "api_url": raw.get("upload_api_url", ""),
            "api_token": raw.get("upload_api_token", ""),
        }

    if "sub2api" in upload_targets:
        data["upload"]["sub2api"] = {
            "api_base": str(raw.get("sub2api_api_base", "")).rstrip("/"),
            "admin_api_key": raw.get("sub2api_admin_api_key", ""),
            "bearer_token": raw.get("sub2api_bearer_token", ""),
            "group_ids": parse_int_list(raw.get("sub2api_group_ids", [])),
            "account_concurrency": max(0, as_int(raw.get("sub2api_account_concurrency", 1), 1)),
            "account_priority": as_int(raw.get("sub2api_account_priority", 1), 1),
        }

    return data


def _resolve_proxy_from_inputs(config_dict: dict, non_interactive, proxy_arg):
    if proxy_arg is not None:
        proxy = proxy_arg.strip()
        config_dict.setdefault("registration", {})["proxy"] = proxy
        return config_dict

    proxy = config_dict.get("registration", {}).get("proxy", "")
    env_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or os.environ.get("ALL_PROXY") or os.environ.get("all_proxy")

    if non_interactive:
        config_dict["registration"]["proxy"] = proxy or env_proxy or ""
        return config_dict

    if proxy:
        print(f"[Info] 检测到默认代理: {proxy}")
        use_default = input("使用此代理? (Y/n): ").strip().lower()
        if use_default == "n":
            proxy = input("输入代理地址 (留空=不使用代理): ").strip()
    elif env_proxy:
        print(f"[Info] 检测到环境变量代理: {env_proxy}")
        use_env = input("使用此代理? (Y/n): ").strip().lower()
        if use_env == "n":
            proxy = input("输入代理地址 (留空=不使用代理): ").strip()
        else:
            proxy = env_proxy
    else:
        proxy = input("输入代理地址 (如 http://127.0.0.1:7890，留空=不使用代理): ").strip()

    config_dict["registration"]["proxy"] = proxy or ""
    return config_dict


def _resolve_count_and_workers(config_dict: dict, non_interactive, total_accounts_arg, workers_arg):
    if total_accounts_arg is not None:
        if total_accounts_arg <= 0:
            raise ValueError("--total-accounts 必须大于 0")
        config_dict.setdefault("registration", {})["total_accounts"] = total_accounts_arg
    elif not non_interactive:
        default_total = config_dict.get("registration", {}).get("total_accounts", 3)
        count_input = input(f"\n注册账号数量 (默认 {default_total}): ").strip()
        config_dict["registration"]["total_accounts"] = int(count_input) if count_input.isdigit() and int(count_input) > 0 else default_total

    if workers_arg is not None and workers_arg <= 0:
        raise ValueError("--workers 必须大于 0")
    return config_dict


def main(argv=None):
    try:
        parser = _build_cli_parser()
        args = parser.parse_args(argv)

        legacy = _load_legacy_config()
        config_dict = _legacy_to_register_config_dict(legacy)

        if args.upload_targets:
            targets, unknown = _parse_upload_targets(args.upload_targets)
            if unknown:
                print(f"无法识别的上传目标: {', '.join(unknown)}")
                return 2
            config_dict.setdefault("upload", {})["targets"] = targets

        if args.sub2api_api_base is not None:
            config_dict.setdefault("upload", {}).setdefault("sub2api", {})["api_base"] = args.sub2api_api_base.strip().rstrip("/")
        if args.sub2api_admin_api_key is not None:
            config_dict.setdefault("upload", {}).setdefault("sub2api", {})["admin_api_key"] = args.sub2api_admin_api_key.strip()
        if args.sub2api_bearer_token is not None:
            config_dict.setdefault("upload", {}).setdefault("sub2api", {})["bearer_token"] = args.sub2api_bearer_token.strip()
        if args.sub2api_group_id is not None:
            config_dict.setdefault("upload", {}).setdefault("sub2api", {})["group_ids"] = [args.sub2api_group_id]

        config_dict = _resolve_proxy_from_inputs(config_dict, args.non_interactive, args.proxy)
        config_dict = _resolve_count_and_workers(config_dict, args.non_interactive, args.total_accounts, args.workers)

        if "sub2api" in config_dict.get("upload", {}).get("targets", []):
            sub2 = config_dict.get("upload", {}).get("sub2api", {})
            temp_cfg = RegisterConfig.model_validate({
                "email": config_dict["email"],
                "registration": config_dict.get("registration", {}),
                "oauth": config_dict.get("oauth", {}),
                "upload": {"targets": [], "sub2api": sub2},
            }).upload.sub2api
            if temp_cfg is not None:
                ok, group_ids = prepare_sub2api_group_binding(
                    temp_cfg,
                    interactive=not args.non_interactive,
                    selected_group_id=args.sub2api_group_id,
                    auto_select_first=args.sub2api_auto_select_first_group,
                    proxy=config_dict.get("registration", {}).get("proxy", ""),
                )
                if not ok:
                    print("Sub2API 上传未完成配置，本次任务已中止。")
                    return 2
                config_dict.setdefault("upload", {}).setdefault("sub2api", {})["group_ids"] = group_ids

        config = RegisterConfig.model_validate(config_dict)
        run_batch(config)
        return 0
    except KeyboardInterrupt:
        print("\n[Info] 用户中断，已退出。")
        return 130
    except Exception as e:
        print(f"配置或执行失败: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
