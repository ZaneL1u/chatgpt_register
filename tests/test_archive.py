"""Tests for batch output archive (BATCH-01)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from chatgpt_register.core.archive import create_archive_dir, prepare_archive_paths


class TestCreateArchiveDir:
    """create_archive_dir() 归档目录生成。"""

    def test_basic(self, tmp_path: Path) -> None:
        """基本调用：返回 Path，目录存在，格式为 YYYYMMDD_HHMM。"""
        with patch("chatgpt_register.core.archive.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260315_1430"
            result = create_archive_dir(base=str(tmp_path))

        assert isinstance(result, Path)
        assert result.exists()
        assert result.is_dir()
        assert result.name == "20260315_1430"
        assert result.parent == tmp_path

    def test_collision(self, tmp_path: Path) -> None:
        """同一分钟内调用两次，第二次追加 _2 后缀。"""
        with patch("chatgpt_register.core.archive.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260315_1430"
            first = create_archive_dir(base=str(tmp_path))
            second = create_archive_dir(base=str(tmp_path))

        assert first.name == "20260315_1430"
        assert second.name == "20260315_1430_2"
        assert first.exists()
        assert second.exists()

    def test_triple_collision(self, tmp_path: Path) -> None:
        """三次调用分别返回无后缀、_2、_3。"""
        with patch("chatgpt_register.core.archive.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260315_1430"
            first = create_archive_dir(base=str(tmp_path))
            second = create_archive_dir(base=str(tmp_path))
            third = create_archive_dir(base=str(tmp_path))

        assert first.name == "20260315_1430"
        assert second.name == "20260315_1430_2"
        assert third.name == "20260315_1430_3"

    def test_custom_base(self, tmp_path: Path) -> None:
        """传入自定义 base 路径，目录在该路径下创建。"""
        custom_base = tmp_path / "custom_output"
        with patch("chatgpt_register.core.archive.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260315_1500"
            result = create_archive_dir(base=str(custom_base))

        assert result.parent == custom_base
        assert result.exists()
        assert result.name == "20260315_1500"


class TestPrepareArchivePaths:
    """prepare_archive_paths() 路径重定向。"""

    def test_basic(self, tmp_path: Path) -> None:
        """所有返回路径都在 archive_dir 下。"""
        archive_dir = tmp_path / "20260315_1430"
        archive_dir.mkdir(parents=True)

        result = prepare_archive_paths(
            archive_dir,
            output_file="registered_accounts.txt",
            ak_file="ak.txt",
            rk_file="rk.txt",
            token_json_dir="codex_tokens",
            log_file="batch.log",
        )

        for key, path_str in result.items():
            assert str(archive_dir) in path_str, f"{key} not under archive_dir"

    def test_strips_prefix(self, tmp_path: Path) -> None:
        """output_file 含路径前缀时只取 basename。"""
        archive_dir = tmp_path / "20260315_1430"
        archive_dir.mkdir(parents=True)

        result = prepare_archive_paths(
            archive_dir,
            output_file="some/path/accounts.txt",
            ak_file="another/dir/ak.txt",
            rk_file="rk.txt",
            token_json_dir="deep/nested/codex_tokens",
            log_file="logs/batch.log",
        )

        assert result["output_file"] == str(archive_dir / "accounts.txt")
        assert result["ak_file"] == str(archive_dir / "ak.txt")
        assert result["rk_file"] == str(archive_dir / "rk.txt")
        assert result["token_json_dir"] == str(archive_dir / "codex_tokens")
        assert result["log_file"] == str(archive_dir / "batch.log")

    def test_default_log(self, tmp_path: Path) -> None:
        """log_file 为空时默认生成 batch.log。"""
        archive_dir = tmp_path / "20260315_1430"
        archive_dir.mkdir(parents=True)

        result = prepare_archive_paths(
            archive_dir,
            output_file="registered_accounts.txt",
            ak_file="ak.txt",
            rk_file="rk.txt",
            token_json_dir="codex_tokens",
            log_file="",
        )

        assert result["log_file"] == str(archive_dir / "batch.log")
