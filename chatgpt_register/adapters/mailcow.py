"""Mailcow 邮箱适配器 — 包含 IMAP 操作函数。"""

from __future__ import annotations

import email as email_lib
import imaplib
import random
import string
from email.header import decode_header

from curl_cffi import requests as curl_requests

from chatgpt_register.adapters.base import EmailAdapter
from chatgpt_register.config.model import MailcowConfig
from chatgpt_register.core.utils import generate_password


# ---------------------------------------------------------------------------
# Mailcow 独立函数
# ---------------------------------------------------------------------------


def _mailcow_create_mailbox(email_addr: str, password: str, config: MailcowConfig):
    """通过 Mailcow API 创建邮箱"""
    if not config.api_url or not config.api_key:
        raise Exception("Mailcow API 配置不完整 (api_url / api_key)")

    api_url = config.api_url.rstrip("/")
    local_part, domain = email_addr.split("@", 1)
    payload = {
        "local_part": local_part,
        "domain": domain,
        "password": password,
        "password2": password,
        "active": "1",
        "quota": "0",
        "force_pw_update": "0",
        "tls_enforce_in": "0",
        "tls_enforce_out": "0",
    }

    resp = curl_requests.post(
        f"{api_url}/api/v1/add/mailbox",
        json=payload,
        headers={
            "X-API-Key": config.api_key,
            "Content-Type": "application/json",
        },
        timeout=15,
    )

    if resp.status_code not in [200, 201]:
        raise Exception(f"Mailcow 创建邮箱失败: {resp.status_code} - {resp.text[:300]}")

    data = resp.json()
    if isinstance(data, list) and data:
        if data[0].get("type") == "danger":
            raise Exception(f"Mailcow 创建邮箱失败: {data[0].get('msg', '')}")

    return True


def _mailcow_delete_mailbox(email_addr: str, config: MailcowConfig):
    """通过 Mailcow API 删除邮箱"""
    api_url = config.api_url.rstrip("/")
    try:
        resp = curl_requests.post(
            f"{api_url}/api/v1/delete/mailbox",
            json=[email_addr],
            headers={
                "X-API-Key": config.api_key,
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        return resp.status_code in [200, 201]
    except Exception:
        return False


def _extract_email_body(msg):
    """从 email.message.Message 提取纯文本或 HTML 内容"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
            elif ct == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return body


def _mailcow_imap_fetch_latest(email_addr: str, password: str, config: MailcowConfig, timeout: int = 10):
    """通过 IMAP 获取最新邮件的文本内容"""
    imap_host = config.imap_host
    imap_port = config.imap_port

    if not imap_host:
        raise Exception("Mailcow IMAP host 未配置")

    conn = None
    try:
        conn = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=timeout)
        conn.login(email_addr, password)
        conn.select("INBOX")

        status, data = conn.search(None, "ALL")
        if status != "OK" or not data[0]:
            return []

        msg_ids = data[0].split()
        results = []
        for mid in msg_ids[-5:]:
            status, msg_data = conn.fetch(mid, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            body = _extract_email_body(msg)
            if body:
                results.append(body)

        return results

    except imaplib.IMAP4.error:
        return []
    finally:
        if conn:
            try:
                conn.logout()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# MailcowAdapter
# ---------------------------------------------------------------------------


class MailcowAdapter(EmailAdapter):
    provider = "mailcow"

    def __init__(self, register, email_config: MailcowConfig):
        super().__init__(register)
        self.config = email_config
        # 自动推断 IMAP host
        if self.config.api_url and not self.config.imap_host:
            from urllib.parse import urlparse
            self.config = self.config.model_copy(
                update={"imap_host": urlparse(self.config.api_url).hostname or ""}
            )

    def create_temp_email(self):
        if not self.config.domain:
            raise Exception("MAILCOW_DOMAIN 未设置")
        chars = string.ascii_lowercase + string.digits
        email_local = "".join(random.choice(chars) for _ in range(random.randint(8, 13)))
        email_addr = f"{email_local}@{self.config.domain}"
        password = generate_password()
        _mailcow_create_mailbox(email_addr, password, self.config)
        return email_addr, password, f"mailcow:{email_addr}:{password}"

    def fetch_messages(self, mail_token: str):
        parts = mail_token.split(":", 2)
        if len(parts) != 3 or parts[0] != "mailcow":
            return []
        email_addr, password = parts[1], parts[2]
        bodies = _mailcow_imap_fetch_latest(email_addr, password, self.config)
        return [{"id": str(i), "_body": body} for i, body in enumerate(bodies)]

    def extract_message_content(self, mail_token: str, message: dict):
        return (message or {}).get("_body", "")

    def delete_mailbox(self, email_addr: str) -> bool:
        """删除 Mailcow 邮箱（清理用）。"""
        return _mailcow_delete_mailbox(email_addr, self.config)
