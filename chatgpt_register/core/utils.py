"""纯工具函数 — 无外部依赖、无全局状态。"""

from __future__ import annotations

import base64
import json
import random
import re
import string
from urllib.parse import parse_qs, urlparse


# ---------------------------------------------------------------------------
# 文本 / 格式辅助
# ---------------------------------------------------------------------------


def plain_print(*args, **kwargs):
    """始终使用原始 builtins.print，不受 dashboard 劫持影响。"""
    import builtins

    builtins.print(*args, **kwargs)


def provider_display_name(provider: str) -> str:
    """将 provider key 转换为显示名称。"""
    mapping = {
        "duckmail": "DuckMail",
        "mailcow": "Mailcow",
        "mailtm": "Mail.tm",
        "catchmail": "Catchmail.io",
        "maildrop": "Maildrop.cc",
    }
    return mapping.get((provider or "").lower(), provider or "Unknown")


def translate_step_to_cn(step: str) -> str:
    mapping = {
        "Visit homepage": "访问首页",
        "Get CSRF": "获取 CSRF",
        "Signin": "提交登录",
        "Authorize": "授权跳转",
        "Register": "提交注册",
        "Send OTP": "发送验证码请求",
        "Validate OTP": "校验验证码",
        "Create Account": "创建账号",
        "Callback": "回调确认",
    }
    text = str(step or "").strip()
    for key, value in mapping.items():
        if key in text:
            return value
    return text or "处理中"


def sanitize_status_text(text: str, limit: int = 40) -> str:
    raw = re.sub(r"^\[[^\]]+\]\s*", "", str(text or "").strip())
    if not raw:
        return "处理中"
    raw = raw.replace("\n", " ")
    return raw if len(raw) <= limit else f"{raw[:limit - 1]}..."


# ---------------------------------------------------------------------------
# 数值解析
# ---------------------------------------------------------------------------


def as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def parse_int_list(value) -> list[int]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        text = str(value).strip()
        if not text:
            return []
        items = [part for part in re.split(r"[,\s]+", text) if part]

    out: list[int] = []
    for item in items:
        try:
            num = int(item)
            if num > 0:
                out.append(num)
        except Exception:
            continue

    # 去重并保持顺序
    return list(dict.fromkeys(out))


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# 密码 / 随机数据
# ---------------------------------------------------------------------------


def generate_password(length: int = 14) -> str:
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%&*"
    pwd = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special),
    ]
    all_chars = lower + upper + digits + special
    pwd += [random.choice(all_chars) for _ in range(length - 4)]
    random.shuffle(pwd)
    return "".join(pwd)


def random_name() -> str:
    first = random.choice([
        "James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia",
        "Lucas", "Mia", "Mason", "Isabella", "Logan", "Charlotte", "Alexander",
        "Amelia", "Benjamin", "Harper", "William", "Evelyn", "Henry", "Abigail",
        "Sebastian", "Emily", "Jack", "Elizabeth",
    ])
    last = random.choice([
        "Smith", "Johnson", "Brown", "Davis", "Wilson", "Moore", "Taylor",
        "Clark", "Hall", "Young", "Anderson", "Thomas", "Jackson", "White",
        "Harris", "Martin", "Thompson", "Garcia", "Robinson", "Lewis",
        "Walker", "Allen", "King", "Wright", "Scott", "Green",
    ])
    return f"{first} {last}"


def random_birthdate() -> str:
    y = random.randint(1985, 2002)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y}-{m:02d}-{d:02d}"


# ---------------------------------------------------------------------------
# JSON / URL 辅助
# ---------------------------------------------------------------------------


def safe_json_loads(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        try:
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw or "")
            return json.loads(cleaned)
        except Exception:
            return {}


def extract_code_from_url(url: str):
    """从 URL query 中提取 code 参数。"""
    if not url or "code=" not in url:
        return None
    try:
        return parse_qs(urlparse(url).query).get("code", [None])[0]
    except Exception:
        return None


def decode_jwt_payload(token: str) -> dict:
    """解码 JWT payload 部分（不验证签名）。"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 邮件验证码提取
# ---------------------------------------------------------------------------


def extract_verification_code(email_content: str):
    """从邮件内容提取 6 位验证码。"""
    if not email_content:
        return None

    patterns = [
        r"Verification code:?\s*(\d{6})",
        r"code is\s*(\d{6})",
        r"代码为[:：]?\s*(\d{6})",
        r"验证码[:：]?\s*(\d{6})",
        r">\s*(\d{6})\s*<",
        r"(?<![#&])\b(\d{6})\b",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, email_content, re.IGNORECASE)
        for code in matches:
            if code == "177010":  # 已知误判
                continue
            return code
    return None
