from __future__ import annotations

from types import SimpleNamespace

from chatgpt_register import cli
from chatgpt_register.config.model import RegisterConfig


class _TTY:
    def isatty(self) -> bool:
        return True

    def write(self, text: str) -> int:
        return len(text)

    def flush(self) -> None:
        return None


def test_cli_uses_tui_for_interactive_tty(monkeypatch, sample_mailtm_dict: dict) -> None:
    launched = {}

    monkeypatch.setattr(cli, "_load_legacy_config", lambda: {})
    monkeypatch.setattr(cli, "_legacy_to_register_config_dict", lambda raw: sample_mailtm_dict)
    monkeypatch.setattr(cli.sys, "stdin", _TTY())
    monkeypatch.setattr(cli.sys, "stdout", _TTY())
    monkeypatch.setattr(cli, "run_batch", lambda config: launched.setdefault("ran", config))

    def fake_launch(config_dict):
        launched["launched"] = config_dict
        return None

    monkeypatch.setattr(cli, "_launch_tui", fake_launch)

    result = cli.main([])

    assert result == 0
    assert launched["launched"]["email"]["provider"] == "mailtm"
    assert "ran" not in launched


def test_cli_runs_batch_with_tui_result(monkeypatch, sample_mailtm_dict: dict) -> None:
    launched = {}
    config = RegisterConfig.model_validate(sample_mailtm_dict)

    monkeypatch.setattr(cli, "_load_legacy_config", lambda: {})
    monkeypatch.setattr(cli, "_legacy_to_register_config_dict", lambda raw: sample_mailtm_dict)
    monkeypatch.setattr(cli.sys, "stdin", _TTY())
    monkeypatch.setattr(cli.sys, "stdout", _TTY())
    monkeypatch.setattr(cli, "_launch_tui", lambda config_dict: config)
    monkeypatch.setattr(cli, "run_batch", lambda built: launched.setdefault("config", built))

    result = cli.main([])

    assert result == 0
    assert launched["config"] == config
