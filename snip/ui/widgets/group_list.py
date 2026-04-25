from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static

from snip.models.group import Group


class GroupItem(ListItem):
    """A single row in the group list."""

    def __init__(self, group: Group | None, count: int = 0) -> None:
        super().__init__()
        self.group = group
        self.count = count

    def compose(self) -> ComposeResult:
        from snip import themes
        t = themes.current
        if self.group is None:
            label = "All Snippets"
            icon = "📁"
        else:
            label = self.group.name
            icon = "📂" if self.count > 0 else "📁"

        color_style = f"[{self.group.color}]" if self.group and self.group.color else ""
        yield Static(
            f"{icon}  {color_style}{label}[/]  [{t.text_dim}]({self.count})[/{t.text_dim}]",
            markup=True,
            classes="group-item-label",
        )


class GroupList(Widget):
    """Leftmost panel: navigable list of groups/folders."""

    groups: reactive[list[Group]] = reactive([], layout=True)
    selected_group_id: reactive[str | None] = reactive(None, layout=True)

    def __init__(self, db, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._db = db

    def compose(self) -> ComposeResult:
        yield Static("GROUPS", classes="panel-label")
        yield ListView(id="group-list-view")

    def _get_group_counts(self) -> dict[str | None, int]:
        counts: dict[str | None, int] = {}
        counts[None] = self._db.count()
        for group in self.groups:
            if group.id:
                counts[group.id] = self._db.count_group(group.id)
                counts[None] -= counts[group.id]
        return counts

    def watch_groups(self, groups: list[Group]) -> None:
        lv: ListView = self.query_one("#group-list-view", ListView)
        lv.clear()

        counts = self._get_group_counts()

        all_count = counts.get(None, 0)
        lv.append(GroupItem(None, all_count))

        for group in groups:
            if group.id:
                count = counts.get(group.id, 0)
                lv.append(GroupItem(group, count))

    def selected_group(self) -> Group | None:
        lv: ListView = self.query_one("#group-list-view", ListView)
        if lv.highlighted_child is None:
            return None
        item = lv.highlighted_child
        if isinstance(item, GroupItem):
            return item.group
        return None

    def highlight_by_group_id(self, group_id: str | None) -> None:
        lv = self.query_one("#group-list-view", ListView)
        for i, child in enumerate(lv.children):
            if isinstance(child, GroupItem):
                if child.group is None and group_id is None:
                    lv.index = i
                    return
                if child.group is not None and child.group.id == group_id:
                    lv.index = i
                    return

    def move_down(self) -> None:
        self.query_one("#group-list-view", ListView).action_cursor_down()

    def move_up(self) -> None:
        self.query_one("#group-list-view", ListView).action_cursor_up()

    def refresh_counts(self) -> None:
        self.watch_groups(self.groups)
