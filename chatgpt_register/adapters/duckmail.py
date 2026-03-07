"""DuckMail 邮箱适配器。"""

from __future__ import annotations

import random
import string
import time

from chatgpt_register.adapters.base import EmailAdapter
from chatgpt_register.config.model import DuckMailConfig
from chatgpt_register.core.utils import generate_password


class DuckMailAdapter(EmailAdapter):
    provider = "duckmail"

    def __init__(self, register, email_config: DuckMailConfig):
        super().__init__(register)
        self.config = email_config

    @property
    def _api_base(self) -> str:
        return self.config.api_base.rstrip("/")

    @property
    def _bearer(self) -> str:
        return self.config.bearer

    def create_temp_email(self):
        if not self._bearer:
            raise Exception("DUCKMAIL_BEARER 未设置，无法创建临时邮箱")

        chars = string.ascii_lowercase + string.digits
        email_local = "".join(random.choice(chars) for _ in range(random.randint(8, 13)))
        email_addr = f"{email_local}@duckmail.sbs"
        password = generate_password()

        headers = {"Authorization": f"Bearer {self._bearer}"}
        session = self.reg._create_email_http_session()

        res = session.post(
            f"{self._api_base}/accounts",
            json={"address": email_addr, "password": password},
            headers=headers,
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code not in (200, 201):
            raise Exception(f"DuckMail 创建邮箱失败: {res.status_code} - {res.text[:200]}")

        time.sleep(0.5)
        token_res = session.post(
            f"{self._api_base}/token",
            json={"address": email_addr, "password": password},
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        token_data = self._json_or_empty(token_res)
        mail_token = token_data.get("token")
        if token_res.status_code != 200 or not mail_token:
            raise Exception(f"DuckMail 获取邮件 Token 失败: {token_res.status_code}")

        return email_addr, password, mail_token

    def fetch_messages(self, mail_token: str):
        session = self.reg._create_email_http_session()
        headers = {"Authorization": f"Bearer {mail_token}"}
        res = session.get(
            f"{self._api_base}/messages",
            headers=headers,
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code != 200:
            return []
        data = self._json_or_empty(res)
        return data.get("hydra:member") or data.get("member") or data.get("data") or []

    def extract_message_content(self, mail_token: str, message: dict):
        msg_id = (message or {}).get("id") or (message or {}).get("@id")
        if not msg_id:
            return ""
        if isinstance(msg_id, str) and msg_id.startswith("/messages/"):
            msg_id = msg_id.split("/")[-1]

        session = self.reg._create_email_http_session()
        headers = {"Authorization": f"Bearer {mail_token}"}
        res = session.get(
            f"{self._api_base}/messages/{msg_id}",
            headers=headers,
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code != 200:
            return ""
        detail = self._json_or_empty(res)
        return detail.get("text") or detail.get("html") or ""
