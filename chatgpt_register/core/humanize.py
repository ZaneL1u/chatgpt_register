"""拟人化邮箱前缀生成器。

生成真实人名格式的邮箱前缀（如 emma.wilson、emma_1994），
替代随机字母数字字符串，提升反风控效果。

4 种格式均匀随机选取：
  1. firstname.lastname  — emma.wilson
  2. firstname_NNNN      — emma_1994（1980-2006 年份）
  3. firstnameNN         — emma94（年份后 2 位）
  4. f.lastname          — e.wilson（首字母 + 姓氏）
"""

from __future__ import annotations

import random
import string
import threading


class HumanizedPrefixGenerator:
    """线程安全的拟人化邮箱前缀生成器，保证运行期内唯一性。"""

    _used: set[str] = set()
    _lock = threading.Lock()

    _MAX_RETRIES = 1000

    def generate(self) -> str:
        """生成一个唯一的拟人化邮箱前缀。

        Returns:
            唯一的前缀字符串（全小写）。
            超过重试上限时 fallback 到随机字符串。
        """
        with self._lock:
            for _ in range(self._MAX_RETRIES):
                prefix = self._make_prefix()
                if prefix not in self._used:
                    self._used.add(prefix)
                    return prefix
            # 超过重试上限，fallback 到随机字符串
            fallback = "".join(
                random.choice(string.ascii_lowercase + string.digits)
                for _ in range(random.randint(8, 13))
            )
            self._used.add(fallback)
            return fallback

    def _make_prefix(self) -> str:
        """生成单个前缀（不保证唯一性）。"""
        first, last = self._get_names()
        fmt = random.randint(0, 3)
        year = random.randint(1980, 2006)
        if fmt == 0:
            return f"{first}.{last}"
        elif fmt == 1:
            return f"{first}_{year}"
        elif fmt == 2:
            return f"{first}{year % 100:02d}"
        else:
            return f"{first[0]}.{last}"

    def _get_names(self) -> tuple[str, str]:
        """获取随机名和姓（全小写）。优先 faker，fallback 到 names。"""
        try:
            from faker import Faker

            fake = Faker("en_US")
            return fake.first_name().lower(), fake.last_name().lower()
        except (ImportError, Exception):
            pass
        try:
            import names

            return names.get_first_name().lower(), names.get_last_name().lower()
        except ImportError:
            raise RuntimeError(
                "faker 和 names 均未安装，无法生成拟人化邮箱前缀"
            )

    @classmethod
    def reset(cls) -> None:
        """清空已用前缀集合（仅供测试使用）。"""
        with cls._lock:
            cls._used.clear()
