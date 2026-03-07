"""ProfileManager — TOML profile 持久化管理器。

将 RegisterConfig 实例保存为人类可读的 TOML 文件，
并可从 TOML 文件还原为 RegisterConfig 实例。
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import tomli_w

from config_model import RegisterConfig

_DEFAULT_BASE = Path.home() / ".chatgpt-register" / "profiles"

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_MAX_NAME_LENGTH = 64


def _validate_name(name: str) -> None:
    """校验 profile 名称，非法名称抛出 ValueError。"""
    if not name:
        raise ValueError("Profile 名称不能为空")
    if len(name) > _MAX_NAME_LENGTH:
        raise ValueError(
            f"Profile 名称不能超过 {_MAX_NAME_LENGTH} 个字符，当前: {len(name)}"
        )
    if "/" in name or "\\" in name:
        raise ValueError(f"Profile 名称不能包含路径分隔符: {name!r}")
    if not _NAME_PATTERN.match(name):
        raise ValueError(
            f"Profile 名称只允许小写字母、数字、下划线和连字符，"
            f"且必须以字母或数字开头: {name!r}"
        )


class ProfileManager:
    """TOML profile 持久化管理器。

    支持保存、加载、列举、删除 RegisterConfig profile 文件。
    存储路径可通过构造参数指定。
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or _DEFAULT_BASE).expanduser().resolve()

    def save(self, name: str, config: RegisterConfig) -> Path:
        """保存配置为 TOML profile 文件。

        Args:
            name: Profile 名称（仅允许 [a-z0-9][a-z0-9_-]*，最长 64 字符）
            config: 要保存的配置实例

        Returns:
            保存的文件路径

        Raises:
            ValueError: 名称不合法
        """
        _validate_name(name)
        path = self.base_dir / f"{name}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump(mode="json", exclude_none=True)
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
        return path

    def load(self, name: str) -> RegisterConfig:
        """从 TOML profile 文件加载配置。

        Args:
            name: Profile 名称

        Returns:
            还原的 RegisterConfig 实例

        Raises:
            FileNotFoundError: Profile 文件不存在
        """
        path = self.base_dir / f"{name}.toml"
        if not path.exists():
            raise FileNotFoundError(f"Profile 不存在: {path}")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return RegisterConfig.model_validate(data)

    def list_profiles(self) -> list[str]:
        """列举所有已保存的 profile 名称（排序）。"""
        if not self.base_dir.exists():
            return []
        return sorted(p.stem for p in self.base_dir.glob("*.toml"))

    def exists(self, name: str) -> bool:
        """检查 profile 是否存在。"""
        return (self.base_dir / f"{name}.toml").exists()

    def delete(self, name: str) -> None:
        """删除 profile，不存在时不报错。"""
        path = self.base_dir / f"{name}.toml"
        if path.exists():
            path.unlink()
