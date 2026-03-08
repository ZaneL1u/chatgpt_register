"""确认摘要步骤。"""

from __future__ import annotations

import json

from pydantic import ValidationError
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Select, Static

from chatgpt_register.config.model import format_validation_errors
from chatgpt_register.tui.screens.base import BaseWizardScreen
from chatgpt_register.tui.screens.email import validate_email_values
from chatgpt_register.tui.screens.registration import validate_registration_values
from chatgpt_register.tui.screens.upload import validate_upload_values

SENSITIVE_INPUT_IDS = {
    "summary-duckmail-bearer",
    "summary-mailcow-api-key",
    "summary-cpa-api-token",
    "summary-sub2api-admin-api-key",
    "summary-sub2api-bearer-token",
}


class SummaryScreen(BaseWizardScreen):
    STEP_TITLE = "步骤 4/4 · 确认摘要"
    STEP_HINT = "这里是唯一允许回改配置的页面；确认无误后将进入最终确认。"
    NEXT_LABEL = "我已确认，立即执行"

    def __init__(self) -> None:
        super().__init__()
        self.show_sensitive = False

    def compose_body(self) -> ComposeResult:
        yield Horizontal(
            Button("显示敏感字段", id="toggle-summary-sensitive"),
            classes="wizard-actions",
        )
        yield Static("", id="summary-preview", classes="placeholder")

        for widget in self._compose_selected_email_fields():
            yield widget
        for widget in self._compose_registration_fields():
            yield widget
        for widget in self._compose_upload_fields():
            yield widget
        for widget in self._compose_oauth_fields():
            yield widget
        self.call_after_refresh(self.refresh_from_state)

    def _compose_selected_email_fields(self):
        provider = self.wizard_state.email_provider
        yield Static(f"邮箱平台：{provider}", classes="field-label")
        if provider == "duckmail":
            yield self._field_block("DuckMail API Base", Input(id="summary-duckmail-api-base"))
            yield self._sensitive_field_block("DuckMail Bearer Token", "summary-duckmail-bearer")
        elif provider == "mailcow":
            yield self._field_block("Mailcow API URL", Input(id="summary-mailcow-api-url"))
            yield self._sensitive_field_block("Mailcow API Key", "summary-mailcow-api-key")
            yield self._field_block("Mailcow Domain", Input(id="summary-mailcow-domain"))
            yield self._field_block("IMAP Host", Input(id="summary-mailcow-imap-host"))
            yield self._field_block("IMAP Port", Input(id="summary-mailcow-imap-port"))
        else:
            yield self._field_block("Mail.tm API Base", Input(id="summary-mailtm-api-base"))

    def _compose_registration_fields(self):
        return [
            Static("注册参数", classes="field-label"),
            self._field_block("注册账号数量", Input(id="summary-total-accounts")),
            self._field_block("并发数", Input(id="summary-workers")),
            self._field_block("代理地址", Input(id="summary-proxy")),
            self._field_block("输出文件", Input(id="summary-output-file")),
            self._field_block("AK 文件", Input(id="summary-ak-file")),
            self._field_block("RK 文件", Input(id="summary-rk-file")),
            self._field_block("Token 目录", Input(id="summary-token-json-dir")),
        ]

    def _compose_upload_fields(self):
        widgets = [
            Static("上传配置", classes="field-label"),
            Select(
                [("不上传", "none"), ("CPA", "cpa"), ("Sub2API", "sub2api"), ("CPA + Sub2API", "both")],
                allow_blank=False,
                id="summary-upload-target",
            ),
        ]
        widgets.extend(
            [
                self._field_block("CPA API URL", Input(id="summary-cpa-api-url")),
                self._sensitive_field_block("CPA API Token", "summary-cpa-api-token"),
                self._field_block("Sub2API API Base", Input(id="summary-sub2api-api-base")),
                self._sensitive_field_block("Sub2API Admin API Key", "summary-sub2api-admin-api-key"),
                self._sensitive_field_block("Sub2API Bearer Token", "summary-sub2api-bearer-token"),
                self._field_block("Sub2API 账号并发", Input(id="summary-sub2api-account-concurrency")),
                self._field_block("Sub2API 账号优先级", Input(id="summary-sub2api-account-priority")),
                self._field_block("Sub2API 分组 ID", Input(id="summary-sub2api-group-id")),
            ]
        )
        return widgets

    def _compose_oauth_fields(self):
        return [
            Static("OAuth", classes="field-label"),
            Select([("开启", "true"), ("关闭", "false")], allow_blank=False, id="summary-oauth-enabled"),
            Select([("必须成功", "true"), ("允许失败继续", "false")], allow_blank=False, id="summary-oauth-required"),
            self._field_block("OAuth Issuer", Input(id="summary-oauth-issuer")),
            self._field_block("OAuth Client ID", Input(id="summary-oauth-client-id")),
            self._field_block("OAuth Redirect URI", Input(id="summary-oauth-redirect-uri")),
        ]

    def _field_block(self, label: str, widget: Input) -> Vertical:
        return Vertical(
            Static(label, classes="field-label"),
            widget,
            Static("", id=f"{widget.id}-error", classes="field-error"),
            classes="field-block",
        )

    def _sensitive_field_block(self, label: str, field_id: str) -> Vertical:
        return Vertical(
            Static(label, classes="field-label"),
            Horizontal(
                Input(id=field_id, password=True),
                Button("显示", id=f"toggle-{field_id}", classes="toggle-button"),
                classes="sensitive-row",
            ),
            Static("", id=f"{field_id}-error", classes="field-error"),
            classes="field-block",
        )

    def on_screen_resume(self) -> None:
        self.refresh_from_state()

    def refresh_from_state(self) -> None:
        state = self.wizard_state
        provider = state.email_provider
        email = state.draft_email[provider]
        if provider == "duckmail":
            self.query_one("#summary-duckmail-api-base", Input).value = email["api_base"]
            self.query_one("#summary-duckmail-bearer", Input).value = email["bearer"]
        elif provider == "mailcow":
            self.query_one("#summary-mailcow-api-url", Input).value = email["api_url"]
            self.query_one("#summary-mailcow-api-key", Input).value = email["api_key"]
            self.query_one("#summary-mailcow-domain", Input).value = email["domain"]
            self.query_one("#summary-mailcow-imap-host", Input).value = email["imap_host"]
            self.query_one("#summary-mailcow-imap-port", Input).value = email["imap_port"]
        else:
            self.query_one("#summary-mailtm-api-base", Input).value = email["api_base"]

        self.query_one("#summary-total-accounts", Input).value = state.registration["total_accounts"]
        self.query_one("#summary-workers", Input).value = state.registration["workers"]
        self.query_one("#summary-proxy", Input).value = state.registration["proxy"]
        self.query_one("#summary-output-file", Input).value = state.registration["output_file"]
        self.query_one("#summary-ak-file", Input).value = state.registration["ak_file"]
        self.query_one("#summary-rk-file", Input).value = state.registration["rk_file"]
        self.query_one("#summary-token-json-dir", Input).value = state.registration["token_json_dir"]

        self.query_one("#summary-upload-target", Select).value = state.upload["target"]
        self.query_one("#summary-cpa-api-url", Input).value = state.upload["cpa"]["api_url"]
        self.query_one("#summary-cpa-api-token", Input).value = state.upload["cpa"]["api_token"]
        self.query_one("#summary-sub2api-api-base", Input).value = state.upload["sub2api"]["api_base"]
        self.query_one("#summary-sub2api-admin-api-key", Input).value = state.upload["sub2api"]["admin_api_key"]
        self.query_one("#summary-sub2api-bearer-token", Input).value = state.upload["sub2api"]["bearer_token"]
        self.query_one("#summary-sub2api-account-concurrency", Input).value = state.upload["sub2api"]["account_concurrency"]
        self.query_one("#summary-sub2api-account-priority", Input).value = state.upload["sub2api"]["account_priority"]
        self.query_one("#summary-sub2api-group-id", Input).value = state.upload["sub2api"].get("selected_group_id", "")

        self.query_one("#summary-oauth-enabled", Select).value = "true" if state.oauth["enabled"] else "false"
        self.query_one("#summary-oauth-required", Select).value = "true" if state.oauth["required"] else "false"
        self.query_one("#summary-oauth-issuer", Input).value = str(state.oauth["issuer"])
        self.query_one("#summary-oauth-client-id", Input).value = str(state.oauth["client_id"])
        self.query_one("#summary-oauth-redirect-uri", Input).value = str(state.oauth["redirect_uri"])
        self._set_sensitive_visibility()
        self._update_next_button_label()
        self.refresh_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._sync_input(event.input.id or "", event.value)
        self.validate_current_step()
        self.refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        select_id = event.select.id or ""
        if select_id == "summary-upload-target":
            self.wizard_state.upload["target"] = str(event.value)
        elif select_id == "summary-oauth-enabled":
            self.wizard_state.oauth["enabled"] = str(event.value) == "true"
        elif select_id == "summary-oauth-required":
            self.wizard_state.oauth["required"] = str(event.value) == "true"
        self.validate_current_step()
        self.refresh_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "toggle-summary-sensitive":
            self.show_sensitive = not self.show_sensitive
            event.button.label = "隐藏敏感字段" if self.show_sensitive else "显示敏感字段"
            self._set_sensitive_visibility()
            self.refresh_preview()
            return
        if button_id.startswith("toggle-summary-"):
            field_id = button_id.removeprefix("toggle-")
            target = self.query_one(f"#{field_id}", Input)
            target.password = not target.password
            event.button.label = "隐藏" if not target.password else "显示"
            return
        super().on_button_pressed(event)

    def validate_current_step(self) -> list[str]:
        summary: list[str] = []
        email_errors = validate_email_values(
            self.wizard_state.email_provider,
            self.wizard_state.draft_email[self.wizard_state.email_provider],
        )
        registration_errors = validate_registration_values(self.wizard_state.registration)
        upload_errors = validate_upload_values(self.wizard_state.upload)
        mapped: dict[str, str] = {}
        mapped.update(_map_email_errors(self.wizard_state.email_provider, email_errors))
        mapped.update(_map_registration_errors(registration_errors))
        mapped.update(_map_upload_errors(upload_errors))

        for field_id in [
            "summary-duckmail-api-base",
            "summary-duckmail-bearer",
            "summary-mailcow-api-url",
            "summary-mailcow-api-key",
            "summary-mailcow-domain",
            "summary-mailcow-imap-host",
            "summary-mailcow-imap-port",
            "summary-mailtm-api-base",
            "summary-total-accounts",
            "summary-workers",
            "summary-proxy",
            "summary-output-file",
            "summary-ak-file",
            "summary-rk-file",
            "summary-token-json-dir",
            "summary-cpa-api-url",
            "summary-cpa-api-token",
            "summary-sub2api-api-base",
            "summary-sub2api-admin-api-key",
            "summary-sub2api-bearer-token",
            "summary-sub2api-account-concurrency",
            "summary-sub2api-account-priority",
            "summary-sub2api-group-id",
        ]:
            try:
                self.set_field_error(field_id, mapped.get(field_id, ""))
            except Exception:
                continue

        try:
            self.wizard_state.build_config()
        except ValidationError as exc:
            summary.append(format_validation_errors(exc))
        for message in mapped.values():
            if message and message not in summary:
                summary.append(message)
        self.set_error_summary(summary)
        return summary

    def handle_next(self) -> None:
        errors = self.validate_current_step()
        if errors:
            return
        config = self.wizard_state.build_config()
        if self.app.should_prompt_profile_save():
            self.app.request_profile_save(config)
            return
        self.app.exit(config)

    def refresh_preview(self) -> None:
        preview = self.wizard_state.export_config_dict()
        if not self.show_sensitive:
            _mask_sensitive(preview)
        self.query_one("#summary-preview", Static).update(json.dumps(preview, ensure_ascii=False, indent=2))

    def _sync_input(self, field_id: str, value: str) -> None:
        provider = self.wizard_state.email_provider
        if field_id == "summary-total-accounts":
            self.wizard_state.registration["total_accounts"] = value
        elif field_id == "summary-workers":
            self.wizard_state.registration["workers"] = value
        elif field_id == "summary-proxy":
            self.wizard_state.registration["proxy"] = value
        elif field_id == "summary-output-file":
            self.wizard_state.registration["output_file"] = value
        elif field_id == "summary-ak-file":
            self.wizard_state.registration["ak_file"] = value
        elif field_id == "summary-rk-file":
            self.wizard_state.registration["rk_file"] = value
        elif field_id == "summary-token-json-dir":
            self.wizard_state.registration["token_json_dir"] = value
        elif field_id == "summary-cpa-api-url":
            self.wizard_state.upload["cpa"]["api_url"] = value
        elif field_id == "summary-cpa-api-token":
            self.wizard_state.upload["cpa"]["api_token"] = value
        elif field_id == "summary-sub2api-api-base":
            self.wizard_state.upload["sub2api"]["api_base"] = value
        elif field_id == "summary-sub2api-admin-api-key":
            self.wizard_state.upload["sub2api"]["admin_api_key"] = value
        elif field_id == "summary-sub2api-bearer-token":
            self.wizard_state.upload["sub2api"]["bearer_token"] = value
        elif field_id == "summary-sub2api-account-concurrency":
            self.wizard_state.upload["sub2api"]["account_concurrency"] = value
        elif field_id == "summary-sub2api-account-priority":
            self.wizard_state.upload["sub2api"]["account_priority"] = value
        elif field_id == "summary-sub2api-group-id":
            self.wizard_state.upload["sub2api"]["selected_group_id"] = value
            self.wizard_state.upload["sub2api"]["group_ids"] = [int(value)] if value.isdigit() else []
        elif field_id == "summary-oauth-issuer":
            self.wizard_state.oauth["issuer"] = value
        elif field_id == "summary-oauth-client-id":
            self.wizard_state.oauth["client_id"] = value
        elif field_id == "summary-oauth-redirect-uri":
            self.wizard_state.oauth["redirect_uri"] = value
        elif provider == "duckmail":
            mapping = {
                "summary-duckmail-api-base": "api_base",
                "summary-duckmail-bearer": "bearer",
            }
            if field_id in mapping:
                self.wizard_state.draft_email[provider][mapping[field_id]] = value
        elif provider == "mailcow":
            mapping = {
                "summary-mailcow-api-url": "api_url",
                "summary-mailcow-api-key": "api_key",
                "summary-mailcow-domain": "domain",
                "summary-mailcow-imap-host": "imap_host",
                "summary-mailcow-imap-port": "imap_port",
            }
            if field_id in mapping:
                self.wizard_state.draft_email[provider][mapping[field_id]] = value
        elif provider == "mailtm" and field_id == "summary-mailtm-api-base":
            self.wizard_state.draft_email[provider]["api_base"] = value

    def _set_sensitive_visibility(self) -> None:
        for field_id in SENSITIVE_INPUT_IDS:
            try:
                self.query_one(f"#{field_id}", Input).password = not self.show_sensitive
            except Exception:
                continue

    def _update_next_button_label(self) -> None:
        label = "保存 profile 并执行" if self.app.should_prompt_profile_save() else self.NEXT_LABEL
        self.query_one("#next-button", Button).label = label



