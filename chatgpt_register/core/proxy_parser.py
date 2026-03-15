"""代理地址解析与校验模块。

提供代理 URL 解析、批量解析、文件导入和摘要统计功能。
支持 http、https、socks4、socks5 协议。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED_SCHEMES = {"http", "https", "socks4", "socks5"}

_SCHEME_DISPLAY = {
    "http": "HTTP",
    "https": "HTTPS",
    "socks4": "SOCKS4",
    "socks5": "SOCKS5",
}


def parse_proxy(raw: str) -> str | None:
    """解析并标准化单个代理地址。

    支持格式：
    - socks5://user:pass@host:port
    - http://host:port
    - host:port （默认补 http://）

    返回标准化后的 URL 字符串，无效时返回 None。
    """
    raw = raw.strip()
    if not raw:
        return None

    # 无 scheme 时默认 http
    if "://" not in raw:
        raw = f"http://{raw}"

    parsed = urlparse(raw)

    if parsed.scheme not in SUPPORTED_SCHEMES:
        return None

    if not parsed.hostname:
        return None

    # 代理地址必须包含端口号
    if parsed.port is None:
        return None

    return raw


def parse_proxies(lines: list[str]) -> tuple[list[str], list[str]]:
    """批量解析代理地址列表。

    返回 (valid_proxies, warnings)。
    空行被静默跳过，无效行生成警告消息。
    """
    valid: list[str] = []
    warnings: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        result = parse_proxy(stripped)
        if result is not None:
            valid.append(result)
        else:
            warnings.append(f"无效代理地址，已跳过: {stripped}")

    return valid, warnings


def parse_proxies_from_file(path: str) -> tuple[list[str], list[str]]:
    """从文件读取代理地址列表。

    每行一个代理地址，跳过空行和 # 开头的注释行。
    文件不存在时抛出 FileNotFoundError。
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"代理列表文件不存在: {path}")

    lines = file_path.read_text(encoding="utf-8").splitlines()
    # 过滤注释行
    filtered = [line for line in lines if not line.strip().startswith("#")]
    return parse_proxies(filtered)


def summarize_proxies(proxies: list[str]) -> str:
    """生成代理列表的协议分组摘要。

    返回如 "2 个 SOCKS5 + 1 个 HTTP" 格式的字符串。
    空列表返回 "无代理"。
    """
    if not proxies:
        return "无代理"

    schemes: list[str] = []
    for proxy in proxies:
        parsed = urlparse(proxy)
        schemes.append(parsed.scheme)

    counter = Counter(schemes)
    parts = []
    for scheme, count in counter.most_common():
        display = _SCHEME_DISPLAY.get(scheme, scheme.upper())
        parts.append(f"{count} 个 {display}")

    return " + ".join(parts)
