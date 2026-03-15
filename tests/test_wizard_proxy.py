"""tests/test_wizard_proxy.py — 向导多代理输入测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chatgpt_register.wizard import _ask_proxies


class TestAskProxiesSingleMode:
    """单代理输入模式。"""

    @patch("chatgpt_register.wizard.questionary")
    def test_single_valid_proxy(self, mock_q):
        mock_q.select.return_value.ask.return_value = "单个代理 (直接输入地址)"
        mock_q.text.return_value.ask.return_value = "http://host:8080"
        result = _ask_proxies([])
        assert result == ["http://host:8080"]

    @patch("chatgpt_register.wizard.questionary")
    def test_single_empty_returns_empty(self, mock_q):
        mock_q.select.return_value.ask.return_value = "单个代理 (直接输入地址)"
        mock_q.text.return_value.ask.return_value = ""
        result = _ask_proxies([])
        assert result == []

    @patch("chatgpt_register.wizard.questionary")
    def test_single_invalid_returns_empty(self, mock_q):
        mock_q.select.return_value.ask.return_value = "单个代理 (直接输入地址)"
        mock_q.text.return_value.ask.return_value = "not-a-valid-proxy"
        result = _ask_proxies([])
        assert result == []

    @patch("chatgpt_register.wizard.questionary")
    def test_single_with_prefill(self, mock_q):
        mock_q.select.return_value.ask.return_value = "单个代理 (直接输入地址)"
        mock_q.text.return_value.ask.return_value = "socks5://h:1080"
        result = _ask_proxies(["http://old:80"])
        assert result == ["socks5://h:1080"]


class TestAskProxiesSkipMode:
    """跳过模式。"""

    @patch("chatgpt_register.wizard.questionary")
    def test_skip_returns_empty(self, mock_q):
        mock_q.select.return_value.ask.return_value = "不使用代理"
        result = _ask_proxies([])
        assert result == []


class TestAskProxiesMultilineMode:
    """多行输入模式。"""

    @patch("chatgpt_register.wizard.questionary")
    def test_multiline_valid(self, mock_q):
        mock_q.select.return_value.ask.return_value = "多个代理 (逐行输入)"
        # 连续 text().ask() 返回值
        mock_q.text.return_value.ask.side_effect = [
            "socks5://h:1080",
            "http://h:8080",
            "",  # 空行结束
        ]
        result = _ask_proxies([])
        assert result == ["socks5://h:1080", "http://h:8080"]

    @patch("chatgpt_register.wizard.questionary")
    def test_multiline_with_invalid(self, mock_q):
        mock_q.select.return_value.ask.return_value = "多个代理 (逐行输入)"
        mock_q.text.return_value.ask.side_effect = [
            "socks5://h:1080",
            "bad-proxy",
            "http://h:8080",
            "",  # 空行结束
        ]
        result = _ask_proxies([])
        assert result == ["socks5://h:1080", "http://h:8080"]


class TestAskProxiesFileMode:
    """文件导入模式。"""

    @patch("chatgpt_register.wizard.questionary")
    def test_file_import(self, mock_q, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text("socks5://h:1080\nhttp://h:8080\n")
        mock_q.select.return_value.ask.return_value = "从文件导入 (.txt)"
        mock_q.text.return_value.ask.return_value = str(f)
        result = _ask_proxies([])
        assert result == ["socks5://h:1080", "http://h:8080"]

    @patch("chatgpt_register.wizard.questionary")
    def test_file_not_found(self, mock_q):
        mock_q.select.return_value.ask.return_value = "从文件导入 (.txt)"
        mock_q.text.return_value.ask.return_value = "/nonexistent/file.txt"
        result = _ask_proxies([])
        assert result == []

    @patch("chatgpt_register.wizard.questionary")
    def test_file_empty_path(self, mock_q):
        mock_q.select.return_value.ask.return_value = "从文件导入 (.txt)"
        mock_q.text.return_value.ask.return_value = ""
        result = _ask_proxies([])
        assert result == []


class TestAskProxiesCancel:
    """用户取消操作。"""

    @patch("chatgpt_register.wizard.questionary")
    def test_cancel_at_mode_select(self, mock_q):
        mock_q.select.return_value.ask.return_value = None
        result = _ask_proxies([])
        assert result is None

    @patch("chatgpt_register.wizard.questionary")
    def test_cancel_at_single_input(self, mock_q):
        mock_q.select.return_value.ask.return_value = "单个代理 (直接输入地址)"
        mock_q.text.return_value.ask.return_value = None
        result = _ask_proxies([])
        assert result is None