def _mask_sensitive(payload: dict) -> None:
    for path in [
        ("email", "duckmail", "bearer"),
        ("email", "mailcow", "api_key"),
        ("upload", "cpa", "api_token"),
        ("upload", "sub2api", "admin_api_key"),
        ("upload", "sub2api", "bearer_token"),
    ]:
        node = payload
        for key in path[:-1]:
            node = node.get(key, {})
        value = str(node.get(path[-1], ""))
        if value:
            node[path[-1]] = _mask(value)



def _mask(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"



def _map_email_errors(provider: str, errors: dict[str, str]) -> dict[str, str]:
    mapping = {
        "duckmail": {
            "duckmail-api-base": "summary-duckmail-api-base",
            "duckmail-bearer": "summary-duckmail-bearer",
        },
        "mailcow": {
            "mailcow-api-url": "summary-mailcow-api-url",
            "mailcow-api-key": "summary-mailcow-api-key",
            "mailcow-domain": "summary-mailcow-domain",
            "mailcow-imap-host": "summary-mailcow-imap-host",
            "mailcow-imap-port": "summary-mailcow-imap-port",
        },
        "mailtm": {
            "mailtm-api-base": "summary-mailtm-api-base",
        },
    }
    return {mapping[provider][key]: value for key, value in errors.items() if key in mapping[provider]}



def _map_registration_errors(errors: dict[str, str]) -> dict[str, str]:
    mapping = {
        "registration-total-accounts": "summary-total-accounts",
        "registration-workers": "summary-workers",
        "registration-proxy": "summary-proxy",
        "registration-output-file": "summary-output-file",
        "registration-ak-file": "summary-ak-file",
        "registration-rk-file": "summary-rk-file",
        "registration-token-json-dir": "summary-token-json-dir",
    }
    return {mapping[key]: value for key, value in errors.items() if key in mapping}



def _map_upload_errors(errors: dict[str, str]) -> dict[str, str]:
    mapping = {
        "cpa-api-url": "summary-cpa-api-url",
        "cpa-api-token": "summary-cpa-api-token",
        "sub2api-api-base": "summary-sub2api-api-base",
        "sub2api-admin-api-key": "summary-sub2api-admin-api-key",
        "sub2api-bearer-token": "summary-sub2api-bearer-token",
        "sub2api-account-concurrency": "summary-sub2api-account-concurrency",
        "sub2api-account-priority": "summary-sub2api-account-priority",
        "sub2api-group-select": "summary-sub2api-group-id",
    }
    return {mapping[key]: value for key, value in errors.items() if key in mapping}
