"""保存 profile 的确认弹窗。"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from chatgpt_register.config.profile import InvalidProfileNameError, ProfileManager


class SaveProfileScreen(ModalScreen[str | None]):
    """要求用户提供 profile 名称，并显式确认覆盖。"""

    def __init__(
        self,
        *,
        profile_manager: ProfileManager,
        initial_name: str = "",
        source_profile_name: str | None = None,
    ) -> None:
        super().__init__()
        self.profile_manager = profile_manager
        self.initial_name = initial_name
        self.source_profile_name = source_profile_name
        self._awaiting_overwrite_confirmation = False

    def compose(self) -> ComposeResult:
        source_hint = f"当前派生自：{self.source_profile_name}" if self.source_profile_name else "当前为新建 profile。"
        yield Container(
            Static("保存 profile", classes="step-title"),
            Static("请输入 profile 名称；只有这里确认后才会写入 TOML 文件。"),
            Static(source_hint, classes="step-hint"),
            Static("", id="save-profile-error", classes="error-summary"),
            Static("Profile 名称", classes="field-label"),
            Input(value=self.initial_name, id="save-profile-name", placeholder="例如 prod-duckmail"),
            Horizontal(
                Button("取消", id="cancel-save-profile"),
                Button("保存 profile", id="confirm-save-profile", variant="primary"),
                classes="wizard-actions",
            ),
            id="modal-body",
        )

    def on_mount(self) -> None:
        self.set_focus(self.query_one("#save-profile-name", Input))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "save-profile-name":
            return
        self._awaiting_overwrite_confirmation = False
        self.query_one("#confirm-save-profile", Button).label = "保存 profile"
        self.query_one("#save-profile-error", Static).update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "cancel-save-profile":
            self.dismiss(None)
            return
        if button_id != "confirm-save-profile":
            return

        profile_name = self.query_one("#save-profile-name", Input).value.strip()
        error_summary = self.query_one("#save-profile-error", Static)
        try:
            exists = self.profile_manager.exists(profile_name)
        except InvalidProfileNameError as exc:
            error_summary.update(str(exc))
            return

        if exists and not self._awaiting_overwrite_confirmation:
            self._awaiting_overwrite_confirmation = True
            event.button.label = "确认覆盖保存"
            error_summary.update(f"Profile `{profile_name}` 已存在；再次确认将覆盖原文件。")
            return

        self.dismiss(profile_name)
