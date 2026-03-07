"""EmailAdapter 抽象基类。"""

from __future__ import annotations

from chatgpt_register.core.utils import safe_json_loads


class EmailAdapter:
    """邮箱适配器基类 — 所有具体适配器须继承此类。"""

    provider = "base"

    def __init__(self, register):
        self.reg = register

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
