"""邮箱平台步骤。"""

from __future__ import annotations

from urllib.parse import urlparse

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, ContentSwitcher, Input, RadioButton, RadioSet, Static

from chatgpt_register.tui.screens.base import BaseWizardScreen

EMAIL_FIELDS = {
    "duckmail": {
        "duckmail-api-base": "api_base",
        "duckmail-bearer": "bearer",
    },
    "mailcow": {
        "mailcow-api-url": "api_url",
        "mailcow-api-key": "api_key",
        "mailcow-domain": "domain",
        "mailcow-imap-host": "imap_host",
        "mailcow-imap-port": "imap_port",
    },
    "mailtm": {
        "mailtm-api-base": "api_base",
    },
}

PROVIDER_HINTS = {
    "duckmail": "DuckMail 需要 Bearer Token；切换平台时，未显示字段会保留在内存中。",
    "mailcow": "Mailcow 需要 API 与 IMAP 信息；切换平台时，先前输入不会丢失。",
    "mailtm": "Mail.tm 仅需 API Base；后续若切换回来，会恢复之前填写的内容。",
}


class EmailScreen(BaseWizardScreen):
    STEP_TITLE = "步骤 1/4 · 邮箱平台"
    STEP_HINT = "先选择邮箱平台，再填写该平台专属配置。"

    def compose_body(self) -> ComposeResult:
        provider = self.wizard_state.email_provider
        yield Static("选择邮箱平台", classes="field-label")
        yield RadioSet(
            RadioButton("DuckMail", id="provider-duckmail", value=provider == "duckmail"),
            RadioButton("Mailcow", id="provider-mailcow", value=provider == "mailcow"),
            RadioButton("Mail.tm", id="provider-mailtm", value=provider == "mailtm"),
            id="email-provider",
        )
        yield Static(PROVIDER_HINTS[provider], id="provider-hint", classes="step-hint")
        with ContentSwitcher(initial=provider, id="provider-switcher"):
            yield self._compose_duckmail_panel()
            yield self._compose_mailcow_panel()
            yield self._compose_mailtm_panel()

    def _compose_duckmail_panel(self) -> Container:
        draft = self.wizard_state.draft_email["duckmail"]
        return Container(
            self._field_block("DuckMail API Base", Input(value=draft["api_base"], id="duckmail-api-base", placeholder="https://api.duckmail.sbs")),
            self._sensitive_field_block("DuckMail Bearer Token", "duckmail-bearer", draft["bearer"]),
            id="duckmail",
            classes="step-panel",
        )

    def _compose_mailcow_panel(self) -> Container:
        draft = self.wizard_state.draft_email["mailcow"]
        return Container(
            self._field_block("Mailcow API URL", Input(value=draft["api_url"], id="mailcow-api-url", placeholder="https://mail.example.com")),
            self._sensitive_field_block("Mailcow API Key", "mailcow-api-key", draft["api_key"]),
            self._field_block("Mailcow Domain", Input(value=draft["domain"], id="mailcow-domain", placeholder="example.com")),
            self._field_block("IMAP Host", Input(value=draft["imap_host"], id="mailcow-imap-host", placeholder="mail.example.com")),
            self._field_block("IMAP Port", Input(value=draft["imap_port"], id="mailcow-imap-port", placeholder="993")),
            id="mailcow",
            classes="step-panel",
        )

    def _compose_mailtm_panel(self) -> Container:
        draft = self.wizard_state.draft_email["mailtm"]
        return Container(
            self._field_block("Mail.tm API Base", Input(value=draft["api_base"], id="mailtm-api-base", placeholder="https://api.mail.tm")),
            id="mailtm",
            classes="step-panel",
        )

    def _field_block(self, label: str, widget: Input) -> Vertical:
        return Vertical(
            Static(label, classes="field-label"),
            widget,
            Static("", id=f"{widget.id}-error", classes="field-error"),
            classes="field-block",
        )

    def _sensitive_field_block(self, label: str, field_id: str, value: str) -> Vertical:
        return Vertical(
            Static(label, classes="field-label"),
            Horizontal(
                Input(value=value, id=field_id, password=True),
                Button("显示", id=f"toggle-{field_id}", classes="toggle-button"),
                classes="sensitive-row",
            ),
            Static("", id=f"{field_id}-error", classes="field-error"),
            classes="field-block",
        )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        provider = event.pressed.id.removeprefix("provider-")
        self.wizard_state.email_provider = provider
        self.query_one("#provider-switcher", ContentSwitcher).current = provider
        self.query_one("#provider-hint", Static).update(PROVIDER_HINTS[provider])
        self.set_error_summary([])

    def on_input_changed(self, event: Input.Changed) -> None:
        provider, field = self._field_to_state_key(event.input.id or "")
        if provider is None:
            return
        self.wizard_state.draft_email[provider][field] = event.value
        if provider == self.wizard_state.email_provider:
            self.validate_current_step()

    def on_input_blurred(self, event: Input.Blurred) -> None:
        provider, _ = self._field_to_state_key(event.input.id or "")
        if provider == self.wizard_state.email_provider:
            self.validate_current_step()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("toggle-"):
            field_id = button_id.removeprefix("toggle-")
            target = self.query_one(f"#{field_id}", Input)
            target.password = not target.password
            event.button.label = "隐藏" if not target.password else "显示"
            return
        super().on_button_pressed(event)

    def validate_current_step(self) -> list[str]:
        provider = self.wizard_state.email_provider
        values = self.wizard_state.draft_email[provider]
        field_errors = validate_email_values(provider, values)
        summary: list[str] = []

        for field_id in EMAIL_FIELDS[provider]:
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
        self.go_to("registration")

    def _field_to_state_key(self, field_id: str) -> tuple[str | None, str | None]:
        for provider, fields in EMAIL_FIELDS.items():
            if field_id in fields:
                return provider, fields[field_id]
        return None, None


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return bool(parsed.scheme and parsed.netloc)


def validate_email_values(provider: str, values: dict[str, str]) -> dict[str, str]:
    field_errors: dict[str, str] = {}

    if provider == "duckmail":
        if not _is_valid_url(values["api_base"]):
            field_errors["duckmail-api-base"] = "请输入有效的 DuckMail API 地址。"
        if not values["bearer"].strip():
            field_errors["duckmail-bearer"] = "请输入 DuckMail Bearer Token。"
    elif provider == "mailcow":
        if not _is_valid_url(values["api_url"]):
            field_errors["mailcow-api-url"] = "请输入有效的 Mailcow API URL。"
        for field_id, message in {
            "mailcow-api-key": "请输入 Mailcow API Key。",
            "mailcow-domain": "请输入 Mailcow 域名。",
            "mailcow-imap-host": "请输入 Mailcow IMAP Host。",
        }.items():
            state_key = EMAIL_FIELDS[provider][field_id]
            if not values[state_key].strip():
                field_errors[field_id] = message
        try:
            if int(values["imap_port"]) <= 0:
                raise ValueError
        except ValueError:
            field_errors["mailcow-imap-port"] = "IMAP Port 必须是大于 0 的整数。"
    elif provider == "mailtm":
        if not _is_valid_url(values["api_base"]):
            field_errors["mailtm-api-base"] = "请输入有效的 Mail.tm API 地址。"

    return field_errors
