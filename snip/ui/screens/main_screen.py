from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Input, Label, ListView, Static

from snip.models.group import Group
from snip.models.snippet import Snippet
from snip.ui.widgets.app_header import AppHeader
from snip.ui.widgets.group_list import GroupItem, GroupList
from snip.ui.widgets.snippet_list import SnippetItem, SnippetList
from snip.ui.widgets.snippet_preview import SnippetPreview


class MainScreen(Screen):
    """The primary TUI screen."""

    MIN_WIDTH = 80
    MIN_HEIGHT = 12

    BINDINGS = [
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False, priority=True),
        Binding("up", "move_up", "Up", show=False, priority=True),
        Binding("tab", "switch_focus", "Switch Panel"),
        Binding("shift+tab", "switch_focus_back", "Switch Panel", show=False),
        Binding("n", "new_snippet", "New"),
        Binding("e", "edit_snippet", "Edit"),
        Binding("d", "delete_snippet", "Delete"),
        Binding("y", "yank_snippet", "Copy"),
        Binding("p", "pin_snippet", "Pin"),
        Binding("g", "new_group", "New Group"),
        Binding("r", "rename_group", "Rename Group"),
        Binding("shift+d", "delete_group", "Delete Group"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with Horizontal(classes="search-bar"):
            yield Label("/", classes="search-label")
            yield Input(placeholder="search snippets...", id="search-input")
        with Horizontal(classes="panels"):
            yield GroupList(self._db, id="group-list")
            yield SnippetList(id="snippet-list")
            yield SnippetPreview(id="snippet-preview")
        yield Static("", id="status-bar", classes="status-bar")
        yield Footer()
        with Vertical(id="too-small-overlay"):
            yield Static(
                f"terminal too small\nminimum {self.MIN_WIDTH}\u00d7{self.MIN_HEIGHT}"
            )

    def on_mount(self) -> None:
        self._refresh_groups()
        self._refresh_list()
        self.query_one("#snippet-list", SnippetList).query_one(
            "#list-view", ListView
        ).focus()

    def on_resize(self, event) -> None:  # type: ignore[override]
        too_small = (
            event.size.width < self.MIN_WIDTH or event.size.height < self.MIN_HEIGHT
        )
        self.query_one("#too-small-overlay").display = too_small

    def _refresh_groups(self) -> None:
        gl: GroupList = self.query_one("#group-list", GroupList)
        gl.groups = self._db.get_all_groups()

    def _get_current_group_id(self) -> str | None:
        gl: GroupList = self.query_one("#group-list", GroupList)
        selected_group = gl.selected_group()
        if selected_group is None:
            return None
        return selected_group.id

    def _refresh_list(self, query: str = "", select_id: str | None = None) -> None:
        group_id = self._get_current_group_id()

        if query:
            if group_id is None:
                snippets = self._db.search(query)
            else:
                snippets = self._db.search_by_group_with_descendants(query, group_id)
        else:
            if group_id is None:
                snippets = self._db.get_all()
            else:
                snippets = self._db.get_by_group_with_descendants(group_id)

        sl: SnippetList = self.query_one("#snippet-list", SnippetList)
        sl.snippets = snippets

        target: Snippet | None = None
        if select_id is not None:
            target = next((s for s in snippets if s.id == select_id), None)
        if target is None and snippets:
            target = snippets[0]

        if target is not None:
            self._update_preview(target)
            sl.highlight_by_id(target.id)
        else:
            self.query_one("#snippet-preview", SnippetPreview).snippet = None

        gl: GroupList = self.query_one("#group-list", GroupList)
        gl.refresh_counts()

        if group_id is None:
            total = self._db.count()
        else:
            total = self._db.count_group_with_descendants(group_id)
        self._update_status(len(snippets), total)

    def _update_preview(self, snippet: Snippet | None) -> None:
        self.query_one("#snippet-preview", SnippetPreview).snippet = snippet

    def _update_status(self, shown: int, total: int) -> None:
        gl: GroupList = self.query_one("#group-list", GroupList)
        selected_group = gl.selected_group()

        group_label = ""
        if selected_group is None:
            group_label = "All Snippets"
        else:
            group_label = selected_group.name

        count = f"{shown}/{total} snippet{'s' if total != 1 else ''}"
        group_info = f"  \u00b7  [{group_label}]"
        filt = f"  \u00b7  \"{self._query}\"" if self._query else ""
        self.query_one("#status-bar", Static).update(count + group_info + filt)

    def __init__(self, db) -> None:  # type: ignore[override]
        super().__init__()
        self._db = db
        self._query = ""
        self._focused_panel = "snippet"

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._query = event.value
            self._refresh_list(self._query)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        if isinstance(event.item, SnippetItem):
            self._update_preview(event.item.snippet)
        elif isinstance(event.item, GroupItem):
            self._refresh_list(self._query)

    def _get_focused_list(self) -> SnippetList | GroupList | None:
        sl = self.query_one("#snippet-list", SnippetList)
        gl = self.query_one("#group-list", GroupList)

        sl_list = sl.query_one("#list-view", ListView)
        gl_list = gl.query_one("#group-list-view", ListView)

        if sl_list.has_focus:
            return sl
        if gl_list.has_focus:
            return gl
        return None

    def action_move_down(self) -> None:
        focused = self._get_focused_list()
        if focused is not None:
            focused.move_down()

    def action_move_up(self) -> None:
        focused = self._get_focused_list()
        if focused is not None:
            focused.move_up()

    def action_switch_focus(self) -> None:
        sl = self.query_one("#snippet-list", SnippetList)
        gl = self.query_one("#group-list", GroupList)

        sl_list = sl.query_one("#list-view", ListView)
        gl_list = gl.query_one("#group-list-view", ListView)

        if gl_list.has_focus:
            sl_list.focus()
        else:
            gl_list.focus()

    def action_switch_focus_back(self) -> None:
        self.action_switch_focus()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_clear_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        if inp.value:
            inp.clear()
            self._query = ""
            self._refresh_list()
        else:
            focused = self._get_focused_list()
            if isinstance(focused, SnippetList):
                focused.query_one("#list-view", ListView).focus()
            elif isinstance(focused, GroupList):
                focused.query_one("#group-list-view", ListView).focus()

    def action_new_snippet(self) -> None:
        from snip.ui.screens.edit_screen import EditScreen

        group_id = self._get_current_group_id()
        groups = self._db.get_all_groups()

        def _on_result(result: Snippet | None) -> None:
            if result is not None:
                self._db.create(result)
                self._refresh_list(self._query, select_id=result.id)
                self._flash(f"created \u2018{result.title}\u2019")

        self.app.push_screen(EditScreen(group_id=group_id, groups=groups), _on_result)

    def action_edit_snippet(self) -> None:
        from snip.ui.screens.edit_screen import EditScreen

        snippet = self.query_one("#snippet-list", SnippetList).highlighted_snippet()
        if snippet is None:
            return

        groups = self._db.get_all_groups()

        def _on_result(result: Snippet | None) -> None:
            if result is not None:
                self._db.update(result)
                self._refresh_list(self._query, select_id=result.id)
                self._flash(f"updated \u2018{result.title}\u2019")

        self.app.push_screen(EditScreen(snippet, groups=groups), _on_result)

    def action_delete_snippet(self) -> None:
        snippet = self.query_one("#snippet-list", SnippetList).highlighted_snippet()
        if snippet is None or snippet.id is None:
            return
        title = snippet.title
        self._db.delete(snippet.id)
        self._refresh_list(self._query)
        self._flash(f"deleted \u2018{title}\u2019")

    def action_yank_snippet(self) -> None:
        snippet = self.query_one("#snippet-list", SnippetList).highlighted_snippet()
        if snippet is None:
            return
        from snip.utils.clipboard import copy_to_clipboard

        if copy_to_clipboard(snippet.content):
            self._flash(f"copied \u2018{snippet.title}\u2019 to clipboard")
        else:
            self._flash("clipboard unavailable \u2013 install pyperclip")

    def action_pin_snippet(self) -> None:
        snippet = self.query_one("#snippet-list", SnippetList).highlighted_snippet()
        if snippet is None or snippet.id is None:
            return
        snippet_id = snippet.id
        pinned = self._db.toggle_pin(snippet_id)
        self._refresh_list(self._query, select_id=snippet_id)
        state = "pinned" if pinned else "unpinned"
        self._flash(f"\u2018{snippet.title}\u2019 {state}")

    def action_new_group(self) -> None:
        from snip.ui.screens.group_edit_screen import GroupEditScreen

        existing_groups = self._db.get_all_groups()

        def _on_result(result: Group | None) -> None:
            if result is not None:
                self._db.create_group(result)
                self._refresh_groups()
                self._flash(f"created group \u2018{result.name}\u2019")

        self.app.push_screen(GroupEditScreen(existing_groups=existing_groups), _on_result)

    def action_rename_group(self) -> None:
        from snip.ui.screens.group_edit_screen import GroupEditScreen

        gl: GroupList = self.query_one("#group-list", GroupList)
        group = gl.selected_group()
        if group is None:
            self._flash("no group selected")
            return

        existing_groups = self._db.get_all_groups()

        def _on_result(result: Group | None) -> None:
            if result is not None:
                self._db.update_group(result)
                self._refresh_groups()
                self._flash(f"renamed group to \u2018{result.name}\u2019")

        self.app.push_screen(GroupEditScreen(group, existing_groups=existing_groups), _on_result)

    def action_delete_group(self) -> None:
        gl: GroupList = self.query_one("#group-list", GroupList)
        group = gl.selected_group()
        if group is None or group.id is None:
            self._flash("no group selected")
            return

        group_name = group.name
        group_id = group.id

        direct_snippets = self._db.count_group(group_id)
        total_snippets = self._db.count_group_with_descendants(group_id)

        if total_snippets > 0:
            if direct_snippets == total_snippets:
                self._flash(f"group \u2018{group_name}\u2019 has {total_snippets} snippet(s) - move them first")
            else:
                child_snippets = total_snippets - direct_snippets
                self._flash(f"group \u2018{group_name}\u2019 has {total_snippets} snippet(s) ({direct_snippets} direct + {child_snippets} in subgroups) - move them first")
            return

        self._db.delete_group(group_id)
        self._refresh_groups()
        self._refresh_list(self._query)
        self._flash(f"deleted group \u2018{group_name}\u2019")

    def action_quit(self) -> None:
        self.app.exit()

    def _flash(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(f"\u2713  {msg}")
