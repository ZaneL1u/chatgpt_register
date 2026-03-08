"""ProfileManager — TOML profile 持久化管理器。

将 RegisterConfig 实例保存为人类可读的 TOML 文件，
并可从 TOML 文件还原为 RegisterConfig 实例。
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import tomli_w
from pydantic import ValidationError

from chatgpt_register.config.model import (
    RegisterConfig,
    format_validation_errors,
)

_DEFAULT_BASE = Path.home() / ".chatgpt-register" / "profiles"

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_MAX_NAME_LENGTH = 64


class ProfileError(Exception):
    """Profile 仓储层基类异常。"""


class InvalidProfileNameError(ValueError, ProfileError):
    """Profile 名称不合法。"""


class ProfileNotFoundError(FileNotFoundError, ProfileError):
    """Profile 文件不存在。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = path.stem
        super().__init__(f"Profile 不存在: {self.name}")


class ProfileDecodeError(ProfileError):
    """Profile TOML 内容损坏或不可解析。"""

    def __init__(self, path: Path, error: tomllib.TOMLDecodeError) -> None:
        self.path = path
        self.name = path.stem
        self.__cause__ = error
        message = f"Profile 文件已损坏，TOML 解析失败: {self.name} ({path})"
        super().__init__(message)


class ProfileValidationError(ProfileError):
    """Profile 结构不合法，无法转成 RegisterConfig。"""

    def __init__(self, path: Path, error: ValidationError) -> None:
        self.path = path
        self.name = path.stem
        self.details = format_validation_errors(error)
        self.__cause__ = error
        super().__init__(
            f"Profile 配置不合法，请检查必填项与字段格式: {self.name}\n{self.details}"
        )


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    """供 CLI/TUI 直接展示的 profile 摘要。"""

    name: str
    path: Path
    email_provider: str
    upload_targets: tuple[str, ...]
    total_accounts: int
    workers: int
    updated_at: datetime


def _validate_name(name: str) -> None:
    """校验 profile 名称，非法名称抛出 InvalidProfileNameError。"""
    if not name:
        raise InvalidProfileNameError("Profile 名称不能为空")
    if len(name) > _MAX_NAME_LENGTH:
        raise InvalidProfileNameError(
            f"Profile 名称不能超过 {_MAX_NAME_LENGTH} 个字符，当前: {len(name)}"
        )
    if "/" in name or "\\" in name:
        raise InvalidProfileNameError(f"Profile 名称不能包含路径分隔符: {name!r}")
    if not _NAME_PATTERN.match(name):
        raise InvalidProfileNameError(
            "Profile 名称只允许小写字母、数字、下划线和连字符，"
            f"且必须以字母或数字开头: {name!r}"
        )


class ProfileManager:
    """TOML profile 持久化管理器。

    支持保存、加载、列举、删除 RegisterConfig profile 文件。
    存储路径可通过构造参数指定。
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or _DEFAULT_BASE).expanduser().resolve()

    def _profile_path(self, name: str) -> Path:
        _validate_name(name)
        return self.base_dir / f"{name}.toml"

    def _read_profile_data(self, path: Path) -> dict:
        try:
            with open(path, "rb") as file_obj:
                return tomllib.load(file_obj)
        except tomllib.TOMLDecodeError as error:
            raise ProfileDecodeError(path, error) from error

    def _load_from_path(self, path: Path) -> RegisterConfig:
        data = self._read_profile_data(path)
        try:
            return RegisterConfig.model_validate(data)
        except ValidationError as error:
            raise ProfileValidationError(path, error) from error

    def _build_summary(self, path: Path, config: RegisterConfig) -> ProfileSummary:
        return ProfileSummary(
            name=path.stem,
            path=path,
            email_provider=config.email.provider,
            upload_targets=tuple(config.upload.targets),
            total_accounts=config.registration.total_accounts,
            workers=config.registration.workers,
            updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
        )

    def save(self, name: str, config: RegisterConfig) -> Path:
        """保存配置为 TOML profile 文件。"""
        path = self._profile_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump(mode="json", exclude_none=True)
        with open(path, "wb") as file_obj:
            tomli_w.dump(data, file_obj)
        return path

    def load(self, name: str) -> RegisterConfig:
        """从 TOML profile 文件加载配置。"""
        path = self._profile_path(name)
        if not path.exists():
            raise ProfileNotFoundError(path)
        return self._load_from_path(path)

    def list_profiles(self) -> list[str]:
        """列举所有已保存的 profile 名称（排序）。"""
        if not self.base_dir.exists():
            return []
        return sorted(path.stem for path in self.base_dir.glob("*.toml"))

    def list_profile_summaries(self) -> list[ProfileSummary]:
        """列举所有 profile 摘要，供上层 UI 直接展示。"""
        if not self.base_dir.exists():
            return []

        summaries: list[ProfileSummary] = []
        for path in sorted(self.base_dir.glob("*.toml"), key=lambda item: item.stem):
            config = self._load_from_path(path)
            summaries.append(self._build_summary(path, config))
        return summaries

    def exists(self, name: str) -> bool:
        """检查 profile 是否存在。"""
        return self._profile_path(name).exists()

    def delete(self, name: str) -> None:
        """删除 profile，不存在时不报错。"""
        path = self._profile_path(name)
        if path.exists():
            path.unlink()


__all__ = [
    "InvalidProfileNameError",
    "ProfileDecodeError",
    "ProfileError",
    "ProfileManager",
    "ProfileNotFoundError",
    "ProfileSummary",
    "ProfileValidationError",
]
