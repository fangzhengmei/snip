from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


@dataclass
class ImportResult:
    success: bool
    data: list[dict] | None = None
    error: str | None = None


class ImportScreen(ModalScreen[ImportResult]):
    """Modal for importing snippets from a JSON file."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "import", "Import", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                "[bold #7aa2f7]\u25c6[/bold #7aa2f7]  import snippets",
                markup=True,
                classes="modal-title",
            )
            yield Label("\u2500" * 60, classes="modal-divider")

            yield Label("JSON file path", classes="form-label")
            yield Input(
                placeholder="e.g. backup.json",
                id="input-path",
            )

            with Horizontal(classes="btn-row"):
                yield Button("cancel", variant="default", id="btn-cancel")
                yield Button("import", variant="primary", id="btn-import")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_import()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-import":
            self._do_import()

    def action_cancel(self) -> None:
        self.dismiss(ImportResult(success=False))

    def action_import(self) -> None:
        self._do_import()

    def _do_import(self) -> None:
        path_str = self.query_one("#input-path", Input).value.strip()
        if not path_str:
            self.query_one("#input-path", Input).focus()
            return

        path = Path(path_str).expanduser()
        if not path.exists():
            self.dismiss(ImportResult(success=False, error=f"file not found: {path_str}"))
            return

        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as e:
            self.dismiss(ImportResult(success=False, error=f"failed to read file: {e}"))
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            self.dismiss(ImportResult(success=False, error=f"invalid JSON: {e}"))
            return

        if not isinstance(data, list):
            self.dismiss(ImportResult(success=False, error="JSON must be an array of snippet objects"))
            return

        self.dismiss(ImportResult(success=True, data=data))
