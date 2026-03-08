"""Tests for ProfileManager TOML persistence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.config.profile import (
    InvalidProfileNameError,
    ProfileDecodeError,
    ProfileManager,
    ProfileNotFoundError,
    ProfileSummary,
    ProfileValidationError,
)


class TestSaveAndLoad:
    """测试保存和加载功能"""

    def test_save_and_load(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """保存 duckmail 配置 -> 加载 -> 数据与原始一致"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        original = RegisterConfig.model_validate(sample_duckmail_dict)
        pm.save("test-profile", original)
        loaded = pm.load("test-profile")
        assert loaded.email.provider == "duckmail"
        assert loaded.email.duckmail is not None
        assert loaded.email.duckmail.bearer == "test-duckmail-token"
        assert loaded.registration.total_accounts == 5
        assert loaded.registration.proxy == "socks5://127.0.0.1:1080"
        assert loaded.upload.targets == ["cpa"]
        assert loaded.upload.cpa is not None
        assert loaded.upload.cpa.api_token == "test-cpa-token"

    def test_save_creates_directory(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """保存到不存在的目录 -> 自动创建目录"""
        nested = tmp_profiles_dir / "deep" / "nested"
        pm = ProfileManager(base_dir=nested)
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        path = pm.save("auto-dir", config)
        assert path.exists()
        assert nested.is_dir()

    def test_save_overwrites(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """对同一 profile 名保存两次 -> 第二次覆盖"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        config1 = RegisterConfig.model_validate(sample_duckmail_dict)
        pm.save("overwrite-test", config1)

        modified = sample_duckmail_dict.copy()
        modified["registration"] = {
            **sample_duckmail_dict["registration"],
            "total_accounts": 99,
        }
        config2 = RegisterConfig.model_validate(modified)
        pm.save("overwrite-test", config2)

        loaded = pm.load("overwrite-test")
        assert loaded.registration.total_accounts == 99


class TestLoadErrors:
    """测试加载错误处理"""

    def test_load_nonexistent(self, tmp_profiles_dir: Path) -> None:
        """加载不存在的 profile -> ProfileNotFoundError，包含中文"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        with pytest.raises(ProfileNotFoundError, match="Profile 不存在: nonexistent"):
            pm.load("nonexistent")

    def test_load_invalid_name(self, tmp_profiles_dir: Path) -> None:
        """非法名称加载 -> InvalidProfileNameError"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        with pytest.raises(InvalidProfileNameError, match="Profile 名称"):
            pm.load("../escape")

    def test_load_broken_toml(self, tmp_profiles_dir: Path) -> None:
        """坏 TOML -> ProfileDecodeError，消息可直接提示用户"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        tmp_profiles_dir.mkdir(parents=True, exist_ok=True)
        (tmp_profiles_dir / "broken.toml").write_text("[email\nprovider='duckmail'\n")

        with pytest.raises(ProfileDecodeError, match="TOML 解析失败: broken"):
            pm.load("broken")

    def test_load_invalid_structure(self, tmp_profiles_dir: Path) -> None:
        """结构不合法 -> ProfileValidationError，包含校验细节"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        tmp_profiles_dir.mkdir(parents=True, exist_ok=True)
        (tmp_profiles_dir / "invalid.toml").write_text(
            """
[email]
provider = "duckmail"

[registration]
total_accounts = 2
workers = 1
""".strip()
        )

        with pytest.raises(ProfileValidationError, match="Profile 配置不合法") as exc_info:
            pm.load("invalid")
        assert "配置校验失败" in str(exc_info.value)


class TestCustomBaseDir:
    """测试自定义存储路径"""

    def test_custom_base_dir(
        self, tmp_path: Path, sample_duckmail_dict: dict
    ) -> None:
        """传入自定义 base_dir -> 文件保存到该目录下"""
        custom_dir = tmp_path / "custom-profiles"
        pm = ProfileManager(base_dir=custom_dir)
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        path = pm.save("custom", config)
        assert path.parent == custom_dir
        assert path.name == "custom.toml"


class TestListProfiles:
    """测试列举功能"""

    def test_list_profiles_empty(self, tmp_profiles_dir: Path) -> None:
        """空目录 -> 返回空列表"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        assert pm.list_profiles() == []

    def test_list_profiles(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """保存 3 个 profile -> list_profiles 返回排序后的 3 个名称"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        pm.save("charlie", config)
        pm.save("alpha", config)
        pm.save("bravo", config)
        profiles = pm.list_profiles()
        assert profiles == ["alpha", "bravo", "charlie"]

    def test_list_profile_summaries_all_platforms(
        self,
        tmp_profiles_dir: Path,
        sample_duckmail_dict: dict,
        sample_mailcow_dict: dict,
        sample_mailtm_dict: dict,
    ) -> None:
        """摘要接口覆盖全部邮箱平台并保持稳定排序"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        pm.save("charlie", RegisterConfig.model_validate(sample_mailtm_dict))
        pm.save("alpha", RegisterConfig.model_validate(sample_duckmail_dict))
        pm.save("bravo", RegisterConfig.model_validate(sample_mailcow_dict))

        summaries = pm.list_profile_summaries()

        assert [summary.name for summary in summaries] == ["alpha", "bravo", "charlie"]
        assert all(isinstance(summary, ProfileSummary) for summary in summaries)

        duckmail_summary, mailcow_summary, mailtm_summary = summaries
        assert duckmail_summary.email_provider == "duckmail"
        assert duckmail_summary.upload_targets == ("cpa",)
        assert duckmail_summary.total_accounts == 5
        assert duckmail_summary.workers == 3
        assert duckmail_summary.path.name == "alpha.toml"
        assert isinstance(duckmail_summary.updated_at, datetime)

        assert mailcow_summary.email_provider == "mailcow"
        assert mailcow_summary.upload_targets == ()
        assert mailcow_summary.total_accounts == 10
        assert mailcow_summary.workers == 4

        assert mailtm_summary.email_provider == "mailtm"
        assert mailtm_summary.upload_targets == ("sub2api",)
        assert mailtm_summary.total_accounts == 3
        assert mailtm_summary.workers == 2

    def test_list_profile_summaries_broken_toml(
        self, tmp_profiles_dir: Path
    ) -> None:
        """摘要接口遇到坏文件 -> 抛出可识别异常供上层决定处理策略"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        tmp_profiles_dir.mkdir(parents=True, exist_ok=True)
        (tmp_profiles_dir / "broken.toml").write_text("[email\nprovider='duckmail'\n")

        with pytest.raises(ProfileDecodeError, match="TOML 解析失败: broken"):
            pm.list_profile_summaries()


class TestExistsAndDelete:
    """测试存在性检查和删除"""

    def test_exists(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """保存后 exists 返回 True，未保存时返回 False"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        assert pm.exists("test") is False
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        pm.save("test", config)
        assert pm.exists("test") is True

    def test_exists_invalid_name(self, tmp_profiles_dir: Path) -> None:
        """非法名称 exists -> InvalidProfileNameError"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        with pytest.raises(InvalidProfileNameError, match="Profile 名称"):
            pm.exists("bad/name")

    def test_delete(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """保存后删除 -> exists 返回 False"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        pm.save("to-delete", config)
        assert pm.exists("to-delete") is True
        pm.delete("to-delete")
        assert pm.exists("to-delete") is False

    def test_delete_nonexistent(self, tmp_profiles_dir: Path) -> None:
        """删除不存在的 profile -> 不报错"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        pm.delete("does-not-exist")

    def test_delete_invalid_name(self, tmp_profiles_dir: Path) -> None:
        """非法名称删除 -> InvalidProfileNameError"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        with pytest.raises(InvalidProfileNameError, match="Profile 名称"):
            pm.delete("bad/name")


class TestTomlContent:
    """测试 TOML 文件内容质量"""

    def test_toml_content_readable(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """保存后 TOML 文件包含可读文本"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        path = pm.save("readable", config)
        content = path.read_text()
        assert "[email]" in content
        assert 'provider = "duckmail"' in content
        assert "[email.duckmail]" in content

    def test_toml_excludes_unused_platform(
        self, tmp_profiles_dir: Path, sample_duckmail_dict: dict
    ) -> None:
        """duckmail 配置的 TOML 中不包含 mailcow/mailtm"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        path = pm.save("duckmail-only", config)
        content = path.read_text()
        assert "[email.mailcow]" not in content
        assert "[email.mailtm]" not in content


class TestRoundtrip:
    """测试所有平台的往返一致性"""

    def test_roundtrip_all_platforms(
        self,
        tmp_profiles_dir: Path,
        sample_duckmail_dict: dict,
        sample_mailcow_dict: dict,
        sample_mailtm_dict: dict,
    ) -> None:
        """分别测试 duckmail/mailcow/mailtm 的 save -> load 往返"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)

        for name, data in [
            ("duckmail", sample_duckmail_dict),
            ("mailcow", sample_mailcow_dict),
            ("mailtm", sample_mailtm_dict),
        ]:
            original = RegisterConfig.model_validate(data)
            pm.save(name, original)
            loaded = pm.load(name)
            assert original.model_dump(mode="json", exclude_none=True) == loaded.model_dump(
                mode="json", exclude_none=True
            )


class TestNameValidation:
    """测试 profile 名称校验"""

    @pytest.mark.parametrize(
        "bad_name",
        [
            "",
            "../escape",
            "a/b",
            "a\\b",
            "-leading",
            "_leading",
            "A" * 65,
            "UPPER",
            "has space",
        ],
    )
    def test_profile_name_validation(
        self,
        tmp_profiles_dir: Path,
        sample_duckmail_dict: dict,
        bad_name: str,
    ) -> None:
        """非法名称 save -> 抛出 InvalidProfileNameError"""
        pm = ProfileManager(base_dir=tmp_profiles_dir)
        config = RegisterConfig.model_validate(sample_duckmail_dict)
        with pytest.raises(InvalidProfileNameError):
            pm.save(bad_name, config)
