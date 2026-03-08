from __future__ import annotations

from pathlib import Path

from chatgpt_register import cli
from chatgpt_register.config.model import RegisterConfig


class _TTY:
    def isatty(self) -> bool:
        return True

    def write(self, text: str) -> int:
        return len(text)

    def flush(self) -> None:
        return None


def test_cli_uses_wizard_for_interactive_tty(monkeypatch, tmp_profiles_dir: Path) -> None:
    launched = {}

    monkeypatch.setattr(cli.sys, "stdin", _TTY())
    monkeypatch.setattr(cli.sys, "stdout", _TTY())
    monkeypatch.setattr(cli, "run_batch", lambda config: launched.setdefault("ran", config))

    def fake_launch(profile_manager):
        launched["profile_manager"] = profile_manager
        return None

    monkeypatch.setattr(cli, "_launch_wizard", fake_launch)

    result = cli.main(["--profiles-dir", str(tmp_profiles_dir)])

    assert result == 0
    assert launched["profile_manager"].base_dir == tmp_profiles_dir.resolve()
    assert "ran" not in launched


def test_cli_runs_batch_with_wizard_result(monkeypatch, tmp_profiles_dir: Path, sample_mailtm_dict: dict) -> None:
    launched = {}
    config = RegisterConfig.model_validate(sample_mailtm_dict)

    monkeypatch.setattr(cli.sys, "stdin", _TTY())
    monkeypatch.setattr(cli.sys, "stdout", _TTY())
    monkeypatch.setattr(cli, "_launch_wizard", lambda profile_manager: config)
    monkeypatch.setattr(cli, "run_batch", lambda built: launched.setdefault("config", built))

    result = cli.main(["--profiles-dir", str(tmp_profiles_dir)])

    assert result == 0
    assert launched["config"] == config
