from __future__ import annotations

import pytest
from textual.widgets import Button, Input, Select, Static

from chatgpt_register.tui.app import WizardApp


@pytest.mark.asyncio
async def test_upload_target_switch_keeps_hidden_state(sample_duckmail_dict: dict) -> None:
    app = WizardApp(initial_config_dict=sample_duckmail_dict)

    async with app.run_test(size=(120, 50)) as pilot:
        app.go_to_step("upload")
        await pilot.pause()
        token_input = app.screen.query_one("#cpa-api-token", Input)
        token_input.value = "persist-me"
        await pilot.pause()

        target = app.screen.query_one("#upload-target", Select)
        target.value = "sub2api"
        await pilot.pause()
        target.value = "cpa"
        await pilot.pause()

        assert app.wizard_state.upload["cpa"]["api_token"] == "persist-me"
        assert app.screen.query_one("#cpa-api-token", Input).value == "persist-me"


@pytest.mark.asyncio
async def test_upload_loads_sub2api_groups_into_state(monkeypatch, sample_mailcow_dict: dict) -> None:
    app = WizardApp(initial_config_dict=sample_mailcow_dict)

    monkeypatch.setattr(
        "chatgpt_register.tui.screens.upload.fetch_sub2api_openai_groups",
        lambda config, proxy="": [{"id": 7, "name": "Primary", "status": "active"}],
    )

    async with app.run_test(size=(120, 50)) as pilot:
        app.go_to_step("upload")
        await pilot.pause()
        target = app.screen.query_one("#upload-target", Select)
        target.value = "sub2api"
        await pilot.pause()
        app.screen.query_one("#sub2api-api-base", Input).value = "https://sub2api.example.com"
        app.screen.query_one("#sub2api-admin-api-key", Input).value = "admin-key"
        await pilot.pause()

        app.screen.query_one("#load-sub2api-groups", Button).press()
        await pilot.pause()

        assert app.wizard_state.upload["available_groups"][0]["id"] == 7
        assert app.wizard_state.upload["sub2api"]["selected_group_id"] == "7"


@pytest.mark.asyncio
async def test_upload_requires_sub2api_credentials_before_next(sample_mailcow_dict: dict) -> None:
    app = WizardApp(initial_config_dict=sample_mailcow_dict)

    async with app.run_test(size=(120, 50)) as pilot:
        app.go_to_step("upload")
        await pilot.pause()
        target = app.screen.query_one("#upload-target", Select)
        target.value = "sub2api"
        await pilot.pause()
        app.screen.query_one("#sub2api-api-base", Input).value = "https://sub2api.example.com"
        await pilot.pause()

        app.screen.query_one("#next-button", Button).press()
        await pilot.pause()

        summary = app.screen.query_one("#error-summary", Static)
        assert "Admin API Key 或 Bearer Token" in str(summary.render())
        assert app.current_screen_name == "upload"
