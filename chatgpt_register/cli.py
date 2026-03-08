"""Profile-only CLI 入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.config.profile import ProfileManager
from chatgpt_register.core.batch import run_batch

_LEGACY_CONFIG_PATH = Path("config.json")


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chatgpt-register",
        description="ChatGPT 批量自动注册工具（TUI + TOML Profile）",
    )
    parser.add_argument("--profile", help="直接加载已保存的 profile 并执行。")
    parser.add_argument("--profiles-dir", type=Path, help="自定义 TOML profile 存储目录。")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="非交互模式；未提供 --profile 时直接失败。",
    )
    return parser


def _build_profile_manager(profiles_dir: Path | None) -> ProfileManager:
    return ProfileManager(base_dir=profiles_dir)


def _warn_legacy_config_if_present() -> None:
    legacy_path = Path.cwd() / _LEGACY_CONFIG_PATH
    if not legacy_path.exists():
        return
    print(
        "[迁移提示] 检测到当前目录存在 `config.json`；CLI 已不再加载 JSON 配置。"
        "请运行交互式 TUI 创建/修复 TOML profile，或使用 `--profile <name>`。"
    )


def _should_launch_tui(args: argparse.Namespace) -> bool:
    return (
        not args.non_interactive
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    )


def _launch_tui(profile_manager: ProfileManager) -> RegisterConfig | None:
    from chatgpt_register.tui import WizardApp

    app = WizardApp(profile_manager=profile_manager)
    return app.run()


def _load_profile(profile_manager: ProfileManager, profile_name: str) -> RegisterConfig:
    return profile_manager.load(profile_name)


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _build_cli_parser()
        args = parser.parse_args(argv)
        profile_manager = _build_profile_manager(args.profiles_dir)

        _warn_legacy_config_if_present()

        if args.profile:
            config = _load_profile(profile_manager, args.profile)
            run_batch(config)
            return 0

        if _should_launch_tui(args):
            config = _launch_tui(profile_manager)
            if config is None:
                print("[Info] 已取消 TUI 配置，未执行注册。")
                return 0
            run_batch(config)
            return 0

        print(
            "非交互模式必须提供 `--profile <name>`。"
            "请先运行 `uv run chatgpt-register` 创建 profile，或在命令中传入 `--profile`。"
        )
        return 2
    except KeyboardInterrupt:
        print("\n[Info] 用户中断，已退出。")
        return 130
    except Exception as error:
        print(f"配置或执行失败: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
