"""Shared test fixtures for chatgpt-register tests."""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def sample_duckmail_dict() -> dict:
    """完整的 duckmail 配置字典，可直接传给 RegisterConfig.model_validate()"""
    return {
        "email": {
            "provider": "duckmail",
            "duckmail": {
                "api_base": "https://api.duckmail.sbs",
                "bearer": "test-duckmail-token",
            },
        },
        "registration": {
            "total_accounts": 5,
            "proxy": "socks5://127.0.0.1:1080",
            "output_file": "registered_accounts.txt",
            "ak_file": "ak.txt",
            "rk_file": "rk.txt",
            "token_json_dir": "codex_tokens",
        },
        "oauth": {
            "enabled": True,
            "required": True,
            "issuer": "https://auth.openai.com",
            "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
            "redirect_uri": "http://localhost:1455/auth/callback",
        },
        "upload": {
            "targets": ["cpa"],
            "cpa": {
                "api_url": "https://cpa.example.com/api",
                "api_token": "test-cpa-token",
            },
        },
    }


@pytest.fixture
def sample_mailcow_dict() -> dict:
    """完整的 mailcow 配置字典"""
    return {
        "email": {
            "provider": "mailcow",
            "mailcow": {
                "api_url": "https://mail.example.com",
                "api_key": "test-mailcow-key",
                "domain": "example.com",
                "imap_host": "mail.example.com",
                "imap_port": 993,
            },
        },
        "registration": {
            "total_accounts": 10,
            "proxy": "",
            "output_file": "registered_accounts.txt",
            "ak_file": "ak.txt",
            "rk_file": "rk.txt",
            "token_json_dir": "codex_tokens",
        },
        "oauth": {
            "enabled": True,
            "required": True,
            "issuer": "https://auth.openai.com",
            "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
            "redirect_uri": "http://localhost:1455/auth/callback",
        },
        "upload": {
            "targets": [],
        },
    }


@pytest.fixture
def sample_mailtm_dict() -> dict:
    """完整的 mailtm 配置字典"""
    return {
        "email": {
            "provider": "mailtm",
            "mailtm": {
                "api_base": "https://api.mail.tm",
            },
        },
        "registration": {
            "total_accounts": 3,
            "proxy": "http://proxy.example.com:8080",
            "output_file": "output.txt",
            "ak_file": "ak.txt",
            "rk_file": "rk.txt",
            "token_json_dir": "codex_tokens",
        },
        "oauth": {
            "enabled": False,
            "required": False,
            "issuer": "https://auth.openai.com",
            "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
            "redirect_uri": "http://localhost:1455/auth/callback",
        },
        "upload": {
            "targets": ["sub2api"],
            "sub2api": {
                "api_base": "https://sub2api.example.com",
                "admin_api_key": "test-admin-key",
                "bearer_token": "test-bearer",
                "group_ids": [1, 2, 3],
                "account_concurrency": 2,
                "account_priority": 5,
            },
        },
    }


@pytest.fixture
def tmp_profiles_dir(tmp_path: Path) -> Path:
    """临时目录，供 ProfileManager 测试使用"""
    return tmp_path / "profiles"
