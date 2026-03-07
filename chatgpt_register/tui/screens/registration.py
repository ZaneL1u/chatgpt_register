"""注册参数步骤。"""

from __future__ import annotations

from urllib.parse import urlparse

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Static

from chatgpt_register.tui.screens.base import BaseWizardScreen

REGISTRATION_FIELDS = {
    "registration-total-accounts": "total_accounts",
    "registration-workers": "workers",
    "registration-proxy": "proxy",
    "registration-output-file": "output_file",
    "registration-ak-file": "ak_file",
    "registration-rk-file": "rk_file",
    "registration-token-json-dir": "token_json_dir",
}


class RegistrationScreen(BaseWizardScreen):
    STEP_TITLE = "步骤 2/4 · 注册参数"
    STEP_HINT = "设置注册规模、代理和输出路径；本阶段不提供返回上一步。"

    def compose_body(self) -> ComposeResult:
        state = self.wizard_state.registration
        yield self._field_block("注册账号数量", Input(value=state["total_accounts"], id="registration-total-accounts", placeholder="3"))
        yield self._field_block("并发数", Input(value=state["workers"], id="registration-workers", placeholder="3"))
        yield self._field_block("代理地址（可空）", Input(value=state["proxy"], id="registration-proxy", placeholder="http://127.0.0.1:7890"))
        yield self._field_block("输出文件", Input(value=state["output_file"], id="registration-output-file"))
        yield self._field_block("AK 文件", Input(value=state["ak_file"], id="registration-ak-file"))
        yield self._field_block("RK 文件", Input(value=state["rk_file"], id="registration-rk-file"))
        yield self._field_block("Token 目录", Input(value=state["token_json_dir"], id="registration-token-json-dir"))

    def _field_block(self, label: str, widget: Input) -> Vertical:
        return Vertical(
            Static(label, classes="field-label"),
            widget,
            Static("", id=f"{widget.id}-error", classes="field-error"),
            classes="field-block",
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        key = REGISTRATION_FIELDS.get(event.input.id or "")
        if key is None:
            return
        self.wizard_state.registration[key] = event.value
        self.validate_current_step()

    def on_input_blurred(self, event: Input.Blurred) -> None:
        if (event.input.id or "") in REGISTRATION_FIELDS:
            self.validate_current_step()

    def validate_current_step(self) -> list[str]:
        state = self.wizard_state.registration
        field_errors: dict[str, str] = {}
        summary: list[str] = []

        total_accounts = _positive_int(state["total_accounts"])
        workers = _positive_int(state["workers"])

        if total_accounts is None:
            field_errors["registration-total-accounts"] = "注册账号数量必须是大于 0 的整数。"
        if workers is None:
            field_errors["registration-workers"] = "并发数必须是大于 0 的整数。"
        if total_accounts is not None and workers is not None and workers > total_accounts:
            field_errors["registration-workers"] = "并发数不能大于注册账号数量。"

        proxy = state["proxy"].strip()
        if proxy and not _is_valid_proxy(proxy):
            field_errors["registration-proxy"] = "代理地址必须包含协议和主机，例如 http://127.0.0.1:7890。"

        for field_id, key in REGISTRATION_FIELDS.items():
            if key in {"proxy", "total_accounts", "workers"}:
                continue
            if not state[key].strip():
                field_errors[field_id] = "该字段不能为空。"

        for field_id in REGISTRATION_FIELDS:
            self.set_field_error(field_id, field_errors.get(field_id, ""))
        for message in field_errors.values():
            if message not in summary:
                summary.append(message)
        self.set_error_summary(summary)
        return summary

    def handle_next(self) -> None:
        errors = self.validate_current_step()
        if errors:
            return
        self.go_to("upload")


def _positive_int(value: str) -> int | None:
    try:
        result = int(value)
    except ValueError:
        return None
    return result if result > 0 else None


def _is_valid_proxy(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)
