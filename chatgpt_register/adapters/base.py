"""EmailAdapter 抽象基类。"""

from __future__ import annotations

import random
import string

from chatgpt_register.core.humanize import HumanizedPrefixGenerator
from chatgpt_register.core.utils import safe_json_loads


class EmailAdapter:
    """邮箱适配器基类 — 所有具体适配器须继承此类。"""

    provider = "base"
    _prefix_generator: HumanizedPrefixGenerator | None = None

    def __init__(self, register):
        self.reg = register

    @classmethod
    def _get_prefix_generator(cls) -> HumanizedPrefixGenerator:
        """惰性初始化全局前缀生成器（类变量单例）。"""
        if cls._prefix_generator is None:
            cls._prefix_generator = HumanizedPrefixGenerator()
        return cls._prefix_generator

    def _generate_local_part(self, humanize: bool, *, alphanumeric_only: bool = False) -> str:
        """生成邮箱本地部分（@ 前缀）。

        Args:
            humanize: 是否使用拟人化格式。True 使用人名格式，False 使用随机字符串。
            alphanumeric_only: 为 True 时去掉 `.` 和 `_`，适用于不接受特殊字符的 API 型邮箱服务。
        """
        if humanize:
            prefix = self._get_prefix_generator().generate()
            if alphanumeric_only:
                prefix = prefix.replace(".", "").replace("_", "")
            return prefix
        return "".join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(random.randint(8, 13))
        )

    def create_temp_email(self):
        raise NotImplementedError

    def fetch_messages(self, mail_token: str):
        return []

    def extract_message_content(self, mail_token: str, message: dict):
        if not isinstance(message, dict):
            return ""
        return (
            message.get("_body")
            or message.get("text")
            or message.get("html")
            or message.get("data")
            or ""
        )

    def _json_or_empty(self, resp):
        try:
            return resp.json()
        except Exception:
            return safe_json_loads(resp.text)
