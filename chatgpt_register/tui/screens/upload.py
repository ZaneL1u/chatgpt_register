"""上传目标步骤。"""

from __future__ import annotations

from urllib.parse import urlparse

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Input, Select, Static

from chatgpt_register.config.model import Sub2ApiConfig
from chatgpt_register.tui.screens.base import BaseWizardScreen
from chatgpt_register.upload.sub2api import fetch_sub2api_openai_groups

UPLOAD_HINTS = {
    "none": "不上传账号，仍会保留之前填写过的上传配置。",
    "cpa": "仅展示 CPA 字段；切换目标时，Sub2API 草稿不会丢失。",
    "sub2api": "仅展示 Sub2API 字段；建议先加载 openai 分组再继续。",
    "both": "同时配置 CPA 与 Sub2API，两组字段都会保留到最终配置中。",
}


class UploadScreen(BaseWizardScreen):
    STEP_TITLE = "步骤 3/4 · 上传目标"
    STEP_HINT = "选择上传方式，并完成对应服务的参数配置。"

    def compose_body(self) -> ComposeResult:
        target = self.wizard_state.upload["target"]
        yield Static("上传目标", classes="field-label")
        yield Select(
            [
                ("不上传", "none"),
                ("CPA", "cpa"),
                ("Sub2API", "sub2api"),
                ("CPA + Sub2API", "both"),
            ],
            value=target,
            allow_blank=False,
            id="upload-target",
        )
        yield Static(UPLOAD_HINTS[target], id="upload-hint", classes="step-hint")
        yield self._compose_cpa_section()
        yield self._compose_sub2api_section()
        self.call_after_refresh(self._refresh_sections)

    def _compose_cpa_section(self) -> Container:
        draft = self.wizard_state.upload["cpa"]
        return Container(
            self._field_block("CPA API URL", Input(value=draft["api_url"], id="cpa-api-url", placeholder="https://cpa.example.com/api")),
            self._sensitive_field_block("CPA API Token", "cpa-api-token", draft["api_token"]),
            id="cpa-section",
            classes="step-panel",
        )

    def _compose_sub2api_section(self) -> Container:
        draft = self.wizard_state.upload["sub2api"]
        return Container(
            self._field_block("Sub2API API Base", Input(value=draft["api_base"], id="sub2api-api-base", placeholder="https://sub2api.example.com")),
            self._sensitive_field_block("Sub2API Admin API Key", "sub2api-admin-api-key", draft["admin_api_key"]),
            self._sensitive_field_block("Sub2API Bearer Token", "sub2api-bearer-token", draft["bearer_token"]),
            self._field_block("账号并发", Input(value=draft["account_concurrency"], id="sub2api-account-concurrency", placeholder="1")),
            self._field_block("账号优先级", Input(value=draft["account_priority"], id="sub2api-account-priority", placeholder="1")),
            Horizontal(
                Button("加载 openai 分组", id="load-sub2api-groups", variant="primary"),
                Select(self._group_options(), id="sub2api-group-select", value=self._selected_group_value()),
                classes="field-block",
            ),
            Static("", id="sub2api-group-select-error", classes="field-error"),
            id="sub2api-section",
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

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "upload-target":
            self.wizard_state.upload["target"] = str(event.value)
            self.query_one("#upload-hint", Static).update(UPLOAD_HINTS[self.wizard_state.upload["target"]])
            self._refresh_sections()
            self.validate_current_step()
        elif event.select.id == "sub2api-group-select":
            value = "" if event.value == Select.BLANK else str(event.value)
            self.wizard_state.upload["sub2api"]["selected_group_id"] = value
            self.wizard_state.upload["sub2api"]["group_ids"] = [int(value)] if value else []
            self.validate_current_step()

    def on_input_changed(self, event: Input.Changed) -> None:
        field_id = event.input.id or ""
        if field_id.startswith("cpa-"):
            self.wizard_state.upload["cpa"][_upload_field_key(field_id)] = event.value
        elif field_id.startswith("sub2api-"):
            self.wizard_state.upload["sub2api"][_upload_field_key(field_id)] = event.value
        self.validate_current_step()

    def on_input_blurred(self, event: Input.Blurred) -> None:
        if event.input.id:
            self.validate_current_step()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("toggle-"):
            field_id = button_id.removeprefix("toggle-")
            target = self.query_one(f"#{field_id}", Input)
            target.password = not target.password
            event.button.label = "隐藏" if not target.password else "显示"
            return
        if button_id == "load-sub2api-groups":
            self._load_sub2api_groups()
            return
        super().on_button_pressed(event)

    def validate_current_step(self) -> list[str]:
        field_errors = validate_upload_values(self.wizard_state.upload)
        summary: list[str] = []
        for field_id in [
            "cpa-api-url",
            "cpa-api-token",
            "sub2api-api-base",
            "sub2api-admin-api-key",
            "sub2api-bearer-token",
            "sub2api-account-concurrency",
            "sub2api-account-priority",
            "sub2api-group-select",
        ]:
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
        self.go_to("summary")

    def _refresh_sections(self) -> None:
        target = self.wizard_state.upload["target"]
        cpa_section = self.query_one("#cpa-section", Container)
        sub2api_section = self.query_one("#sub2api-section", Container)
        cpa_section.styles.display = "block" if target in {"cpa", "both"} else "none"
        sub2api_section.styles.display = "block" if target in {"sub2api", "both"} else "none"

    def _group_options(self) -> list[tuple[str, str]]:
        options = [("请选择分组", Select.BLANK)]
        for group in self.wizard_state.upload["available_groups"]:
            options.append((f"{group['name']} (ID={group['id']})", str(group["id"])))
        return options

    def _selected_group_value(self) -> str:
        return self.wizard_state.upload["sub2api"].get("selected_group_id", "") or Select.BLANK

    def _load_sub2api_groups(self) -> None:
        field_errors = validate_upload_values(self.wizard_state.upload, require_group=False)
        blocking = [
            field_errors.get("sub2api-api-base"),
            field_errors.get("sub2api-admin-api-key"),
            field_errors.get("sub2api-bearer-token"),
        ]
        blocking = [item for item in blocking if item]
        if blocking:
            self.set_error_summary(blocking)
            return

        config = Sub2ApiConfig.model_validate(
            {
                "api_base": self.wizard_state.upload["sub2api"]["api_base"].strip(),
                "admin_api_key": self.wizard_state.upload["sub2api"]["admin_api_key"],
                "bearer_token": self.wizard_state.upload["sub2api"]["bearer_token"],
                "group_ids": [],
                "account_concurrency": 1,
                "account_priority": 1,
            }
        )
        try:
            groups = fetch_sub2api_openai_groups(config, proxy=self.wizard_state.registration["proxy"].strip())
        except Exception as exc:
            self.set_error_summary([f"加载 Sub2API 分组失败：{exc}"])
            return

        self.wizard_state.upload["available_groups"] = groups
        selected = self.wizard_state.upload["sub2api"].get("selected_group_id", "")
        if not selected and groups:
            selected = str(groups[0]["id"])
            self.wizard_state.upload["sub2api"]["selected_group_id"] = selected
            self.wizard_state.upload["sub2api"]["group_ids"] = [int(selected)]
        select = self.query_one("#sub2api-group-select", Select)
        select.set_options(self._group_options())
        select.value = selected or Select.BLANK
        self.validate_current_step()


def _upload_field_key(field_id: str) -> str:
    mapping = {
        "cpa-api-url": "api_url",
        "cpa-api-token": "api_token",
        "sub2api-api-base": "api_base",
        "sub2api-admin-api-key": "admin_api_key",
        "sub2api-bearer-token": "bearer_token",
        "sub2api-account-concurrency": "account_concurrency",
        "sub2api-account-priority": "account_priority",
    }
    return mapping[field_id]


def validate_upload_values(upload: dict, require_group: bool = True) -> dict[str, str]:
    field_errors: dict[str, str] = {}
    target = upload["target"]
    if target in {"cpa", "both"}:
        if not _is_valid_url(upload["cpa"]["api_url"]):
            field_errors["cpa-api-url"] = "请输入有效的 CPA API URL。"
        if not upload["cpa"]["api_token"].strip():
            field_errors["cpa-api-token"] = "请输入 CPA API Token。"
    if target in {"sub2api", "both"}:
        if not _is_valid_url(upload["sub2api"]["api_base"]):
            field_errors["sub2api-api-base"] = "请输入有效的 Sub2API API Base。"
        if not upload["sub2api"]["admin_api_key"].strip() and not upload["sub2api"]["bearer_token"].strip():
            field_errors["sub2api-admin-api-key"] = "请提供 Admin API Key 或 Bearer Token。"
            field_errors["sub2api-bearer-token"] = "请提供 Admin API Key 或 Bearer Token。"
        try:
            if int(upload["sub2api"]["account_concurrency"]) <= 0:
                raise ValueError
        except ValueError:
            field_errors["sub2api-account-concurrency"] = "账号并发必须是大于 0 的整数。"
        try:
            if int(upload["sub2api"]["account_priority"]) <= 0:
                raise ValueError
        except ValueError:
            field_errors["sub2api-account-priority"] = "账号优先级必须是大于 0 的整数。"
        if require_group and not upload["sub2api"].get("selected_group_id", "").strip():
            field_errors["sub2api-group-select"] = "请先加载并选择一个 Sub2API 分组。"
    return field_errors


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return bool(parsed.scheme and parsed.netloc)
