from __future__ import annotations

import pytest
from textual.widgets import Button, Input, Static

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.config.profile import ProfileManager
from chatgpt_register.tui.app import WizardApp
from chatgpt_register.tui.state import WizardState


@pytest.mark.asyncio
async def test_summary_masks_sensitive_values_by_default(sample_duckmail_dict: dict) -> None:
    app = WizardApp(initial_config_dict=sample_duckmail_dict)

    async with app.run_test(size=(120, 60)) as pilot:
        app.go_to_step("summary")
        await pilot.pause()
        preview = app.screen.query_one("#summary-preview", Static)
        rendered = str(preview.render())
        assert "test-duckmail-token" not in rendered
        assert "te***en" in rendered


@pytest.mark.asyncio
async def test_summary_can_toggle_sensitive_visibility(sample_duckmail_dict: dict) -> None:
    app = WizardApp(initial_config_dict=sample_duckmail_dict)

    async with app.run_test(size=(120, 60)) as pilot:
        app.go_to_step("summary")
        await pilot.pause()
        app.screen.query_one("#toggle-summary-sensitive", Button).press()
        await pilot.pause()

        preview = app.screen.query_one("#summary-preview", Static)
        bearer_input = app.screen.query_one("#summary-duckmail-bearer", Input)
        assert "test-duckmail-token" in str(preview.render())
        assert bearer_input.password is False


@pytest.mark.asyncio
async def test_summary_returns_config_after_inline_edit(sample_duckmail_dict: dict) -> None:
    app = WizardApp(initial_config_dict=sample_duckmail_dict)

    async with app.run_test(size=(120, 60)) as pilot:
        app.go_to_step("summary")
        await pilot.pause()
        app.screen.query_one("#summary-total-accounts", Input).value = "7"
        await pilot.pause()
        app.screen.query_one("#next-button", Button).press()
        await pilot.pause()

        assert isinstance(app.return_value, RegisterConfig)
        assert app.return_value.registration.total_accounts == 7


@pytest.mark.asyncio
async def test_summary_cancel_save_does_not_persist_profile(tmp_profiles_dir, sample_duckmail_dict: dict) -> None:
    profile_manager = ProfileManager(base_dir=tmp_profiles_dir)
    app = WizardApp(profile_manager=profile_manager)
    app.wizard_state = WizardState.from_config_dict(sample_duckmail_dict, require_profile_save=True)

    async with app.run_test(size=(120, 60)) as pilot:
        app.go_to_step("summary")
        await pilot.pause()
        app.screen.query_one("#next-button", Button).press()
        await pilot.pause()
        app.screen.query_one("#save-profile-name", Input).value = "duckmail-new"
        await pilot.pause()
        app.screen.query_one("#cancel-save-profile", Button).press()
        await pilot.pause()

        assert app.current_screen_name == "summary"
        assert app.return_value is None
        assert profile_manager.exists("duckmail-new") is False


@pytest.mark.asyncio
async def test_summary_save_profile_returns_config_and_persists(tmp_profiles_dir, sample_duckmail_dict: dict) -> None:
    profile_manager = ProfileManager(base_dir=tmp_profiles_dir)
    app = WizardApp(profile_manager=profile_manager)
    app.wizard_state = WizardState.from_config_dict(sample_duckmail_dict, require_profile_save=True)

    async with app.run_test(size=(120, 60)) as pilot:
        app.go_to_step("summary")
        await pilot.pause()
        app.screen.query_one("#next-button", Button).press()
        await pilot.pause()
        app.screen.query_one("#save-profile-name", Input).value = "duckmail-new"
        await pilot.pause()
        app.screen.query_one("#confirm-save-profile", Button).press()
        await pilot.pause()

        assert isinstance(app.return_value, RegisterConfig)
        assert profile_manager.exists("duckmail-new") is True
        assert profile_manager.load("duckmail-new").email.provider == "duckmail"
