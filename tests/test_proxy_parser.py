"""tests/test_proxy_parser.py — 代理地址解析模块测试。"""

from __future__ import annotations

import os
import tempfile

import pytest

from chatgpt_register.core.proxy_parser import (
    parse_proxies,
    parse_proxies_from_file,
    parse_proxy,
    summarize_proxies,
)


# ---------------------------------------------------------------------------
# parse_proxy
# ---------------------------------------------------------------------------


class TestParseProxy:
    def test_socks5_full(self):
        assert parse_proxy("socks5://user:pass@host:1080") == "socks5://user:pass@host:1080"

    def test_http_host_port(self):
        assert parse_proxy("http://host:8080") == "http://host:8080"

    def test_bare_host_port_defaults_http(self):
        assert parse_proxy("host:8080") == "http://host:8080"

    def test_socks4(self):
        assert parse_proxy("socks4://host:1080") == "socks4://host:1080"

    def test_https(self):
        assert parse_proxy("https://host:443") == "https://host:443"

    def test_unsupported_scheme_returns_none(self):
        assert parse_proxy("ftp://host:21") is None

    def test_empty_string_returns_none(self):
        assert parse_proxy("") is None

    def test_whitespace_returns_none(self):
        assert parse_proxy("   ") is None

    def test_no_hostname_returns_none(self):
        assert parse_proxy("http://") is None

    def test_strips_whitespace(self):
        assert parse_proxy("  http://host:8080  ") == "http://host:8080"

    def test_socks5_no_auth(self):
        assert parse_proxy("socks5://host:1080") == "socks5://host:1080"


# ---------------------------------------------------------------------------
# parse_proxies
# ---------------------------------------------------------------------------


class TestParseProxies:
    def test_mixed_valid_invalid(self):
        lines = ["socks5://h:1080", "", "bad-no-port", "http://h:80"]
        valid, warnings = parse_proxies(lines)
        assert valid == ["socks5://h:1080", "http://h:80"]
        assert len(warnings) == 1  # "bad-no-port" (empty is skipped silently)

    def test_all_valid(self):
        lines = ["http://a:80", "socks5://b:1080"]
        valid, warnings = parse_proxies(lines)
        assert valid == ["http://a:80", "socks5://b:1080"]
        assert warnings == []

    def test_empty_list(self):
        valid, warnings = parse_proxies([])
        assert valid == []
        assert warnings == []

    def test_all_empty_lines(self):
        valid, warnings = parse_proxies(["", "  ", ""])
        assert valid == []
        assert warnings == []


# ---------------------------------------------------------------------------
# parse_proxies_from_file
# ---------------------------------------------------------------------------


class TestParseProxiesFromFile:
    def test_reads_file(self, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text("socks5://h:1080\nhttp://h:80\n")
        valid, warnings = parse_proxies_from_file(str(f))
        assert valid == ["socks5://h:1080", "http://h:80"]
        assert warnings == []

    def test_skips_comments(self, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text("# this is a comment\nsocks5://h:1080\n# another\nhttp://h:80\n")
        valid, warnings = parse_proxies_from_file(str(f))
        assert valid == ["socks5://h:1080", "http://h:80"]
        assert warnings == []

    def test_skips_blank_lines(self, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text("\n\nsocks5://h:1080\n\n")
        valid, warnings = parse_proxies_from_file(str(f))
        assert valid == ["socks5://h:1080"]

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_proxies_from_file("/nonexistent/path.txt")


# ---------------------------------------------------------------------------
# summarize_proxies
# ---------------------------------------------------------------------------


class TestSummarizeProxies:
    def test_mixed(self):
        result = summarize_proxies(["socks5://h:1", "http://h:2", "socks5://h:3"])
        assert "2" in result and "SOCKS5" in result and "1" in result and "HTTP" in result

    def test_single_http(self):
        result = summarize_proxies(["http://h:80"])
        assert "1" in result and "HTTP" in result

    def test_empty(self):
        assert summarize_proxies([]) == "无代理"

    def test_bare_host_counted_as_http(self):
        # bare host:port would have been normalized to http:// by parse_proxy
        result = summarize_proxies(["http://h:80"])
        assert "HTTP" in result
