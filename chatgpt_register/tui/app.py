"""Textual 向导应用。"""

from __future__ import annotations

from textual.app import App, ScreenStackError
from textual.binding import Binding
from textual.screen import Screen

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.tui.screens import ConfirmExitScreen, EmailScreen, RegistrationScreen, SummaryScreen, UploadScreen
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
        self.install_screen(UploadScreen(), "upload")
        self.install_screen(SummaryScreen(), "summary")
        self.install_screen(ConfirmExitScreen(), "confirm-exit")
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
