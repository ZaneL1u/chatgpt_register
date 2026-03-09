"""Maildrop.cc 免费临时邮箱适配器。

无需注册、无需 API Key，公共共享邮箱。
固定域名 maildrop.cc，使用 GraphQL API。
"""

from __future__ import annotations

import random
import string

from chatgpt_register.adapters.base import EmailAdapter
from chatgpt_register.config.model import MaildropConfig


class MaildropAdapter(EmailAdapter):
    """Maildrop.cc 邮箱适配器（GraphQL API）。"""

    provider = "maildrop"

    def __init__(self, register, email_config: MaildropConfig):
        super().__init__(register)
        self.config = email_config

    @property
    def _api_base(self) -> str:
        return self.config.api_base.rstrip("/")

    def create_temp_email(self):
        """生成随机邮箱地址，无需注册。"""
        local = "".join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(random.randint(8, 13))
        )
        email_addr = f"{local}@maildrop.cc"
        # mail_token 用 "maildrop:{email}" 格式传递邮箱地址
        return email_addr, "", f"maildrop:{email_addr}"

    def _extract_mailbox(self, mail_token: str) -> str:
        """从 mail_token 提取 mailbox 名称（@ 前的用户名部分）。"""
        if mail_token.startswith("maildrop:"):
            email = mail_token[len("maildrop:"):]
        else:
            email = mail_token
        return email.split("@")[0]

    def _graphql_query(self, query: str) -> dict:
        """执行 GraphQL 查询。"""
        session = self.reg._create_email_http_session()
        res = session.post(
            self._api_base,
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code != 200:
            return {}
        data = self._json_or_empty(res)
        if isinstance(data, dict):
            return data.get("data", {})
        return {}

    def fetch_messages(self, mail_token: str):
        """查询收件箱消息列表。"""
        mailbox = self._extract_mailbox(mail_token)
        query = (
            '{ inbox(mailbox: "%s") '
            "{ id headerfrom subject date } }" % mailbox
        )
        data = self._graphql_query(query)
        inbox = data.get("inbox")
        if isinstance(inbox, list):
            return inbox
        return []

    def extract_message_content(self, mail_token: str, message: dict):
        """获取单封邮件的内容。"""
        msg_id = (message or {}).get("id")
        if not msg_id:
            return ""
        mailbox = self._extract_mailbox(mail_token)
        query = (
            '{ message(mailbox: "%s", id: "%s") '
            "{ id subject headerfrom date data html } }" % (mailbox, msg_id)
        )
        data = self._graphql_query(query)
        msg = data.get("message")
        if not isinstance(msg, dict):
            return ""
        # Maildrop 返回 html 和 data 字段，data 含原始邮件头
        return msg.get("html") or msg.get("data") or ""
