from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static

from snip.models.group import Group


class GroupItem(ListItem):
    """A single row in the group list, supporting hierarchical indentation."""

    def __init__(self, group: Group | None, count: int = 0, depth: int = 0, total_count: int = 0) -> None:
        super().__init__()
        self.group = group
        self.count = count
        self.depth = depth
        self.total_count = total_count

    def compose(self) -> ComposeResult:
        from snip import themes
        t = themes.current

        if self.group is None:
            label = "All Snippets"
            icon = "📁"
            indent = ""
            count_display = f"({self.count})"
        else:
            label = self.group.name
            indent = "  " * self.depth
            if self.depth > 0:
                indent += "└─ "

            icon = "📂" if self.total_count > 0 else "📁"
            if self.total_count > self.count:
                count_display = f"({self.count}+{self.total_count - self.count})"
            else:
                count_display = f"({self.count})"

        color_style = f"[{self.group.color}]" if self.group and self.group.color else ""
        yield Static(
            f"{indent}{icon}  {color_style}{label}[/]  [{t.text_dim}]{count_display}[/{t.text_dim}]",
            markup=True,
            classes="group-item-label",
        )


class GroupList(Widget):
    """Leftmost panel: navigable list of groups/folders with hierarchy support."""

    groups: reactive[list[Group]] = reactive([], layout=True)
    selected_group_id: reactive[str | None] = reactive(None, layout=True)

    def __init__(self, db, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._db = db

    def compose(self) -> ComposeResult:
        yield Static("GROUPS", classes="panel-label")
        yield ListView(id="group-list-view")

    def _get_group_by_id(self, group_id: str) -> Group | None:
        for group in self.groups:
            if group.id == group_id:
                return group
        return None

    def _get_group_depth(self, group_id: str) -> int:
        """Calculate how many levels deep a group is."""
        depth = 0
        current: str | None = group_id

        while current:
            group = self._get_group_by_id(current)
            if group and group.parent_id:
                depth += 1
                current = group.parent_id
            else:
                break

        return depth

    def _get_child_group_ids(self, parent_id: str | None) -> list[str]:
        """Get all direct child group IDs."""
        return [g.id for g in self.groups if g.id and g.parent_id == parent_id]

    def _get_all_descendant_ids(self, group_id: str) -> list[str]:
        """Get all descendant group IDs (children, grandchildren, etc.)."""
        descendants: list[str] = []
        to_check = [group_id]

        while to_check:
            current = to_check.pop()
            child_ids = self._get_child_group_ids(current)
            for child_id in child_ids:
                if child_id not in descendants:
                    descendants.append(child_id)
                    to_check.append(child_id)

        return descendants

    def _get_snippet_count_with_descendants(self, group_id: str | None) -> int:
        """Get snippet count including all descendant groups."""
        if group_id is None:
            return self._db.count()

        total = self._db.count_group(group_id)
        descendant_ids = self._get_all_descendant_ids(group_id)
        for desc_id in descendant_ids:
            total += self._db.count_group(desc_id)
        return total

    def _get_groups_sorted_hierarchically(self) -> list[Group]:
        """Sort groups hierarchically: parents before children, alphabetically at each level."""

        def sort_children(parent_id: str | None) -> list[Group]:
            children = [g for g in self.groups if g.parent_id == parent_id]
            children.sort(key=lambda g: g.name.lower())
            result: list[Group] = []
            for child in children:
                result.append(child)
                if child.id:
                    result.extend(sort_children(child.id))
            return result

        return sort_children(None)

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
        total_all = self._db.count()
        lv.append(GroupItem(None, all_count, 0, total_all))

        sorted_groups = self._get_groups_sorted_hierarchically()
        for group in sorted_groups:
            if group.id:
                depth = self._get_group_depth(group.id)
                count = counts.get(group.id, 0)
                total_count = self._get_snippet_count_with_descendants(group.id)
                lv.append(GroupItem(group, count, depth, total_count))

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
