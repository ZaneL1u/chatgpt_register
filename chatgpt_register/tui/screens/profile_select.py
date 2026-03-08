"""Profile 选择启动页。"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, ListItem, ListView, Static

from chatgpt_register.config.profile import ProfileError, ProfileSummary


class ProfileSelectScreen(Screen[None]):
    """在进入向导前选择已有 profile、新建或派生。"""

    def __init__(self) -> None:
        super().__init__()
        self._summaries: list[ProfileSummary] = []

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="wizard-scroll"):
            yield Static("选择已保存的 Profile", classes="step-title")
            yield Static("可直接运行现有配置，也可以新建或基于已有配置派生。", classes="step-hint")
            yield Static("", id="error-summary", classes="error-summary")
            yield ListView(id="profile-list")
            with Horizontal(classes="wizard-actions"):
                yield Button("退出", id="exit-button")
                yield Button("新建 profile", id="create-profile")
                yield Button("基于已选 profile 派生", id="derive-selected-profile")
                yield Button("立即运行已选 profile", id="run-selected-profile", variant="primary")
        self.call_after_refresh(self.refresh_profiles)

    def on_screen_resume(self) -> None:
        self.refresh_profiles()

    def refresh_profiles(self) -> None:
        try:
            summaries = self.app.list_profile_summaries()
        except ProfileError as exc:
            self.set_error_summary([str(exc)])
            return

        if not summaries:
            self.app.create_new_profile()
            return

        list_view = self.query_one("#profile-list", ListView)
        if self._summaries == summaries and list_view.children:
            return

        self._summaries = summaries
        if list_view.children:
            for child in list(list_view.children):
                child.remove()
        for summary in summaries:
            list_view.append(self._build_item(summary))
        list_view.index = 0
        self.set_error_summary([])

    def _build_item(self, summary: ProfileSummary) -> ListItem:
        return ListItem(
            Vertical(
                Static(summary.name, id=f"profile-name-{summary.name}", classes="profile-item-name"),
                Static(self._format_summary(summary), id=f"profile-meta-{summary.name}", classes="profile-item-meta"),
            ),
            name=summary.name,
            id=f"profile-item-{summary.name}",
            classes="profile-item",
        )

    def _format_summary(self, summary: ProfileSummary) -> str:
        targets = ", ".join(summary.upload_targets) if summary.upload_targets else "none"
        return (
            f"邮箱平台：{summary.email_provider} · 上传目标：{targets} · "
            f"账号数：{summary.total_accounts} · 并发：{summary.workers}"
        )

    def set_error_summary(self, messages: list[str]) -> None:
        self.query_one("#error-summary", Static).update("\n".join(f"- {message}" for message in messages if message))

    def _selected_profile_name(self) -> str | None:
        if not self._summaries:
            return None
        index = self.query_one("#profile-list", ListView).index
        if index is None:
            return self._summaries[0].name
        if index < 0 or index >= len(self._summaries):
            return None
        return self._summaries[index].name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "exit-button":
            self.app.request_exit_confirmation()
            return
        if button_id == "create-profile":
            self.app.create_new_profile()
            return

        profile_name = self._selected_profile_name()
        if not profile_name:
            self.set_error_summary(["请选择一个 profile 后再继续。"])
            return

        if button_id == "run-selected-profile":
            error = self.app.run_profile(profile_name)
            self.set_error_summary([error] if error else [])
        elif button_id == "derive-selected-profile":
            error = self.app.derive_profile(profile_name)
            self.set_error_summary([error] if error else [])
