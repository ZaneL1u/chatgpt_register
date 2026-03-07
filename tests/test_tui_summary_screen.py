from __future__ import annotations

import pytest
from textual.widgets import Button, Input, Static

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.tui.app import WizardApp


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
