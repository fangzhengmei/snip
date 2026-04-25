from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea

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
        "input-parent",
        "input-description",
        "input-color",
        "btn-cancel",
        "btn-save",
    ]

    def __init__(
        self,
        group: Group | None = None,
        existing_groups: list[Group] | None = None,
    ) -> None:
        super().__init__()
        self._editing = group
        self._is_new = group is None
        self._existing_groups = existing_groups or []

    def _get_all_descendants(self, group_id: str) -> list[str]:
        """Get all descendant group IDs (children, grandchildren, etc.)"""
        descendants: list[str] = []
        to_check = [group_id]

        while to_check:
            current = to_check.pop()
            for group in self._existing_groups:
                if group.parent_id == current and group.id and group.id not in descendants:
                    descendants.append(group.id)
                    to_check.append(group.id)

        return descendants

    def _get_valid_parent_options(self) -> list[tuple[str, str | None]]:
        """Get valid parent options, excluding self and descendants"""
        options: list[tuple[str, str | None]] = [("(No Parent - Top Level)", None)]

        current_id = self._editing.id if self._editing else None
        excluded_ids: set[str] = set()

        if current_id:
            excluded_ids.add(current_id)
            excluded_ids.update(self._get_all_descendants(current_id))

        for group in self._existing_groups:
            if group.id and group.id not in excluded_ids:
                indent = self._get_group_depth(group.id)
                prefix = "  " * indent
                options.append((f"{prefix}└─ {group.name}", group.id))

        return options

    def _get_group_depth(self, group_id: str) -> int:
        """Calculate how many levels deep a group is (for indentation)"""
        depth = 0
        current: str | None = group_id

        while current:
            parent = next(
                (g for g in self._existing_groups if g.id == current),
                None,
            )
            if parent and parent.parent_id:
                depth += 1
                current = parent.parent_id
            else:
                break

        return depth

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
            yield Static("", id="error-message", classes="error-message")

            yield Label("parent group", classes="form-label")
            parent_options = self._get_valid_parent_options()
            current_parent_id = g.parent_id if g else None
            yield Select(
                parent_options,
                value=current_parent_id,
                id="input-parent",
                allow_blank=False,
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

    def _show_error(self, message: str) -> None:
        error_label = self.query_one("#error-message", Static)
        error_label.update(f"[#f7768e]\u26a0  {message}[/#f7768e]")

    def _clear_error(self) -> None:
        error_label = self.query_one("#error-message", Static)
        error_label.update("")

    def _is_duplicate_name(self, name: str) -> bool:
        current_id = self._editing.id if self._editing else None
        for group in self._existing_groups:
            if group.name.lower() == name.lower() and group.id != current_id:
                return True
        return False

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
        if isinstance(getattr(focused, "parent", None), Select):
            focused = focused.parent
        current_id = getattr(focused, "id", None)
        try:
            idx = self._FIELDS.index(current_id)
        except ValueError:
            return
        new_idx = max(0, min(idx + direction, len(self._FIELDS) - 1))
        if new_idx != idx:
            target = self.query_one(f"#{self._FIELDS[new_idx]}")
            target.focus()
            if isinstance(target, Select):
                target.action_show_overlay()

    def action_next_field(self) -> None:
        focused = self.focused
        if isinstance(focused, TextArea):
            row, _ = focused.cursor_location
            if row >= focused.document.line_count - 1:
                self._navigate(+1)
            else:
                focused.action_cursor_down()
        elif isinstance(getattr(focused, "parent", None), Select):
            overlay = focused
            at_bottom = (
                overlay.highlighted is None
                or overlay.highlighted >= overlay.option_count - 1
            )
            if at_bottom:
                select = focused.parent
                select.expanded = False
                select.focus()
                self._navigate(+1)
            else:
                overlay.action_cursor_down()
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
        elif isinstance(getattr(focused, "parent", None), Select):
            overlay = focused
            at_top = overlay.highlighted is None or overlay.highlighted <= 0
            if at_top:
                select = focused.parent
                select.expanded = False
                select.focus()
                self._navigate(-1)
            else:
                overlay.action_cursor_up()
        else:
            self._navigate(-1)

    def _save(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()

        if not name:
            self._show_error("Group name cannot be empty")
            self.query_one("#input-name", Input).focus()
            return

        if self._is_duplicate_name(name):
            self._show_error(f"A group named '{name}' already exists")
            self.query_one("#input-name", Input).focus()
            return

        parent_select: Select = self.query_one("#input-parent", Select)
        parent_id = parent_select.value if parent_select.value != Select.BLANK else None
        if parent_id == "":
            parent_id = None

        self._clear_error()

        description = self.query_one("#input-description", TextArea).text.strip()
        color = self.query_one("#input-color", Input).value.strip()

        if self._editing is not None:
            self._editing.name = name
            self._editing.parent_id = parent_id
            self._editing.description = description
            self._editing.color = color
            self.dismiss(self._editing)
        else:
            self.dismiss(
                Group(
                    name=name,
                    parent_id=parent_id,
                    description=description,
                    color=color,
                )
            )
