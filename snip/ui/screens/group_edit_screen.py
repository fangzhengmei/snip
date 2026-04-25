from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea

from snip.models.group import Group


class GroupEditScreen(ModalScreen[Group | None]):
    """Modal form for creating or editing a group."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("down", "next_field", show=False, priority=True),
        Binding("up", "prev_field", show=False, priority=True),
    ]

    _FIELDS = [
        "input-name",
        "input-description",
        "input-color",
        "btn-cancel",
        "btn-save",
    ]

    def __init__(self, group: Group | None = None) -> None:
        super().__init__()
        self._editing = group
        self._is_new = group is None

    def compose(self) -> ComposeResult:
        g = self._editing
        verb = "new group" if self._is_new else "edit group"
        with Vertical():
            yield Label(
                f"[bold #7aa2f7]\u25c6[/bold #7aa2f7]  {verb}",
                markup=True,
                classes="modal-title",
            )
            yield Label("\u2500" * 60, classes="modal-divider")

            yield Label("name", classes="form-label")
            yield Input(
                value=g.name if g else "",
                placeholder="e.g. Python Utilities",
                id="input-name",
            )

            yield Label("description (optional)", classes="form-label")
            yield TextArea(
                text=g.description if g else "",
                id="input-description",
                tab_behavior="indent",
                height=3,
            )

            yield Label("color (optional, e.g. #ff5555)", classes="form-label")
            yield Input(
                value=g.color if g else "",
                placeholder="e.g. #ff5555 or red",
                id="input-color",
            )

            with Horizontal(classes="btn-row"):
                yield Button("cancel", variant="default", id="btn-cancel")
                yield Button("save", variant="primary", id="btn-save")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._navigate(+1)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            self._save()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_save(self) -> None:
        self._save()

    def _navigate(self, direction: int) -> None:
        focused = self.focused
        if focused is None:
            return
        current_id = getattr(focused, "id", None)
        try:
            idx = self._FIELDS.index(current_id)
        except ValueError:
            return
        new_idx = max(0, min(idx + direction, len(self._FIELDS) - 1))
        if new_idx != idx:
            target = self.query_one(f"#{self._FIELDS[new_idx]}")
            target.focus()

    def action_next_field(self) -> None:
        focused = self.focused
        if isinstance(focused, TextArea):
            row, _ = focused.cursor_location
            if row >= focused.document.line_count - 1:
                self._navigate(+1)
            else:
                focused.action_cursor_down()
        else:
            self._navigate(+1)

    def action_prev_field(self) -> None:
        focused = self.focused
        if isinstance(focused, TextArea):
            row, _ = focused.cursor_location
            if row == 0:
                self._navigate(-1)
            else:
                focused.action_cursor_up()
        else:
            self._navigate(-1)

    def _save(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        if not name:
            self.query_one("#input-name", Input).focus()
            return

        description = self.query_one("#input-description", TextArea).text.strip()
        color = self.query_one("#input-color", Input).value.strip()

        if self._editing is not None:
            self._editing.name = name
            self._editing.description = description
            self._editing.color = color
            self.dismiss(self._editing)
        else:
            self.dismiss(
                Group(
                    name=name,
                    description=description,
                    color=color,
                )
            )
