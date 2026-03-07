"""Textual 向导应用。"""

from __future__ import annotations

from textual.app import App, ComposeResult, ScreenStackError
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Static

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.tui.screens import EmailScreen, RegistrationScreen
from chatgpt_register.tui.state import WizardState


class WizardApp(App[RegisterConfig | None]):
    """四步配置向导。"""

    CSS = """
    Screen {
        align: center top;
    }

    #wizard-scroll {
        width: 86;
        max-width: 96;
        padding: 1 2;
    }

    .step-title {
        text-style: bold;
        margin: 0 0 1 0;
    }

    .step-hint {
        color: $text-muted;
        margin: 0 0 1 0;
    }

    .error-summary {
        color: $error;
        margin: 0 0 1 0;
    }

    .field-block {
        margin: 0 0 1 0;
    }

    .field-label {
        margin: 0 0 1 0;
    }

    .field-error {
        color: $error;
        margin: 1 0 0 0;
    }

    .wizard-actions {
        margin: 1 0 2 0;
        height: auto;
    }

    .wizard-actions Button {
        margin-right: 1;
    }

    .sensitive-row Button {
        margin-left: 1;
    }

    #modal-body {
        width: 50;
        padding: 1 2;
        border: round $warning;
        background: $surface;
    }

    .placeholder {
        padding: 2;
        border: round $panel;
    }
    """

    BINDINGS = [
        Binding("escape", "request_exit", "退出"),
        Binding("ctrl+c", "request_exit", "退出"),
    ]

    def __init__(self, initial_config_dict: dict | None = None) -> None:
        super().__init__()
        self.wizard_state = WizardState.from_config_dict(initial_config_dict)
        self.current_screen_name = "email"

    def on_mount(self) -> None:
        self.install_screen(EmailScreen(), "email")
        self.install_screen(RegistrationScreen(), "registration")
        self.install_screen(_PlaceholderScreen("步骤 3/4 · 上传目标", "上传目标页将在 Wave 2 完成；当前占位仅用于验证线性导航。"), "upload")
        self.install_screen(_PlaceholderScreen("步骤 4/4 · 确认摘要", "确认摘要页将在 Wave 2 完成；当前占位仅用于保留 Screen 名称。"), "summary")
        self.install_screen(_ConfirmExitScreen(), "confirm-exit")
        self.current_screen_name = "email"
        self.push_screen("email")

    def go_to_step(self, screen_name: str) -> None:
        self.current_screen_name = screen_name
        try:
            self.screen
        except ScreenStackError:
            self.push_screen(screen_name)
            return
        self.switch_screen(screen_name)

    def action_request_exit(self) -> None:
        self.request_exit_confirmation()

    def request_exit_confirmation(self) -> None:
        if isinstance(self.screen, _ConfirmExitScreen):
            return
        self.push_screen("confirm-exit", self._handle_exit_confirmation)

    def _handle_exit_confirmation(self, should_exit: bool | None) -> None:
        if should_exit:
            self.exit(None)


class _PlaceholderScreen(Screen[None]):
    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.title_text = title
        self.description_text = description

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.title_text, classes="step-title"),
            Static(self.description_text, classes="placeholder"),
        )


class _ConfirmExitScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Container(
            Static("确认退出当前向导？", classes="step-title"),
            Static("未保存的表单改动会丢失。"),
            Horizontal(
                Button("继续编辑", id="cancel-exit"),
                Button("确认退出", id="confirm-exit", variant="error"),
                classes="wizard-actions",
            ),
            id="modal-body",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-exit":
            self.dismiss(False)
        elif event.button.id == "confirm-exit":
            self.dismiss(True)
