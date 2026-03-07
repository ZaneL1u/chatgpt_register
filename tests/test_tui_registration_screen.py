from __future__ import annotations

import pytest
from textual.widgets import Input, Static

from chatgpt_register.tui.app import WizardApp


@pytest.mark.asyncio
async def test_registration_invalid_numbers_block_navigation() -> None:
    app = WizardApp()

    async with app.run_test(size=(120, 40)) as pilot:
        app.go_to_step("registration")
        await pilot.pause()
        total_input = app.screen.query_one("#registration-total-accounts", Input)
        worker_input = app.screen.query_one("#registration-workers", Input)
        total_input.value = "0"
        worker_input.value = "9"
        await pilot.pause()
        await pilot.click("#next-button")
        await pilot.pause()

        summary = app.screen.query_one("#error-summary", Static)
        assert "注册账号数量必须是大于 0 的整数。" in str(summary.render())
        assert app.current_screen_name == "registration"


@pytest.mark.asyncio
async def test_registration_proxy_can_be_empty() -> None:
    app = WizardApp()

    async with app.run_test(size=(120, 40)) as pilot:
        app.go_to_step("registration")
        await pilot.pause()
        proxy_input = app.screen.query_one("#registration-proxy", Input)
        proxy_input.value = ""
        await pilot.pause()

        screen = app.screen
        errors = screen.validate_current_step()
        assert not any("代理地址" in message for message in errors)


@pytest.mark.asyncio
async def test_registration_valid_data_advances_to_upload_placeholder() -> None:
    app = WizardApp()

    async with app.run_test(size=(120, 40)) as pilot:
        app.go_to_step("registration")
        await pilot.pause()
        total_input = app.screen.query_one("#registration-total-accounts", Input)
        worker_input = app.screen.query_one("#registration-workers", Input)
        proxy_input = app.screen.query_one("#registration-proxy", Input)
        total_input.value = "4"
        worker_input.value = "2"
        proxy_input.value = ""
        await pilot.pause()
        await pilot.click("#next-button")
        await pilot.pause()

        assert app.current_screen_name == "upload"
