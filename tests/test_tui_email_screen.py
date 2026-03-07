from __future__ import annotations

import pytest
from textual.widgets import Button, Input, Static

from chatgpt_register.tui.app import WizardApp


@pytest.mark.asyncio
async def test_email_provider_switch_keeps_hidden_state() -> None:
    app = WizardApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#provider-duckmail")
        await pilot.click("#duckmail-bearer")
        await pilot.press("a", "b", "c")
        await pilot.click("#provider-mailcow")
        await pilot.pause()
        await pilot.click("#provider-duckmail")
        await pilot.pause()

        bearer_input = app.screen.query_one("#duckmail-bearer", Input)
        assert bearer_input.value == "abc"
        assert app.wizard_state.draft_email["duckmail"]["bearer"] == "abc"


@pytest.mark.asyncio
async def test_email_sensitive_field_can_toggle_visibility() -> None:
    app = WizardApp(initial_config_dict={"email": {"provider": "duckmail", "duckmail": {"api_base": "https://api.duckmail.sbs", "bearer": "token"}}})

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#provider-duckmail")
        bearer_input = app.screen.query_one("#duckmail-bearer", Input)
        assert bearer_input.password is True

        app.screen.query_one("#toggle-duckmail-bearer", Button).press()
        await pilot.pause()
        assert bearer_input.password is False


@pytest.mark.asyncio
async def test_email_validation_blocks_navigation() -> None:
    app = WizardApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#provider-duckmail")
        app.screen.query_one("#next-button", Button).press()
        await pilot.pause()

        summary = app.screen.query_one("#error-summary", Static)
        assert "DuckMail Bearer Token" in str(summary.render())
        assert app.current_screen_name == "email"
