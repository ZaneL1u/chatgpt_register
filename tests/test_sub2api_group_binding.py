from __future__ import annotations

import builtins
from copy import deepcopy

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.upload.sub2api import (
    prepare_sub2api_group_binding,
    validate_sub2api_group_binding,
)


def _sub2api_config(payload: dict):
    config = RegisterConfig.model_validate(payload)
    assert config.upload.sub2api is not None
    return config.upload.sub2api


def test_prepare_sub2api_group_binding_accepts_complete_profile(
    monkeypatch,
    sample_mailtm_dict: dict,
) -> None:
    seen_imports: list[str] = []
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "questionary":
            raise AssertionError("运行阶段不应导入 questionary")
        seen_imports.append(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    ok, group_ids = prepare_sub2api_group_binding(_sub2api_config(sample_mailtm_dict))

    assert ok is True
    assert group_ids == [1, 2, 3]
    assert "questionary" not in seen_imports


def test_validate_sub2api_group_binding_fails_without_group_ids(
    sample_mailtm_dict: dict,
) -> None:
    payload = deepcopy(sample_mailtm_dict)
    payload["upload"]["sub2api"]["group_ids"] = []

    ok, group_ids, error = validate_sub2api_group_binding(_sub2api_config(payload))

    assert ok is False
    assert group_ids == []
    assert error is not None
    assert "group_ids" in error
