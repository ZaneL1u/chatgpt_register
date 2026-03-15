"""Mail.tm 邮箱适配器。"""

from __future__ import annotations

import random

from chatgpt_register.adapters.base import EmailAdapter
from chatgpt_register.config.model import MailTmConfig
from chatgpt_register.core.utils import generate_password


class MailTmAdapter(EmailAdapter):
    provider = "mailtm"

    def __init__(self, register, email_config: MailTmConfig, *, humanize_email: bool = True):
        super().__init__(register)
        self.config = email_config
        self._humanize_email = humanize_email

    @property
    def _api_base(self) -> str:
        return self.config.api_base.rstrip("/")

    @staticmethod
    def _extract_items(data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("hydra:member", "member", "data", "items", "results"):
                val = data.get(key)
                if isinstance(val, list):
                    return val
        return []

    def _pick_domain(self, session):
        res = session.get(
            f"{self._api_base}/domains",
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        data = self._json_or_empty(res)
        domains = self._extract_items(data)
        if not domains:
            raise Exception("Mail.tm 无可用域名")

        candidates = []
        for item in domains:
            if isinstance(item, dict):
                domain = item.get("domain") or item.get("name")
            elif isinstance(item, str):
                domain = item
            else:
                domain = None
            if domain and "@" not in domain:
                candidates.append(domain)

        if not candidates:
            raise Exception(f"Mail.tm 域名响应格式异常: {type(data).__name__}")
        return random.choice(candidates)

    def create_temp_email(self):
        session = self.reg._create_email_http_session()
        domain = self._pick_domain(session)
        password = generate_password()

        for _ in range(5):
            local = self._generate_local_part(self._humanize_email, alphanumeric_only=True)
            email_addr = f"{local}@{domain}"
            res = session.post(
                f"{self._api_base}/accounts",
                json={"address": email_addr, "password": password},
                timeout=15,
                impersonate=self.reg.impersonate,
            )
            if res.status_code not in (200, 201):
                continue

            token_res = session.post(
                f"{self._api_base}/token",
                json={"address": email_addr, "password": password},
                timeout=15,
                impersonate=self.reg.impersonate,
            )
            token_data = self._json_or_empty(token_res)
            mail_token = token_data.get("token") if isinstance(token_data, dict) else ""
            if token_res.status_code == 200 and mail_token:
                return email_addr, password, mail_token
            raise Exception(f"Mail.tm 获取 token 失败: {token_res.status_code}")

        raise Exception("Mail.tm 创建邮箱失败（可能触发限速或域名不可用）")

    def fetch_messages(self, mail_token: str):
        session = self.reg._create_email_http_session()
        res = session.get(
            f"{self._api_base}/messages",
            headers={"Authorization": f"Bearer {mail_token}"},
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code != 200:
            return []
        data = self._json_or_empty(res)
        return self._extract_items(data)

    def extract_message_content(self, mail_token: str, message: dict):
        msg_id = (message or {}).get("id") or (message or {}).get("@id")
        if not msg_id:
            return ""
        if isinstance(msg_id, str) and msg_id.startswith("/messages/"):
            msg_id = msg_id.split("/")[-1]

        session = self.reg._create_email_http_session()
        res = session.get(
            f"{self._api_base}/messages/{msg_id}",
            headers={"Authorization": f"Bearer {mail_token}"},
            timeout=15,
            impersonate=self.reg.impersonate,
        )
        if res.status_code != 200:
            return ""
        detail = self._json_or_empty(res)
        if not isinstance(detail, dict):
            return ""
        return detail.get("text") or detail.get("html") or detail.get("intro") or ""
