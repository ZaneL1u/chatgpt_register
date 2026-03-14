"""拟人化邮箱前缀生成器测试套件。

覆盖需求: HUMAN-01, HUMAN-02, HUMAN-03, HUMAN-04
TDD RED 阶段：chatgpt_register.core.humanize 模块尚未创建时，
这些测试预期全部 FAIL（ImportError）。
"""

from __future__ import annotations

import re
import threading

import pytest

from chatgpt_register.core.humanize import HumanizedPrefixGenerator
from chatgpt_register.config.model import EmailConfig

# ---------------------------------------------------------------------------
# 格式正则定义
# ---------------------------------------------------------------------------

# firstname.lastname — e.g. emma.wilson (first name >= 2 chars to distinguish from f.lastname)
PAT_FIRST_DOT_LAST = re.compile(r"^[a-z]{2,}\.[a-z]+$")

# firstname_NNNN — e.g. emma_1994
PAT_FIRST_UNDER_YEAR = re.compile(r"^[a-z]+_(\d{4})$")

# firstnameNN — e.g. emma94
PAT_FIRST_YY = re.compile(r"^[a-z]+(\d{2})$")

# f.lastname — e.g. e.wilson
PAT_INITIAL_DOT_LAST = re.compile(r"^[a-z]\.[a-z]+$")

ALL_PATTERNS = [PAT_FIRST_DOT_LAST, PAT_FIRST_UNDER_YEAR, PAT_FIRST_YY, PAT_INITIAL_DOT_LAST]


def _matches_any(prefix: str) -> bool:
    """检查前缀是否匹配 4 种格式之一。"""
    return any(p.match(prefix) for p in ALL_PATTERNS)


def _classify(prefix: str) -> int | None:
    """返回前缀匹配的格式编号（0-3），无匹配返回 None。"""
    for i, p in enumerate(ALL_PATTERNS):
        if p.match(prefix):
            return i
    return None


# ---------------------------------------------------------------------------
# HUMAN-01: 邮箱前缀含人名格式
# ---------------------------------------------------------------------------


class TestPrefixHumanFormat:
    """HUMAN-01: 开启 humanize_email 后前缀含人名格式。"""

    def setup_method(self):
        HumanizedPrefixGenerator.reset()

    def test_prefix_is_human_format(self):
        gen = HumanizedPrefixGenerator()
        for _ in range(50):
            prefix = gen.generate()
            assert _matches_any(prefix), f"前缀 '{prefix}' 不匹配任何人名格式"

    def test_names_lowercase(self):
        gen = HumanizedPrefixGenerator()
        for _ in range(50):
            prefix = gen.generate()
            # 去掉数字和分隔符后，所有字母应为小写
            letters = re.sub(r"[^a-zA-Z]", "", prefix)
            assert letters == letters.lower(), f"前缀 '{prefix}' 包含大写字母"


# ---------------------------------------------------------------------------
# HUMAN-02: 至少 3 种不同格式
# ---------------------------------------------------------------------------


class TestFormatDiversity:
    """HUMAN-02: 系统能生成至少 3 种不同格式的邮箱前缀。"""

    def setup_method(self):
        HumanizedPrefixGenerator.reset()

    def test_at_least_3_formats(self):
        gen = HumanizedPrefixGenerator()
        seen_formats: set[int] = set()
        for _ in range(200):
            prefix = gen.generate()
            fmt = _classify(prefix)
            if fmt is not None:
                seen_formats.add(fmt)
        assert len(seen_formats) >= 3, (
            f"200 个前缀中仅出现 {len(seen_formats)} 种格式，期望至少 3 种"
        )

    def test_format_distribution(self):
        """4 种格式各至少出现一次（粗略均匀性检验）。"""
        gen = HumanizedPrefixGenerator()
        counts = {0: 0, 1: 0, 2: 0, 3: 0}
        for _ in range(400):
            prefix = gen.generate()
            fmt = _classify(prefix)
            if fmt is not None:
                counts[fmt] += 1
        for fmt_id, count in counts.items():
            assert count > 0, f"格式 {fmt_id} 在 400 个前缀中从未出现"


