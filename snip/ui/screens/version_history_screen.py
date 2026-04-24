from __future__ import annotations

import difflib
from datetime import datetime
from typing import Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListView, ListItem, Static, TextArea

from snip.models.snippet import Snippet, SnippetVersion


def _format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _compute_diff(old_content: str, new_content: str) -> list[str]:
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="old", tofile="new", n=3))
    return diff


class VersionHistoryScreen(ModalScreen[Tuple[int, bool] | None]):
    """Modal for viewing version history of a snippet."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("down", "move_down", show=False),
        Binding("up", "move_up", show=False),
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("enter", "select_version", "Select Version", show=False),
        Binding("r", "restore_version", "Restore"),
        Binding("d", "toggle_diff", "Show/Hide Diff"),
    ]

    def __init__(self, snippet: Snippet, versions: list[SnippetVersion]) -> None:
        super().__init__()
        self._snippet = snippet
        self._versions = versions
        self._show_diff = True
        self._selected_version_idx = 0

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                f"[bold #7aa2f7]\u25c6[/bold #7aa2f7]  version history \u2013 {self._snippet.title}",
                markup=True,
                classes="modal-title",
            )
            yield Label("\u2500" * 60, classes="modal-divider")

            with Horizontal(classes="version-panels"):
                with Vertical(id="version-list-container"):
                    yield Label("versions (↑↓ to navigate, r to restore, d to toggle diff)", classes="form-label")
                    yield ListView(id="version-list")

                with Vertical(id="version-detail-container"):
                    yield Label("version detail / diff", classes="form-label")
                    yield Static(id="version-header", classes="version-header")
                    yield TextArea(
                        text="",
                        language=None,
                        id="version-content",
                        read_only=True,
                        tab_behavior="indent",
                    )

            with Horizontal(classes="btn-row"):
                yield Button("cancel", variant="default", id="btn-cancel")
                yield Button("restore selected version", variant="primary", id="btn-restore")

    def on_mount(self) -> None:
        self._populate_version_list()

    def _populate_version_list(self) -> None:
        version_list = self.query_one("#version-list", ListView)
        version_list.clear()

        if not self._versions:
            version_list.append(ListItem(Label("no versions available")))
            return

        for i, version in enumerate(self._versions):
            is_latest = i == 0
            version_text = (
                f"[bold]v{version.version}[/bold]"
                + (" [dim]\ufffd current[/dim]" if is_latest else "")
                + f"  [dim]{_format_datetime(version.created_at)}[/dim]"
                + f"  [dim]{version.short_summary}[/dim]"
            )
            item = ListItem(
                Label(version_text, markup=True),
                id=f"version-item-{version.version}",
            )
            version_list.append(item)

        if self._versions:
            version_list.index = self._selected_version_idx
            self._update_version_detail()

    def _get_selected_version(self) -> SnippetVersion | None:
        if not self._versions:
            return None
        version_list = self.query_one("#version-list", ListView)
        idx = version_list.index
        if idx is None or idx < 0 or idx >= len(self._versions):
            return None
        return self._versions[idx]

    def _update_version_detail(self) -> None:
        selected_version = self._get_selected_version()
        if selected_version is None:
            self.query_one("#version-content", TextArea).text = "no version selected"
            self.query_one("#version-header", Static).update("")
            return

        version_idx = self._versions.index(selected_version)
        prev_version = self._versions[version_idx + 1] if version_idx + 1 < len(self._versions) else None

        header = (
            f"[bold]Version {selected_version.version}[/bold]\n"
            f"Title: {selected_version.title}\n"
            f"Language: {selected_version.language}\n"
            f"Created: {_format_datetime(selected_version.created_at)}"
        )
        if selected_version.description:
            header += f"\nDescription: {selected_version.description}"
        if selected_version.tags:
            header += f"\nTags: {', '.join(selected_version.tags)}"

        self.query_one("#version-header", Static).update(header)

        content_area = self.query_one("#version-content", TextArea)
        if self._show_diff and prev_version is not None:
            diff_lines = _compute_diff(prev_version.content, selected_version.content)
            if diff_lines:
                content_area.text = "".join(diff_lines)
                content_area.language = "diff"
            else:
                content_area.text = selected_version.content
                content_area.language = None
        else:
            content_area.text = selected_version.content
            content_area.language = None

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        item_id = getattr(event.item, "id", None)
        if item_id and item_id.startswith("version-item-"):
            version_list = self.query_one("#version-list", ListView)
            self._selected_version_idx = version_list.index if version_list.index is not None else 0
            self._update_version_detail()

    def action_move_down(self) -> None:
        version_list = self.query_one("#version-list", ListView)
        version_list.action_cursor_down()

    def action_move_up(self) -> None:
        version_list = self.query_one("#version-list", ListView)
        version_list.action_cursor_up()

    def action_toggle_diff(self) -> None:
        self._show_diff = not self._show_diff
        self._update_version_detail()

    def action_select_version(self) -> None:
        self._restore_selected_version()

    def action_restore_version(self) -> None:
        self._restore_selected_version()

    def _restore_selected_version(self) -> None:
        selected_version = self._get_selected_version()
        if selected_version is None:
            return
        self.dismiss((selected_version.version, True))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-restore":
            self._restore_selected_version()

    def action_cancel(self) -> None:
        self.dismiss(None)
