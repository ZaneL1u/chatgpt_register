"""HTTP 辅助 — Chrome 指纹、随机延迟、trace headers、PKCE。"""

from __future__ import annotations

import base64
import hashlib
import random
import secrets
import time
import uuid
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# BrowserProfile — 统一浏览器指纹数据结构
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BrowserProfile:
    """统一浏览器指纹数据结构，由 random_chrome_version() 生成。"""

    impersonate: str
    chrome_major: int
    chrome_full: str
    user_agent: str
    sec_ch_ua: str


# ---------------------------------------------------------------------------
# Chrome 指纹配置: impersonate 与 sec-ch-ua 必须匹配真实浏览器
# 每个 impersonate 值对应 2-3 个不同 patch 范围的条目，总计 10 个 profile
# ---------------------------------------------------------------------------

CHROME_PROFILES = [
    # chrome131 系列（2 个 profile）
    {
        "major": 131, "impersonate": "chrome131",
        "build": 6778, "patch_range": (69, 140),
        "sec_ch_ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    },
    {
        "major": 131, "impersonate": "chrome131",
        "build": 6778, "patch_range": (141, 205),
        "sec_ch_ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    },
    # chrome133a 系列（3 个 profile）
    {
        "major": 133, "impersonate": "chrome133a",
        "build": 6943, "patch_range": (33, 100),
        "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    },
    {
        "major": 133, "impersonate": "chrome133a",
        "build": 6943, "patch_range": (101, 200),
        "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    },
    {
        "major": 133, "impersonate": "chrome133a",
        "build": 6943, "patch_range": (201, 300),
        "sec_ch_ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    },
    # chrome136 系列（3 个 profile）
    {
        "major": 136, "impersonate": "chrome136",
        "build": 7103, "patch_range": (48, 100),
        "sec_ch_ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    },
    {
        "major": 136, "impersonate": "chrome136",
        "build": 7103, "patch_range": (101, 175),
        "sec_ch_ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    },
    {
        "major": 136, "impersonate": "chrome136",
        "build": 7103, "patch_range": (176, 250),
        "sec_ch_ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    },
    # chrome142 系列（2 个 profile）
    {
        "major": 142, "impersonate": "chrome142",
        "build": 7540, "patch_range": (30, 90),
        "sec_ch_ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    },
    {
        "major": 142, "impersonate": "chrome142",
        "build": 7540, "patch_range": (91, 150),
        "sec_ch_ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    },
]


def random_chrome_version() -> BrowserProfile:
    """随机选取 Chrome profile，返回 BrowserProfile 实例。"""
    profile = random.choice(CHROME_PROFILES)
    major = profile["major"]
    build = profile["build"]
    patch = random.randint(*profile["patch_range"])
    full_ver = f"{major}.0.{build}.{patch}"
    ua = (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{full_ver} Safari/537.36"
    )
    return BrowserProfile(
        impersonate=profile["impersonate"],
        chrome_major=major,
        chrome_full=full_ver,
        user_agent=ua,
        sec_ch_ua=profile["sec_ch_ua"],
    )


def random_delay(mean: float = 0.5, std: float = 0.15, min_bound: float = 0.2) -> None:
    """正态分布延迟，clamp 到 min_bound 下限。"""
    delay = max(min_bound, random.gauss(mean, std))
    time.sleep(delay)


def make_trace_headers() -> dict[str, str]:
    trace_id = random.randint(10**17, 10**18 - 1)
    parent_id = random.randint(10**17, 10**18 - 1)
    tp = f"00-{uuid.uuid4().hex}-{format(parent_id, '016x')}-01"
    return {
        "traceparent": tp,
        "tracestate": "dd=s:1;o:rum",
        "x-datadog-origin": "rum",
        "x-datadog-sampling-priority": "1",
        "x-datadog-trace-id": str(trace_id),
        "x-datadog-parent-id": str(parent_id),
    }


def generate_pkce() -> tuple[str, str]:
    """返回 (code_verifier, code_challenge)。"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge
