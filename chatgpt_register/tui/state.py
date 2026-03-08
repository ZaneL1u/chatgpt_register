"""TUI 向导共享状态。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chatgpt_register.config.model import RegisterConfig


DEFAULT_EMAIL_DRAFTS: dict[str, dict[str, Any]] = {
    "duckmail": {
        "api_base": "https://api.duckmail.sbs",
        "bearer": "",
    },
    "mailcow": {
        "api_url": "",
        "api_key": "",
        "domain": "",
        "imap_host": "",
        "imap_port": "993",
    },
    "mailtm": {
        "api_base": "https://api.mail.tm",
    },
}

DEFAULT_REGISTRATION: dict[str, str] = {
    "total_accounts": "3",
    "workers": "3",
    "proxy": "",
    "output_file": "registered_accounts.txt",
    "ak_file": "ak.txt",
    "rk_file": "rk.txt",
    "token_json_dir": "codex_tokens",
}

DEFAULT_UPLOAD: dict[str, Any] = {
    "target": "cpa",
    "cpa": {
        "api_url": "",
        "api_token": "",
    },
    "sub2api": {
        "api_base": "",
        "admin_api_key": "",
        "bearer_token": "",
        "selected_group_id": "",
        "group_ids": [],
        "account_concurrency": "1",
        "account_priority": "1",
    },
    "available_groups": [],
}

DEFAULT_OAUTH: dict[str, Any] = {
    "enabled": True,
    "required": True,
    "issuer": "https://auth.openai.com",
    "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
    "redirect_uri": "http://localhost:1455/auth/callback",
}


@dataclass
class WizardState:
    """跨 Screen 保留的配置草稿。"""

    profile_name: str = ""
    source_profile_name: str | None = None
    require_profile_save: bool = False
    email_provider: str = "mailtm"
    draft_email: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            provider: dict(values) for provider, values in DEFAULT_EMAIL_DRAFTS.items()
        }
    )
    registration: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_REGISTRATION))
    upload: dict[str, Any] = field(
        default_factory=lambda: {
            "target": DEFAULT_UPLOAD["target"],
            "cpa": dict(DEFAULT_UPLOAD["cpa"]),
            "sub2api": dict(DEFAULT_UPLOAD["sub2api"]),
            "available_groups": list(DEFAULT_UPLOAD["available_groups"]),
        }
    )
    oauth: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_OAUTH))

    @classmethod
    def from_config_dict(
        cls,
        config_dict: dict[str, Any] | None = None,
        *,
        profile_name: str = "",
        source_profile_name: str | None = None,
        require_profile_save: bool = False,
    ) -> "WizardState":
        config_dict = config_dict or {}
        state = cls()
        state.profile_name = profile_name
        state.source_profile_name = source_profile_name
        state.require_profile_save = require_profile_save

        email = config_dict.get("email", {})
        provider = str(email.get("provider") or state.email_provider).strip().lower()
        if provider in state.draft_email:
            state.email_provider = provider
        for provider_name, defaults in DEFAULT_EMAIL_DRAFTS.items():
            payload = email.get(provider_name) or {}
            merged = dict(defaults)
            for key, value in payload.items():
                merged[key] = str(value)
            state.draft_email[provider_name] = merged

        registration = config_dict.get("registration", {})
        for key, default in DEFAULT_REGISTRATION.items():
            value = registration.get(key, default)
            state.registration[key] = str(value)

        upload = config_dict.get("upload", {})
        state.upload["target"] = _target_from_targets(upload.get("targets", []))
        for key, default in DEFAULT_UPLOAD["cpa"].items():
            state.upload["cpa"][key] = str((upload.get("cpa") or {}).get(key, default))
        for key, default in DEFAULT_UPLOAD["sub2api"].items():
            if key == "group_ids":
                group_ids = (upload.get("sub2api") or {}).get(key, default)
                state.upload["sub2api"][key] = [int(item) for item in group_ids or []]
                continue
            value = (upload.get("sub2api") or {}).get(key, default)
            state.upload["sub2api"][key] = str(value)
        if state.upload["sub2api"]["group_ids"]:
            state.upload["sub2api"]["selected_group_id"] = str(state.upload["sub2api"]["group_ids"][0])

        oauth = config_dict.get("oauth", {})
        for key, default in DEFAULT_OAUTH.items():
            state.oauth[key] = oauth.get(key, default)

        return state

    def export_config_dict(self) -> dict[str, Any]:
        selected_group_id = self.upload["sub2api"].get("selected_group_id", "").strip()
        group_ids = list(self.upload["sub2api"].get("group_ids", []))
        if selected_group_id:
            try:
                group_ids = [int(selected_group_id)]
            except ValueError:
                group_ids = []

        email = {
            "provider": self.email_provider,
            "duckmail": {
                "api_base": self.draft_email["duckmail"]["api_base"].strip(),
                "bearer": self.draft_email["duckmail"]["bearer"],
            },
            "mailcow": {
                "api_url": self.draft_email["mailcow"]["api_url"].strip(),
                "api_key": self.draft_email["mailcow"]["api_key"],
                "domain": self.draft_email["mailcow"]["domain"].strip(),
                "imap_host": self.draft_email["mailcow"]["imap_host"].strip(),
                "imap_port": _as_int(self.draft_email["mailcow"]["imap_port"], 993),
            },
            "mailtm": {
                "api_base": self.draft_email["mailtm"]["api_base"].strip(),
            },
        }
        registration = {
            "total_accounts": _as_int(self.registration["total_accounts"], 1),
            "workers": _as_int(self.registration["workers"], 1),
            "proxy": self.registration["proxy"].strip(),
            "output_file": self.registration["output_file"].strip(),
            "ak_file": self.registration["ak_file"].strip(),
            "rk_file": self.registration["rk_file"].strip(),
            "token_json_dir": self.registration["token_json_dir"].strip(),
        }
        upload = {
            "targets": _targets_from_target(self.upload["target"]),
            "cpa": {
                "api_url": self.upload["cpa"]["api_url"].strip(),
                "api_token": self.upload["cpa"]["api_token"],
            },
            "sub2api": {
                "api_base": self.upload["sub2api"]["api_base"].strip(),
                "admin_api_key": self.upload["sub2api"]["admin_api_key"],
                "bearer_token": self.upload["sub2api"]["bearer_token"],
                "group_ids": group_ids,
                "account_concurrency": _as_int(self.upload["sub2api"]["account_concurrency"], 1),
                "account_priority": _as_int(self.upload["sub2api"]["account_priority"], 1),
            },
        }
        oauth = {
            "enabled": bool(self.oauth["enabled"]),
            "required": bool(self.oauth["required"]),
            "issuer": str(self.oauth["issuer"]).strip(),
            "client_id": str(self.oauth["client_id"]).strip(),
            "redirect_uri": str(self.oauth["redirect_uri"]).strip(),
        }
        return {
            "email": email,
            "registration": registration,
            "upload": upload,
            "oauth": oauth,
        }

    def build_config(self) -> RegisterConfig:
        return RegisterConfig.model_validate(self.export_config_dict())


def _target_from_targets(targets: list[str]) -> str:
    values = {str(item).strip().lower() for item in targets}
    if values == {"cpa", "sub2api"}:
        return "both"
    if values == {"sub2api"}:
        return "sub2api"
    if values == {"cpa"}:
        return "cpa"
    return "none"


def _targets_from_target(target: str) -> list[str]:
    if target == "both":
        return ["cpa", "sub2api"]
    if target in {"cpa", "sub2api"}:
        return [target]
    return []


def _as_int(value: Any, fallback: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback
