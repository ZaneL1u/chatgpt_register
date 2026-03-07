"""Tests for RegisterConfig Pydantic data model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chatgpt_register.config.model import RegisterConfig, format_validation_errors


class TestValidConfigs:
    """测试有效配置能正确创建模型实例"""

    def test_valid_duckmail_config(self, sample_duckmail_dict: dict) -> None:
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        assert config.email.provider == "duckmail"
        assert config.email.duckmail is not None
        assert config.email.duckmail.bearer == "test-duckmail-token"

    def test_valid_mailcow_config(self, sample_mailcow_dict: dict) -> None:
        config = RegisterConfig.model_validate(sample_mailcow_dict)
        assert config.email.provider == "mailcow"
        assert config.email.mailcow is not None
        assert config.email.mailcow.api_key == "test-mailcow-key"
        assert config.email.mailcow.domain == "example.com"

    def test_valid_mailtm_config(self, sample_mailtm_dict: dict) -> None:
        config = RegisterConfig.model_validate(sample_mailtm_dict)
        assert config.email.provider == "mailtm"
        assert config.email.mailtm is not None
        assert config.email.mailtm.api_base == "https://api.mail.tm"


class TestProviderValidation:
    """测试邮箱平台联动校验"""

    def test_provider_case_insensitive(self) -> None:
        """provider='DuckMail' 应自动转为 'duckmail'"""
        data = {
            "email": {
                "provider": "DuckMail",
                "duckmail": {
                    "bearer": "test-token",
                },
            },
        }
        config = RegisterConfig.model_validate(data)
        assert config.email.provider == "duckmail"

    def test_missing_provider_config(self) -> None:
        """选择 duckmail 但无 duckmail 配置节 -> ValidationError，包含中文"""
        data = {
            "email": {
                "provider": "duckmail",
            },
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterConfig.model_validate(data)
        error_str = str(exc_info.value)
        assert "选择了 duckmail 邮箱平台" in error_str


class TestUploadValidation:
    """测试上传目标联动校验"""

    def test_upload_target_cpa_missing_config(self) -> None:
        """targets=['cpa'] 但无 cpa 配置节 -> ValidationError，包含中文"""
        data = {
            "email": {
                "provider": "mailtm",
                "mailtm": {"api_base": "https://api.mail.tm"},
            },
            "upload": {
                "targets": ["cpa"],
            },
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterConfig.model_validate(data)
        error_str = str(exc_info.value)
        assert "上传目标包含 cpa" in error_str

    def test_upload_target_sub2api_missing_config(self) -> None:
        """targets=['sub2api'] 但无 sub2api 配置节 -> ValidationError"""
        data = {
            "email": {
                "provider": "mailtm",
                "mailtm": {"api_base": "https://api.mail.tm"},
            },
            "upload": {
                "targets": ["sub2api"],
            },
        }
        with pytest.raises(ValidationError):
            RegisterConfig.model_validate(data)

    def test_upload_empty_targets(self) -> None:
        """targets=[] -> 校验通过（不上传）"""
        data = {
            "email": {
                "provider": "mailtm",
                "mailtm": {"api_base": "https://api.mail.tm"},
            },
            "upload": {
                "targets": [],
            },
        }
        config = RegisterConfig.model_validate(data)
        assert config.upload.targets == []

    def test_upload_both_targets(self) -> None:
        """targets=['cpa', 'sub2api'] 且提供两个配置节 -> 校验通过"""
        data = {
            "email": {
                "provider": "mailtm",
                "mailtm": {"api_base": "https://api.mail.tm"},
            },
            "upload": {
                "targets": ["cpa", "sub2api"],
                "cpa": {
                    "api_url": "https://cpa.example.com",
                    "api_token": "token",
                },
                "sub2api": {
                    "api_base": "https://sub2api.example.com",
                    "admin_api_key": "key",
                    "bearer_token": "bearer",
                },
            },
        }
        config = RegisterConfig.model_validate(data)
        assert "cpa" in config.upload.targets
        assert "sub2api" in config.upload.targets
        assert config.upload.cpa is not None
        assert config.upload.sub2api is not None


class TestDefaults:
    """测试默认值"""

    def test_default_values(self) -> None:
        """仅传 email 配置 -> registration, oauth, upload 使用默认值"""
        data = {
            "email": {
                "provider": "mailtm",
                "mailtm": {"api_base": "https://api.mail.tm"},
            },
        }
        config = RegisterConfig.model_validate(data)
        # registration defaults
        assert config.registration.total_accounts == 5
        assert config.registration.workers == 3
        assert config.registration.proxy == ""
        assert config.registration.output_file == "registered_accounts.txt"
        assert config.registration.ak_file == "ak.txt"
        assert config.registration.rk_file == "rk.txt"
        assert config.registration.token_json_dir == "codex_tokens"
        # oauth defaults
        assert config.oauth.enabled is True
        assert config.oauth.required is True
        assert config.oauth.issuer == "https://auth.openai.com"
        # upload defaults
        assert config.upload.targets == []


class TestFieldCoverage:
    """验证全局变量覆盖完整性"""

    def test_field_coverage(self, sample_duckmail_dict: dict) -> None:
        """验证 chatgpt_register.py:414-443 中每个全局变量都有对应字段"""
        # 构造包含所有字段的完整配置
        full_dict = {
            "email": {
                "provider": "duckmail",
                "duckmail": {
                    "api_base": "https://api.duckmail.sbs",
                    "bearer": "test-token",
                },
                "mailcow": {
                    "api_url": "https://mail.example.com",
                    "api_key": "key",
                    "domain": "example.com",
                    "imap_host": "mail.example.com",
                    "imap_port": 993,
                },
                "mailtm": {
                    "api_base": "https://api.mail.tm",
                },
            },
            "registration": {
                "total_accounts": 5,
                "workers": 3,
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
                "targets": ["cpa", "sub2api"],
                "cpa": {
                    "api_url": "https://cpa.example.com",
                    "api_token": "token",
                },
                "sub2api": {
                    "api_base": "https://sub2api.example.com",
                    "admin_api_key": "key",
                    "bearer_token": "bearer",
                    "group_ids": [1, 2],
                    "account_concurrency": 2,
                    "account_priority": 3,
                },
            },
        }
        config = RegisterConfig.model_validate(full_dict)
        assert config.registration.workers == 3

        # 逐一验证 chatgpt_register.py:414-443 的全局变量对应字段
        # EMAIL_PROVIDER -> email.provider
        assert config.email.provider == "duckmail"
        # DUCKMAIL_API_BASE -> email.duckmail.api_base
        assert config.email.duckmail.api_base == "https://api.duckmail.sbs"
        # DUCKMAIL_BEARER -> email.duckmail.bearer
        assert config.email.duckmail.bearer == "test-token"
        # MAILCOW_API_URL -> email.mailcow.api_url
        assert config.email.mailcow.api_url == "https://mail.example.com"
        # MAILCOW_API_KEY -> email.mailcow.api_key
        assert config.email.mailcow.api_key == "key"
        # MAILCOW_DOMAIN -> email.mailcow.domain
        assert config.email.mailcow.domain == "example.com"
        # MAILCOW_IMAP_HOST -> email.mailcow.imap_host
        assert config.email.mailcow.imap_host == "mail.example.com"
        # MAILCOW_IMAP_PORT -> email.mailcow.imap_port
        assert config.email.mailcow.imap_port == 993
        # MAILTM_API_BASE -> email.mailtm.api_base
        assert config.email.mailtm.api_base == "https://api.mail.tm"
        # DEFAULT_TOTAL_ACCOUNTS -> registration.total_accounts
        assert config.registration.total_accounts == 5
        # DEFAULT_PROXY -> registration.proxy
        assert config.registration.proxy == "socks5://127.0.0.1:1080"
        # DEFAULT_OUTPUT_FILE -> registration.output_file
        assert config.registration.output_file == "registered_accounts.txt"
        # ENABLE_OAUTH -> oauth.enabled
        assert config.oauth.enabled is True
        # OAUTH_REQUIRED -> oauth.required
        assert config.oauth.required is True
        # OAUTH_ISSUER -> oauth.issuer
        assert config.oauth.issuer == "https://auth.openai.com"
        # OAUTH_CLIENT_ID -> oauth.client_id
        assert config.oauth.client_id == "app_EMoamEEZ73f0CkXaXp7hrann"
        # OAUTH_REDIRECT_URI -> oauth.redirect_uri
        assert config.oauth.redirect_uri == "http://localhost:1455/auth/callback"
        # AK_FILE -> registration.ak_file
        assert config.registration.ak_file == "ak.txt"
        # RK_FILE -> registration.rk_file
        assert config.registration.rk_file == "rk.txt"
        # TOKEN_JSON_DIR -> registration.token_json_dir
        assert config.registration.token_json_dir == "codex_tokens"
        # UPLOAD_TARGETS -> upload.targets
        assert config.upload.targets == ["cpa", "sub2api"]
        # UPLOAD_API_URL -> upload.cpa.api_url
        assert config.upload.cpa.api_url == "https://cpa.example.com"
        # UPLOAD_API_TOKEN -> upload.cpa.api_token
        assert config.upload.cpa.api_token == "token"
        # SUB2API_API_BASE -> upload.sub2api.api_base
        assert config.upload.sub2api.api_base == "https://sub2api.example.com"
        # SUB2API_ADMIN_API_KEY -> upload.sub2api.admin_api_key
        assert config.upload.sub2api.admin_api_key == "key"
        # SUB2API_BEARER_TOKEN -> upload.sub2api.bearer_token
        assert config.upload.sub2api.bearer_token == "bearer"
        # SUB2API_GROUP_IDS -> upload.sub2api.group_ids
        assert config.upload.sub2api.group_ids == [1, 2]
        # SUB2API_ACCOUNT_CONCURRENCY -> upload.sub2api.account_concurrency
        assert config.upload.sub2api.account_concurrency == 2
        # SUB2API_ACCOUNT_PRIORITY -> upload.sub2api.account_priority
        assert config.upload.sub2api.account_priority == 3

    def test_workers_must_be_positive(self, sample_mailtm_dict: dict) -> None:
        sample_mailtm_dict["registration"]["workers"] = 0

        with pytest.raises(ValidationError) as exc_info:
            RegisterConfig.model_validate(sample_mailtm_dict)

        assert "workers" in str(exc_info.value)


class TestFormatting:
    """测试错误格式化和序列化"""

    def test_format_validation_errors(self) -> None:
        """校验失败后调用 format_validation_errors -> 返回包含 '配置校验失败' 的中文字符串"""
        data = {
            "email": {
                "provider": "duckmail",
                # 缺少 duckmail 配置节
            },
        }
        with pytest.raises(ValidationError) as exc_info:
            RegisterConfig.model_validate(data)
        result = format_validation_errors(exc_info.value)
        assert "配置校验失败" in result

    def test_model_dump_excludes_none(self, sample_duckmail_dict: dict) -> None:
        """model_dump(mode='json', exclude_none=True) 不包含 None 值"""
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        dumped = config.model_dump(mode="json", exclude_none=True)

        def _check_no_none(d: dict, path: str = "") -> None:
            for key, value in d.items():
                current = f"{path}.{key}" if path else key
                assert value is not None, f"Found None at {current}"
                if isinstance(value, dict):
                    _check_no_none(value, current)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            _check_no_none(item, f"{current}[{i}]")

        _check_no_none(dumped)

    def test_unused_platform_not_in_dump(self, sample_duckmail_dict: dict) -> None:
        """duckmail 配置中 model_dump 不包含 mailcow/mailtm 键"""
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        dumped = config.model_dump(mode="json", exclude_none=True)
        email_section = dumped["email"]
        assert "mailcow" not in email_section
        assert "mailtm" not in email_section
