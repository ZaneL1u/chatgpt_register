"""核心注册流程 — ChatGPTRegister。"""

from __future__ import annotations

import base64
import json
import random
import re
import secrets
import threading
import time
import traceback
import uuid
from typing import Optional
from urllib.parse import urlencode, urlparse

from curl_cffi import requests as curl_requests

from chatgpt_register.adapters import build_email_adapter
from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.core.http import (
    generate_pkce,
    make_trace_headers,
    random_chrome_version,
    random_delay,
)
from chatgpt_register.core.sentinel import build_sentinel_token
from chatgpt_register.core.tokens import save_codex_tokens
from chatgpt_register.core.utils import (
    extract_code_from_url,
    extract_verification_code,
    random_birthdate,
    random_name,
    translate_step_to_cn,
)
from chatgpt_register.upload import upload_token_data


class ChatGPTRegister:
    BASE = "https://chatgpt.com"
    AUTH = "https://auth.openai.com"

    def __init__(
        self,
        config: RegisterConfig,
        proxy: str | None = None,
        tag: str = "",
        worker_id: Optional[int] = None,
        dashboard=None,
        print_lock: threading.Lock | None = None,
        file_lock: threading.Lock | None = None,
    ):
        self.config = config
        self.tag = tag
        self.worker_id = worker_id
        self.dashboard = dashboard
        self.print_lock = print_lock or threading.Lock()
        self.file_lock = file_lock or threading.Lock()
        self.device_id = str(uuid.uuid4())
        self.auth_session_logging_id = str(uuid.uuid4())
        self.impersonate, self.chrome_major, self.chrome_full, self.ua, self.sec_ch_ua = random_chrome_version()

        self.session = curl_requests.Session(impersonate=self.impersonate)

        self.proxy = proxy if proxy is not None else (config.registration.proxy or None)
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}

        self.session.headers.update({
            "User-Agent": self.ua,
            "Accept-Language": random.choice([
                "en-US,en;q=0.9", "en-US,en;q=0.9,zh-CN;q=0.8",
                "en,en-US;q=0.9", "en-US,en;q=0.8",
            ]),
            "sec-ch-ua": self.sec_ch_ua,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": f'"{self.chrome_full}"',
            "sec-ch-ua-platform-version": f'"{random.randint(10, 15)}.0.0"',
        })

        self.session.cookies.set("oai-did", self.device_id, domain="chatgpt.com")
        self._callback_url = None
        self.email_adapter = build_email_adapter(self, config)

    def _provider_label(self) -> str:
        labels = {
            "duckmail": "DuckMail",
            "mailcow": "Mailcow",
            "mailtm": "Mail.tm",
        }
        return labels.get(self.config.email.provider, self.config.email.provider or "Unknown")

    def _log(self, step, method, url, status, body=None):
        if self.dashboard is not None and self.worker_id is not None:
            self.dashboard.update_worker(
                self.worker_id,
                f"步骤: {translate_step_to_cn(step)}",
                tag=self.tag,
            )

        prefix = f"[{self.tag}] " if self.tag else ""
        lines = [
            f"\n{'='*60}",
            f"{prefix}[Step] {step}",
            f"{prefix}[{method}] {url}",
            f"{prefix}[Status] {status}",
        ]
        if body:
            try:
                lines.append(f"{prefix}[Response] {json.dumps(body, indent=2, ensure_ascii=False)[:1000]}")
            except Exception:
                lines.append(f"{prefix}[Response] {str(body)[:1000]}")
        lines.append(f"{'='*60}")
        with self.print_lock:
            print("\n".join(lines))

    def _print(self, msg):
        if self.dashboard is not None and self.worker_id is not None:
            self.dashboard.update_worker(self.worker_id, msg, tag=self.tag)

        prefix = f"[{self.tag}] " if self.tag else ""
        with self.print_lock:
            print(f"{prefix}{msg}")

    def _create_email_http_session(self):
        session = curl_requests.Session()
        session.headers.update({
            "User-Agent": self.ua,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        if self.proxy:
            session.proxies = {"http": self.proxy, "https": self.proxy}
        return session

    def create_temp_email(self):
        return self.email_adapter.create_temp_email()

    def _fetch_emails(self, mail_token: str):
        try:
            return self.email_adapter.fetch_messages(mail_token) or []
        except Exception:
            return []

    def _extract_message_content(self, mail_token: str, message: dict):
        try:
            return self.email_adapter.extract_message_content(mail_token, message) or ""
        except Exception:
            return ""

    def wait_for_verification_email(self, mail_token: str, timeout: int = 120):
        provider = self._provider_label()
        self._print(f"[OTP] 等待验证码邮件 via {provider} (最多 {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            messages = self._fetch_emails(mail_token)
            for msg in messages[:12]:
                content = self._extract_message_content(mail_token, msg)
                code = extract_verification_code(content)
                if code:
                    self._print(f"[OTP] 验证码: {code}")
                    return code

            elapsed = int(time.time() - start_time)
            self._print(f"[OTP] 等待中... ({elapsed}s/{timeout}s)")
            time.sleep(3)

        self._print(f"[OTP] 超时 ({timeout}s)")
        return None

    def visit_homepage(self):
        url = f"{self.BASE}/"
        r = self.session.get(url, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        }, allow_redirects=True)
        self._log("0. Visit homepage", "GET", url, r.status_code, {"cookies_count": len(self.session.cookies)})

    def get_csrf(self) -> str:
        url = f"{self.BASE}/api/auth/csrf"
        r = self.session.get(url, headers={"Accept": "application/json", "Referer": f"{self.BASE}/"})
        data = r.json()
        token = data.get("csrfToken", "")
        self._log("1. Get CSRF", "GET", url, r.status_code, data)
        if not token:
            raise Exception("Failed to get CSRF token")
        return token

    def signin(self, email: str, csrf: str) -> str:
        url = f"{self.BASE}/api/auth/signin/openai"
        params = {
            "prompt": "login", "ext-oai-did": self.device_id,
            "auth_session_logging_id": self.auth_session_logging_id,
            "screen_hint": "login_or_signup", "login_hint": email,
        }
        form_data = {"callbackUrl": f"{self.BASE}/", "csrfToken": csrf, "json": "true"}
        r = self.session.post(url, params=params, data=form_data, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json", "Referer": f"{self.BASE}/", "Origin": self.BASE,
        })
        data = r.json()
        authorize_url = data.get("url", "")
        self._log("2. Signin", "POST", url, r.status_code, data)
        if not authorize_url:
            raise Exception("Failed to get authorize URL")
        return authorize_url

    def authorize(self, url: str) -> str:
        r = self.session.get(url, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"{self.BASE}/", "Upgrade-Insecure-Requests": "1",
        }, allow_redirects=True)
        final_url = str(r.url)
        self._log("3. Authorize", "GET", url, r.status_code, {"final_url": final_url})
        return final_url

    def register(self, email: str, password: str):
        url = f"{self.AUTH}/api/accounts/user/register"
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "Referer": f"{self.AUTH}/create-account/password", "Origin": self.AUTH}
        headers.update(make_trace_headers())
        r = self.session.post(url, json={"username": email, "password": password}, headers=headers)
        try:
            data = r.json()
        except Exception:
            data = {"text": r.text[:500]}
        self._log("4. Register", "POST", url, r.status_code, data)
        return r.status_code, data

    def send_otp(self):
        url = f"{self.AUTH}/api/accounts/email-otp/send"
        r = self.session.get(url, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"{self.AUTH}/create-account/password", "Upgrade-Insecure-Requests": "1",
        }, allow_redirects=True)
        try:
            data = r.json()
        except Exception:
            data = {"final_url": str(r.url), "status": r.status_code}
        self._log("5. Send OTP", "GET", url, r.status_code, data)
        return r.status_code, data

    def validate_otp(self, code: str):
        url = f"{self.AUTH}/api/accounts/email-otp/validate"
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "Referer": f"{self.AUTH}/email-verification", "Origin": self.AUTH}
        headers.update(make_trace_headers())
        r = self.session.post(url, json={"code": code}, headers=headers)
        try:
            data = r.json()
        except Exception:
            data = {"text": r.text[:500]}
        self._log("6. Validate OTP", "POST", url, r.status_code, data)
        return r.status_code, data

    def create_account(self, name: str, birthdate: str):
        url = f"{self.AUTH}/api/accounts/create_account"
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "Referer": f"{self.AUTH}/about-you", "Origin": self.AUTH}
        headers.update(make_trace_headers())
        r = self.session.post(url, json={"name": name, "birthdate": birthdate}, headers=headers)
        try:
            data = r.json()
        except Exception:
            data = {"text": r.text[:500]}
        self._log("7. Create Account", "POST", url, r.status_code, data)
        if isinstance(data, dict):
            cb = data.get("continue_url") or data.get("url") or data.get("redirect_url")
            if cb:
                self._callback_url = cb
        return r.status_code, data

    def callback(self, url: str = None):
        if not url:
            url = self._callback_url
        if not url:
            self._print("[!] No callback URL, skipping.")
            return None, None
        r = self.session.get(url, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        }, allow_redirects=True)
        self._log("8. Callback", "GET", url, r.status_code, {"final_url": str(r.url)})
        return r.status_code, {"final_url": str(r.url)}

    def run_register(self, email, password, name, birthdate, mail_token):
        self.visit_homepage()
        random_delay(0.3, 0.8)
        csrf = self.get_csrf()
        random_delay(0.2, 0.5)
        auth_url = self.signin(email, csrf)
        random_delay(0.3, 0.8)

        final_url = self.authorize(auth_url)
        final_path = urlparse(final_url).path
        random_delay(0.3, 0.8)

        self._print(f"Authorize -> {final_path}")

        need_otp = False

        if "create-account/password" in final_path:
            self._print("全新注册流程")
            random_delay(0.5, 1.0)
            status, data = self.register(email, password)
            if status != 200:
                raise Exception(f"Register 失败 ({status}): {data}")
            random_delay(0.3, 0.8)
            self.send_otp()
            need_otp = True
        elif "email-verification" in final_path or "email-otp" in final_path:
            self._print("跳到 OTP 验证阶段 (authorize 已触发 OTP，不再重复发送)")
            need_otp = True
        elif "about-you" in final_path:
            self._print("跳到填写信息阶段")
            random_delay(0.5, 1.0)
            self.create_account(name, birthdate)
            random_delay(0.3, 0.5)
            self.callback()
            return True
        elif "callback" in final_path or "chatgpt.com" in final_url:
            self._print("账号已完成注册")
            return True
        else:
            self._print(f"未知跳转: {final_url}")
            self.register(email, password)
            self.send_otp()
            need_otp = True

        if need_otp:
            otp_code = self.wait_for_verification_email(mail_token)
            if not otp_code:
                raise Exception("未能获取验证码")

            random_delay(0.3, 0.8)
            status, data = self.validate_otp(otp_code)
            if status != 200:
                self._print("验证码失败，重试...")
                self.send_otp()
                random_delay(1.0, 2.0)
                otp_code = self.wait_for_verification_email(mail_token, timeout=60)
                if not otp_code:
                    raise Exception("重试后仍未获取验证码")
                random_delay(0.3, 0.8)
                status, data = self.validate_otp(otp_code)
                if status != 200:
                    raise Exception(f"验证码失败 ({status}): {data}")

        random_delay(0.5, 1.5)
        status, data = self.create_account(name, birthdate)
        if status != 200:
            raise Exception(f"Create account 失败 ({status}): {data}")
        random_delay(0.2, 0.5)
        self.callback()
        return True

    # 为控制篇幅，OAuth 逻辑保留最小兼容实现
    def perform_codex_oauth_login_http(self, email: str, password: str, mail_token: str = None):
        self._print("[OAuth] 开始执行 Codex OAuth 纯协议流程...")
        self.session.cookies.set("oai-did", self.device_id, domain=".auth.openai.com")
        self.session.cookies.set("oai-did", self.device_id, domain="auth.openai.com")

        code_verifier, code_challenge = generate_pkce()
        state = secrets.token_urlsafe(24)
        oauth = self.config.oauth

        authorize_params = {
            "response_type": "code",
            "client_id": oauth.client_id,
            "redirect_uri": oauth.redirect_uri,
            "scope": "openid profile email offline_access",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        authorize_url = f"{oauth.issuer.rstrip('/')}/oauth/authorize?{urlencode(authorize_params)}"

        try:
            r = self.session.get(authorize_url, allow_redirects=True, timeout=30, impersonate=self.impersonate)
            final_url = str(r.url)
        except Exception as e:
            self._print(f"[OAuth] /oauth/authorize 异常: {e}")
            return None

        code = extract_code_from_url(final_url)
        if not code:
            self._print("[OAuth] 未获取到 authorization code")
            return None

        token_resp = self.session.post(
            f"{oauth.issuer.rstrip('/')}/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": self.ua},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": oauth.redirect_uri,
                "client_id": oauth.client_id,
                "code_verifier": code_verifier,
            },
            timeout=60,
            impersonate=self.impersonate,
        )
        self._print(f"[OAuth] /oauth/token -> {token_resp.status_code}")

        if token_resp.status_code != 200:
            self._print(f"[OAuth] token 交换失败: {token_resp.status_code} {token_resp.text[:200]}")
            return None

        try:
            data = token_resp.json()
        except Exception:
            self._print("[OAuth] token 响应解析失败")
            return None

        if not data.get("access_token"):
            self._print("[OAuth] token 响应缺少 access_token")
            return None

        self._print("[OAuth] Codex Token 获取成功")
        return data

    def save_tokens(self, email: str, tokens: dict) -> None:
        upload_config = self.config.upload
        save_codex_tokens(
            email,
            tokens,
            ak_file=self.config.registration.ak_file,
            rk_file=self.config.registration.rk_file,
            token_json_dir=self.config.registration.token_json_dir,
            upload_fn=lambda e, td, fp: upload_token_data(
                email=e,
                token_data=td,
                filepath=fp,
                config=upload_config,
                proxy=self.proxy or "",
                print_lock=self.print_lock,
            ),
            file_lock=self.file_lock,
            print_lock=self.print_lock,
        )
