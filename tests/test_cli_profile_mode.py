from __future__ import annotations

from pathlib import Path

from chatgpt_register import cli
from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.config.profile import ProfileManager


class _NonTTY:
    def isatty(self) -> bool:
        return False

    def write(self, text: str) -> int:
        return len(text)

    def flush(self) -> None:
        return None


def _save_profile(base_dir: Path, name: str, payload: dict) -> None:
    manager = ProfileManager(base_dir=base_dir)
    manager.save(name, RegisterConfig.model_validate(payload))


def test_cli_runs_batch_with_named_profile(monkeypatch, tmp_profiles_dir: Path, sample_duckmail_dict: dict) -> None:
    launched = {}
    _save_profile(tmp_profiles_dir, "duckmail-prod", sample_duckmail_dict)

    monkeypatch.setattr(cli, "run_batch", lambda config: launched.setdefault("config", config))

    result = cli.main(["--profile", "duckmail-prod", "--profiles-dir", str(tmp_profiles_dir)])

    assert result == 0
    assert launched["config"].email.provider == "duckmail"
    assert launched["config"].registration.total_accounts == 5


def test_cli_requires_profile_for_non_interactive_mode(
    monkeypatch,
    tmp_profiles_dir: Path,
    capsys,
) -> None:
    monkeypatch.setattr(cli.sys, "stdin", _NonTTY())

    result = cli.main(["--non-interactive", "--profiles-dir", str(tmp_profiles_dir)])

    captured = capsys.readouterr()
    assert result == 2
    assert "--profile <name>" in captured.out


def test_cli_warns_about_legacy_config_without_loading(
    monkeypatch,
    tmp_path: Path,
    tmp_profiles_dir: Path,
    sample_duckmail_dict: dict,
    capsys,
) -> None:
    launched = {}
    _save_profile(tmp_profiles_dir, "duckmail-prod", sample_duckmail_dict)
    (tmp_path / "config.json").write_text("{ invalid json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "run_batch", lambda config: launched.setdefault("config", config))

    result = cli.main(["--profile", "duckmail-prod", "--profiles-dir", str(tmp_profiles_dir)])

    captured = capsys.readouterr()
    assert result == 0
    assert "config.json" in captured.out
    assert "不再加载 JSON 配置" in captured.out
    assert launched["config"].email.provider == "duckmail"
