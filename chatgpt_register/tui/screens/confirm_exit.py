"""退出确认弹窗。"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmExitScreen(ModalScreen[bool]):
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
