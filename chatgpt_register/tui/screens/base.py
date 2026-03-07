"""TUI 向导 Screen 基类。"""

from __future__ import annotations

from typing import Iterable

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static


class BaseWizardScreen(Screen[None]):
    """提供统一标题、错误汇总与导航按钮。"""

    STEP_TITLE = ""
    STEP_HINT = ""
    NEXT_LABEL = "下一步"

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="wizard-scroll"):
            yield Static(self.STEP_TITLE, classes="step-title")
            yield Static(self.STEP_HINT, classes="step-hint")
            yield Static("", id="error-summary", classes="error-summary")
            yield from self.compose_body()
            with Horizontal(classes="wizard-actions"):
                yield Button("退出", id="exit-button")
                yield Button(self.NEXT_LABEL, id="next-button", variant="primary")

    def compose_body(self) -> ComposeResult:
        return
        yield

    @property
    def wizard_state(self):
        return self.app.wizard_state

    def set_error_summary(self, messages: Iterable[str]) -> None:
        summary = self.query_one("#error-summary", Static)
        text = "\n".join(f"- {message}" for message in messages if message)
        summary.update(text)

    def set_field_error(self, field_id: str, message: str) -> None:
        self.query_one(f"#{field_id}-error", Static).update(message)

    def clear_field_errors(self, field_ids: Iterable[str]) -> None:
        for field_id in field_ids:
            self.set_field_error(field_id, "")

    def go_to(self, screen_name: str) -> None:
        self.app.go_to_step(screen_name)

    def request_exit(self) -> None:
        self.app.request_exit_confirmation()

    def validate_current_step(self) -> list[str]:
        return []

    def handle_next(self) -> None:
        raise NotImplementedError

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exit-button":
            self.request_exit()
        elif event.button.id == "next-button":
            self.handle_next()
