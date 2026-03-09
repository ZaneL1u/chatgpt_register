"""Catchmail.io 免费临时邮箱适配器。

无需注册、无需 API Key，公共共享邮箱。
支持多个域名：catchmail.io / .cc / .com / .net / .org / .co
"""

from __future__ import annotations

import random
import string

from chatgpt_register.adapters.base import EmailAdapter
from chatgpt_register.config.model import CatchmailConfig


class CatchmailAdapter(EmailAdapter):
    """Catchmail.io 邮箱适配器。"""

    provider = "catchmail"

    def __init__(self, register, email_config: CatchmailConfig):
        super().__init__(register)
        self.config = email_config

    @property
    def _api_base(self) -> str:
        return self.config.api_base.rstrip("/")

    def create_temp_email(self):
        """生成随机邮箱地址，无需注册。"""
        domain = random.choice(self.config.domains)
        local = "".join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(random.randint(8, 13))
        )
        email_addr = f"{local}@{domain}"
        # Catchmail 无密码，mail_token 用 "catchmail:{email}" 格式传递邮箱地址
        return email_addr, "", f"catchmail:{email_addr}"

    def _extract_email_from_token(self, mail_token: str) -> str:
        """从 mail_token 提取邮箱地址。"""
        if mail_token.startswith("catchmail:"):
            return mail_token[len("catchmail:"):]
        return mail_token

    def fetch_messages(self, mail_token: str):
        """查询收件箱消息列表。"""
        email_addr = self._extract_email_from_token(mail_token)
        session = self.reg._create_email_http_session()
        res = session.get(
            f"{self._api_base}/api/v1/mailbox",
            params={"address": email_addr},
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code != 200:
            return []
        data = self._json_or_empty(res)
        if isinstance(data, dict):
            return data.get("messages", [])
        return []

    def extract_message_content(self, mail_token: str, message: dict):
        """获取单封邮件的内容。"""
        msg_id = (message or {}).get("id")
        if not msg_id:
            return ""
        email_addr = self._extract_email_from_token(mail_token)
        session = self.reg._create_email_http_session()
        res = session.get(
            f"{self._api_base}/api/v1/message/{msg_id}",
            params={"mailbox": email_addr},
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code != 200:
            return ""
        detail = self._json_or_empty(res)
        if not isinstance(detail, dict):
            return ""
        body = detail.get("body")
        if isinstance(body, dict):
            return body.get("text") or body.get("html") or ""
        return detail.get("text") or detail.get("html") or ""
