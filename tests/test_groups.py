import pytest

from snip.models.group import Group
from snip.models.snippet import Snippet


class TestGroupModel:
    def test_group_creation(self):
        group = Group(name="Python Utils")
        assert group.name == "Python Utils"
        assert group.parent_id is None
        assert group.color == ""
        assert group.description == ""
        assert group.created_at is not None
        assert group.updated_at is not None

    def test_group_with_parent(self):
        group = Group(name="Sub Group", parent_id="parent123")
        assert group.parent_id == "parent123"

    def test_group_with_color(self):
        group = Group(name="Colored Group", color="#ff5555")
        assert group.color == "#ff5555"


class TestGroupCRUD:
    def test_create_group(self, tmp_db):
        group = Group(name="Test Group")
        created = tmp_db.create_group(group)
        assert created.id is not None
        assert created.name == "Test Group"

    def test_get_all_groups(self, tmp_db):
        assert tmp_db.get_all_groups() == []
        tmp_db.create_group(Group(name="Group 1"))
        tmp_db.create_group(Group(name="Group 2"))
        assert len(tmp_db.get_all_groups()) == 2

    def test_get_group_by_id(self, tmp_db):
        group = tmp_db.create_group(Group(name="Find Me"))
        fetched = tmp_db.get_group_by_id(group.id)
        assert fetched is not None
        assert fetched.name == "Find Me"

    def test_get_group_by_id_nonexistent(self, tmp_db):
        assert tmp_db.get_group_by_id("nonexistent") is None

    def test_update_group(self, tmp_db):
        group = tmp_db.create_group(Group(name="Original Name"))
        group.name = "Updated Name"
        tmp_db.update_group(group)
        fetched = tmp_db.get_group_by_id(group.id)
        assert fetched.name == "Updated Name"

    def test_delete_group(self, tmp_db):
        group = tmp_db.create_group(Group(name="To Delete"))
        assert tmp_db.delete_group(group.id) is True
        assert tmp_db.get_group_by_id(group.id) is None

    def test_delete_group_nonexistent(self, tmp_db):
        assert tmp_db.delete_group("nonexistent") is False

    def test_delete_group_moves_children(self, tmp_db):
        parent = tmp_db.create_group(Group(name="Parent"))
        child = tmp_db.create_group(Group(name="Child", parent_id=parent.id))
        assert child.parent_id == parent.id

        tmp_db.delete_group(parent.id)

        child_fetched = tmp_db.get_group_by_id(child.id)
        assert child_fetched.parent_id is None


class TestGroupSnippets:
    def test_get_by_group(self, tmp_db):
        group = tmp_db.create_group(Group(name="Python"))
        s1 = tmp_db.create(Snippet(title="In Group", content="a", group_id=group.id))
        s2 = tmp_db.create(Snippet(title="Not In Group", content="b"))

        in_group = tmp_db.get_by_group(group.id)
        assert len(in_group) == 1
        assert in_group[0].title == "In Group"

        not_in_group = tmp_db.get_by_group(None)
        assert len(not_in_group) == 1
        assert not_in_group[0].title == "Not In Group"

    def test_search_by_group(self, tmp_db):
        group = tmp_db.create_group(Group(name="Python"))
        tmp_db.create(Snippet(title="Python List", content="a", group_id=group.id))
        tmp_db.create(Snippet(title="Python Dict", content="b", group_id=group.id))
        tmp_db.create(Snippet(title="Bash Script", content="c"))

        results = tmp_db.search_by_group("python", group.id)
        assert len(results) == 2

        results_none = tmp_db.search_by_group("bash", None)
        assert len(results_none) == 1

    def test_count_group(self, tmp_db):
        group = tmp_db.create_group(Group(name="Test"))
        assert tmp_db.count_group(group.id) == 0

        tmp_db.create(Snippet(title="A", content="a", group_id=group.id))
        tmp_db.create(Snippet(title="B", content="b", group_id=group.id))

        assert tmp_db.count_group(group.id) == 2
        assert tmp_db.count_group(None) == 0

    def test_delete_group_moves_snippets(self, tmp_db):
        group = tmp_db.create_group(Group(name="Has Snippets"))
        snippet = tmp_db.create(Snippet(title="A", content="a", group_id=group.id))

        result = tmp_db.delete_group(group.id)
        assert result is True

        fetched = tmp_db.get_group_by_id(group.id)
        assert fetched is None

        snippet_fetched = tmp_db.get_by_id(snippet.id)
        assert snippet_fetched.group_id is None


class TestGroupValidation:
    def test_duplicate_name_check(self):
        from snip.models.group import Group

        group1 = Group(name="Python", id="id1")
        group2 = Group(name="python", id="id2")
        existing = [group1]

        from snip.ui.screens.group_edit_screen import GroupEditScreen
        screen = GroupEditScreen(existing_groups=existing)

        assert screen._is_duplicate_name("Python") is True
        assert screen._is_duplicate_name("PYTHON") is True
        assert screen._is_duplicate_name("Java") is False

    def test_edit_same_name_not_duplicate(self):
        from snip.models.group import Group

        group1 = Group(name="Python", id="id1")
        group2 = Group(name="Java", id="id2")
        existing = [group1, group2]

        from snip.ui.screens.group_edit_screen import GroupEditScreen
        screen = GroupEditScreen(group=group1, existing_groups=existing)

        assert screen._is_duplicate_name("Python") is False
        assert screen._is_duplicate_name("Java") is True
        assert screen._is_duplicate_name("NewName") is False
