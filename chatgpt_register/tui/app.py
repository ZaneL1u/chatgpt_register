"""Textual 向导应用。"""

from __future__ import annotations

from textual.app import App, ScreenStackError
from textual.binding import Binding

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.config.profile import ProfileError, ProfileManager
from chatgpt_register.tui.screens import (
    ConfirmExitScreen,
    EmailScreen,
    ProfileSelectScreen,
    RegistrationScreen,
    SaveProfileScreen,
    SummaryScreen,
    UploadScreen,
)
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

    #profile-list {
        height: auto;
        max-height: 22;
        margin: 1 0;
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

    .profile-item {
        padding: 0 1;
        margin: 0 0 1 0;
        border: round $panel;
        height: auto;
    }

    .profile-item-name {
        text-style: bold;
    }

    .profile-item-meta {
        color: $text-muted;
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

    def __init__(self, initial_config_dict: dict | None = None, profile_manager: ProfileManager | None = None) -> None:
        super().__init__()
        self.profile_manager = profile_manager
        self.wizard_state = WizardState.from_config_dict(
            initial_config_dict,
            require_profile_save=initial_config_dict is None and profile_manager is not None,
        )
        self.current_screen_name = self._resolve_start_screen(initial_config_dict)

    def _resolve_start_screen(self, initial_config_dict: dict | None) -> str:
        if initial_config_dict is None and self.profile_manager is not None and self.profile_manager.list_profiles():
            return "profile-select"
        return "email"

    def on_mount(self) -> None:
        self.install_screen(ProfileSelectScreen(), "profile-select")
        self.install_screen(EmailScreen(), "email")
        self.install_screen(RegistrationScreen(), "registration")
        self.install_screen(UploadScreen(), "upload")
        self.install_screen(SummaryScreen(), "summary")
        self.install_screen(ConfirmExitScreen(), "confirm-exit")
        self.push_screen(self.current_screen_name)

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
        if isinstance(self.screen, ConfirmExitScreen):
            return
        self.push_screen("confirm-exit", self._handle_exit_confirmation)

    def _handle_exit_confirmation(self, should_exit: bool | None) -> None:
        if should_exit:
            self.exit(None)

    def list_profile_summaries(self):
        if self.profile_manager is None:
            return []
        return self.profile_manager.list_profile_summaries()

    def create_new_profile(self) -> None:
        self.wizard_state = WizardState.from_config_dict(
            require_profile_save=self.profile_manager is not None,
        )
        self.go_to_step("email")

    def run_profile(self, profile_name: str) -> str | None:
        try:
            config = self._load_profile(profile_name)
        except ProfileError as exc:
            return str(exc)
        if config is None:
            return "ProfileManager 未配置，无法直接运行已保存 profile。"
        self.exit(config)
        return None

    def derive_profile(self, profile_name: str) -> str | None:
        try:
            config = self._load_profile(profile_name)
        except ProfileError as exc:
            return str(exc)
        if config is None:
            return "ProfileManager 未配置，无法派生已保存 profile。"
        self.wizard_state = WizardState.from_config_dict(
            config.model_dump(mode="json", exclude_none=True),
            profile_name=f"{profile_name}-copy",
            source_profile_name=profile_name,
            require_profile_save=self.profile_manager is not None,
        )
        self.go_to_step("email")
        return None

    def should_prompt_profile_save(self) -> bool:
        return self.profile_manager is not None and self.wizard_state.require_profile_save

    def request_profile_save(self, config: RegisterConfig) -> None:
        if not self.should_prompt_profile_save() or self.profile_manager is None:
            self.exit(config)
            return
        self.push_screen(
            SaveProfileScreen(
                profile_manager=self.profile_manager,
                initial_name=self.wizard_state.profile_name,
                source_profile_name=self.wizard_state.source_profile_name,
            ),
            lambda profile_name: self._handle_profile_save(profile_name, config),
        )

    def _handle_profile_save(self, profile_name: str | None, config: RegisterConfig) -> None:
        if not profile_name or self.profile_manager is None:
            return
        self.profile_manager.save(profile_name, config)
        self.wizard_state.profile_name = profile_name
        self.wizard_state.require_profile_save = False
        self.exit(config)

    def _load_profile(self, profile_name: str) -> RegisterConfig | None:
        if self.profile_manager is None:
            return None
        return self.profile_manager.load(profile_name)
