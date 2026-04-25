from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, TextArea

from snip.models.group import Group
from snip.models.snippet import SUPPORTED_LANGUAGES, Snippet


class EditScreen(ModalScreen[Snippet | None]):
    """Modal form for creating or editing a snippet."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("down", "next_field", show=False, priority=True),
        Binding("up", "prev_field", show=False, priority=True),
    ]

    _FIELDS = [
        "input-title",
        "input-group",
        "input-language",
        "input-description",
        "input-tags",
        "input-content",
        "btn-cancel",
        "btn-save",
    ]

    def __init__(
        self,
        snippet: Snippet | None = None,
        group_id: str | None = None,
        groups: list[Group] | None = None,
    ) -> None:
        super().__init__()
        self._editing = snippet
        self._is_new = snippet is None
        self._default_group_id = group_id
        self._groups = groups or []

    def compose(self) -> ComposeResult:
        s = self._editing
        verb = "new snippet" if self._is_new else "edit snippet"
        with Vertical():
            yield Label(
                f"[bold #7aa2f7]\u25c6[/bold #7aa2f7]  {verb}",
                markup=True,
                classes="modal-title",
            )
            yield Label("\u2500" * 60, classes="modal-divider")

            yield Label("title", classes="form-label")
            yield Input(
                value=s.title if s else "",
                placeholder="e.g. reverse a list in Python",
                id="input-title",
            )

            yield Label("group", classes="form-label")
            group_options = self._get_group_options()
            current_group_id = s.group_id if s else self._default_group_id
            yield Select(
                group_options,
                value=current_group_id,
                id="input-group",
                allow_blank=False,
            )

            yield Label("language", classes="form-label")
            options = [(lang, lang) for lang in SUPPORTED_LANGUAGES]
            yield Select(
                options,
                value=s.language if s else "text",
                id="input-language",
            )

            yield Label("description", classes="form-label")
            yield Input(
                value=s.description if s else "",
                placeholder="optional short description",
                id="input-description",
            )

            yield Label("tags  (space-separated)", classes="form-label")
            yield Input(
                value=" ".join(s.tags) if s else "",
                placeholder="e.g. python list utils",
                id="input-tags",
            )

            yield Label("code", classes="form-label")
            yield TextArea(
                text=s.content if s else "",
                language=None,
                id="input-content",
                tab_behavior="indent",
            )

            with Horizontal(classes="btn-row"):
                yield Button("cancel", variant="default", id="btn-cancel")
                yield Button("save", variant="primary", id="btn-save")

    def _get_group_options(self) -> list[tuple[str, str | None]]:
        options = [("All Snippets (No Group)", None)]
        for group in self._groups:
            if group.id:
                options.append((group.name, group.id))
        return options

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
        """Move focus through _FIELDS without wrapping. Opens Select when landing on it."""
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
        title = self.query_one("#input-title", Input).value.strip()
        if not title:
            self.query_one("#input-title", Input).focus()
            return

        content = self.query_one("#input-content", TextArea).text
        if not content.strip():
            self.query_one("#input-content", TextArea).focus()
            return

        lang_select: Select = self.query_one("#input-language", Select)
        language = (
            str(lang_select.value) if lang_select.value != Select.BLANK else "text"
        )

        group_select: Select = self.query_one("#input-group", Select)
        group_id = group_select.value if group_select.value != Select.BLANK else None
        if group_id == "":
            group_id = None

        description = self.query_one("#input-description", Input).value.strip()
        tags = [t for t in self.query_one("#input-tags", Input).value.strip().split() if t]

        if self._editing is not None:
            self._editing.title = title
            self._editing.content = content
            self._editing.language = language
            self._editing.group_id = group_id
            self._editing.description = description
            self._editing.tags = tags
            self.dismiss(self._editing)
        else:
            self.dismiss(
                Snippet(
                    title=title,
                    content=content,
                    language=language,
                    group_id=group_id,
                    description=description,
                    tags=tags,
                )
            )