# ---------------------------------------------------------------------------
# HUMAN-03: 同批次不重复
# ---------------------------------------------------------------------------


class TestUniqueness:
    """HUMAN-03: 同一批次中所有邮箱前缀不重复。"""

    def setup_method(self):
        HumanizedPrefixGenerator.reset()

    def test_uniqueness_across_batch(self):
        gen = HumanizedPrefixGenerator()
        prefixes = [gen.generate() for _ in range(200)]
        assert len(set(prefixes)) == len(prefixes), "发现重复前缀"

    def test_thread_safety(self):
        """多线程并发生成 100 个前缀，无重复。"""
        gen = HumanizedPrefixGenerator()
        results: list[str] = []
        lock = threading.Lock()

        def worker():
            for _ in range(25):
                prefix = gen.generate()
                with lock:
                    results.append(prefix)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 100
        assert len(set(results)) == len(results), "多线程生成中发现重复前缀"


# ---------------------------------------------------------------------------
# HUMAN-04: 配置开关与向下兼容
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """HUMAN-04: humanize_email 配置开关和旧 profile 兼容。"""

    def test_backward_compatibility(self, legacy_email_config_dict):
        """旧 profile 不含 humanize_email 时默认值为 True。"""
        config = EmailConfig.model_validate(legacy_email_config_dict["email"])
        assert config.humanize_email is True

    def test_humanize_enabled(self, humanize_email_config_dict):
        """显式设置 humanize_email=True。"""
        config = EmailConfig.model_validate(humanize_email_config_dict["email"])
        assert config.humanize_email is True

    def test_humanize_disabled(self, no_humanize_email_config_dict):
        """显式设置 humanize_email=False。"""
        config = EmailConfig.model_validate(no_humanize_email_config_dict["email"])
        assert config.humanize_email is False


# ---------------------------------------------------------------------------
# 年份范围验证
# ---------------------------------------------------------------------------


class TestYearRange:
    """含年份的格式中，年份在 1980-2006 范围内。"""

    def setup_method(self):
        HumanizedPrefixGenerator.reset()

    def test_year_range(self):
        gen = HumanizedPrefixGenerator()
        for _ in range(200):
            prefix = gen.generate()
            # 检查 firstname_NNNN 格式
            m = PAT_FIRST_UNDER_YEAR.match(prefix)
            if m:
                year = int(m.group(1))
                assert 1980 <= year <= 2006, f"年份 {year} 不在 1980-2006 范围内"
            # 检查 firstnameNN 格式
            m2 = PAT_FIRST_YY.match(prefix)
            if m2:
                yy = int(m2.group(1))
                # 80-99 或 00-06
                assert (80 <= yy <= 99) or (0 <= yy <= 6), (
                    f"两位年份 {yy:02d} 不在 80-06 范围内"
                )


# ---------------------------------------------------------------------------
# Faker fallback 测试
# ---------------------------------------------------------------------------


class TestFallback:
    """faker 不可用时自动回退到 names 库。"""

    def setup_method(self):
        HumanizedPrefixGenerator.reset()

    def test_fallback_to_names(self, monkeypatch):
        """模拟 faker 不可用，验证 fallback 到 names。"""
        import sys

        # 暂时从 sys.modules 中移除 faker 并阻止导入
        original = sys.modules.get("faker")
        sys.modules["faker"] = None  # type: ignore[assignment]
        try:
            gen = HumanizedPrefixGenerator()
            prefix = gen.generate()
            assert _matches_any(prefix), f"Fallback 前缀 '{prefix}' 不匹配人名格式"
        finally:
            if original is not None:
                sys.modules["faker"] = original
            else:
                sys.modules.pop("faker", None)
