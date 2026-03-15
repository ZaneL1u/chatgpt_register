"""反机器人加固测试 — Phase 9 (ANTI-01 ~ ANTI-05)。"""

from __future__ import annotations

import dataclasses

from chatgpt_register.core.http import BrowserProfile, CHROME_PROFILES, random_chrome_version


class TestBrowserProfile:
    """ANTI-02: BrowserProfile dataclass 统一浏览器指纹。"""

    def test_browser_profile_dataclass(self):
        """BrowserProfile 是 frozen dataclass，含 5 个字段。"""
        assert dataclasses.is_dataclass(BrowserProfile)
        fields = {f.name for f in dataclasses.fields(BrowserProfile)}
        assert fields == {"impersonate", "chrome_major", "chrome_full", "user_agent", "sec_ch_ua"}
        # frozen — 不可修改
        bp = random_chrome_version()
        try:
            bp.impersonate = "x"  # type: ignore[misc]
            assert False, "should be frozen"
        except dataclasses.FrozenInstanceError:
            pass

    def test_random_chrome_version_returns_browser_profile(self):
        """random_chrome_version() 返回 BrowserProfile。"""
        bp = random_chrome_version()
        assert isinstance(bp, BrowserProfile)

    def test_random_chrome_version_fields_nonempty(self):
        """所有字段非空。"""
        bp = random_chrome_version()
        assert bp.impersonate
        assert bp.chrome_major > 0
        assert bp.chrome_full
        assert bp.user_agent
        assert bp.sec_ch_ua

    def test_random_chrome_version_ua_contains_version(self):
        """UA 字符串包含完整版本号。"""
        bp = random_chrome_version()
        assert bp.chrome_full in bp.user_agent


class TestChromeProfiles:
    """ANTI-03: CHROME_PROFILES 扩充到 8-12 个版本。"""

    def test_chrome_profiles_count(self):
        """8-12 个 profile。"""
        assert 8 <= len(CHROME_PROFILES) <= 12

    def test_chrome_profiles_impersonate_values(self):
        """impersonate 值与 curl_cffi 0.14.0 对齐。"""
        valid = {"chrome131", "chrome133a", "chrome136", "chrome142"}
        for p in CHROME_PROFILES:
            assert p["impersonate"] in valid, f"unexpected impersonate: {p['impersonate']}"

    def test_chrome_profiles_major_minimum(self):
        """所有版本 >= 131。"""
        for p in CHROME_PROFILES:
            assert p["major"] >= 131, f"major {p['major']} < 131"

    def test_chrome_profiles_have_required_fields(self):
        """每个 profile 包含所有必需字段。"""
        required = {"major", "impersonate", "build", "patch_range", "sec_ch_ua"}
        for i, p in enumerate(CHROME_PROFILES):
            assert required.issubset(p.keys()), f"profile {i} missing fields: {required - p.keys()}"

    def test_chrome_profiles_patch_range_valid(self):
        """patch_range 是有效的 (min, max) 元组。"""
        for i, p in enumerate(CHROME_PROFILES):
            lo, hi = p["patch_range"]
            assert lo < hi, f"profile {i}: patch_range ({lo}, {hi}) invalid"
