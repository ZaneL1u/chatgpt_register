from __future__ import annotations

import pytest
from textual.widgets import Button, ListView, Static

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.config.profile import ProfileManager
from chatgpt_register.tui.app import WizardApp



def _save_profile(profile_manager: ProfileManager, name: str, payload: dict) -> None:
    profile_manager.save(name, RegisterConfig.model_validate(payload))


@pytest.mark.asyncio
async def test_profile_screen_shows_saved_profiles_first(tmp_profiles_dir, sample_duckmail_dict: dict) -> None:
    profile_manager = ProfileManager(base_dir=tmp_profiles_dir)
    _save_profile(profile_manager, "duckmail-prod", sample_duckmail_dict)
    app = WizardApp(profile_manager=profile_manager)

    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()

        assert app.current_screen_name == "profile-select"
        assert "duckmail-prod" in str(app.screen.query_one("#profile-name-duckmail-prod", Static).render())
        meta = str(app.screen.query_one("#profile-meta-duckmail-prod", Static).render())
        assert "duckmail" in meta
        assert "cpa" in meta
        assert "账号数：5" in meta
        assert "并发：3" in meta


@pytest.mark.asyncio
async def test_profile_screen_skips_to_email_when_no_saved_profiles(tmp_profiles_dir) -> None:
    app = WizardApp(profile_manager=ProfileManager(base_dir=tmp_profiles_dir))

    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()

        assert app.current_screen_name == "email"
        app.screen.query_one("#email-provider")


@pytest.mark.asyncio
async def test_profile_screen_run_selected_profile_returns_config(tmp_profiles_dir, sample_duckmail_dict: dict) -> None:
    profile_manager = ProfileManager(base_dir=tmp_profiles_dir)
    _save_profile(profile_manager, "duckmail-prod", sample_duckmail_dict)
    app = WizardApp(profile_manager=profile_manager)

    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()
        app.screen.query_one("#run-selected-profile", Button).press()
        await pilot.pause()

        assert isinstance(app.return_value, RegisterConfig)
        assert app.return_value.email.provider == "duckmail"
        assert app.return_value.registration.total_accounts == 5


@pytest.mark.asyncio
async def test_profile_screen_derive_prefills_wizard_state(tmp_profiles_dir, sample_mailcow_dict: dict) -> None:
    profile_manager = ProfileManager(base_dir=tmp_profiles_dir)
    _save_profile(profile_manager, "mailcow-prod", sample_mailcow_dict)
    app = WizardApp(profile_manager=profile_manager)

    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()
        app.screen.query_one("#derive-selected-profile", Button).press()
        await pilot.pause()

        assert app.current_screen_name == "email"
        assert app.wizard_state.email_provider == "mailcow"
        assert app.wizard_state.source_profile_name == "mailcow-prod"
        assert app.wizard_state.require_profile_save is True
        assert app.wizard_state.draft_email["mailcow"]["api_url"] == "https://mail.example.com"
        assert not (tmp_profiles_dir / "mailcow-prod-copy.toml").exists()
