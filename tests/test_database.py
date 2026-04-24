import sqlite3

import pytest

from snip.models.snippet import Snippet
from snip.storage.database import Database, _parse_file, _to_file_text


class TestCreate:
    def test_assigns_string_id(self, tmp_db, sample_snippet):
        result = tmp_db.create(sample_snippet)
        assert result.id is not None
        assert isinstance(result.id, str)
        assert len(result.id) == 12

    def test_sets_timestamps(self, tmp_db, sample_snippet):
        result = tmp_db.create(sample_snippet)
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_persists_all_fields(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        fetched = tmp_db.get_by_id(sample_snippet.id)
        assert fetched is not None
        assert fetched.title == sample_snippet.title
        assert fetched.content == sample_snippet.content
        assert fetched.language == sample_snippet.language
        assert fetched.description == sample_snippet.description
        assert fetched.tags == sample_snippet.tags

    def test_writes_markdown_file(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        files = list((tmp_db._dir).glob("*.md"))
        assert len(files) == 1

    def test_ids_are_unique(self, tmp_db):
        a = tmp_db.create(Snippet(title="A", content="a"))
        b = tmp_db.create(Snippet(title="B", content="b"))
        assert a.id != b.id


class TestGetAll:
    def test_empty_returns_empty_list(self, tmp_db):
        assert tmp_db.get_all() == []

    def test_returns_all_created_snippets(self, tmp_db):
        tmp_db.create(Snippet(title="A", content="a"))
        tmp_db.create(Snippet(title="B", content="b"))
        assert len(tmp_db.get_all()) == 2

    def test_pinned_snippets_come_first(self, tmp_db):
        tmp_db.create(Snippet(title="Normal", content="n"))
        tmp_db.create(Snippet(title="Pinned", content="p", pinned=True))
        results = tmp_db.get_all()
        assert results[0].title == "Pinned"


class TestUpdate:
    def test_updates_title(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        sample_snippet.title = "Updated Title"
        tmp_db.update(sample_snippet)
        fetched = tmp_db.get_by_id(sample_snippet.id)
        assert fetched.title == "Updated Title"

    def test_updates_tags(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        sample_snippet.tags = ["new", "tags"]
        tmp_db.update(sample_snippet)
        fetched = tmp_db.get_by_id(sample_snippet.id)
        assert fetched.tags == ["new", "tags"]

    def test_bumps_updated_at(self, tmp_db, sample_snippet):
        import time
        tmp_db.create(sample_snippet)
        before = sample_snippet.updated_at
        time.sleep(0.01)
        tmp_db.update(sample_snippet)
        fetched = tmp_db.get_by_id(sample_snippet.id)
        assert fetched.updated_at > before


class TestDelete:
    def test_delete_removes_snippet(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        assert tmp_db.delete(sample_snippet.id) is True
        assert tmp_db.get_by_id(sample_snippet.id) is None

    def test_delete_removes_file(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        tmp_db.delete(sample_snippet.id)
        assert not list(tmp_db._dir.glob("*.md"))

    def test_delete_nonexistent_returns_false(self, tmp_db):
        assert tmp_db.delete("nonexistentid") is False

    def test_count_decreases_after_delete(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        tmp_db.delete(sample_snippet.id)
        assert tmp_db.count() == 0


class TestSearch:
    def test_search_by_title(self, tmp_db):
        tmp_db.create(Snippet(title="Docker prune", content="docker system prune -a"))
        tmp_db.create(Snippet(title="Git reset", content="git reset --hard"))
        results = tmp_db.search("docker")
        assert len(results) == 1
        assert results[0].title == "Docker prune"

    def test_search_returns_all_on_empty_query(self, tmp_db):
        tmp_db.create(Snippet(title="A", content="a"))
        tmp_db.create(Snippet(title="B", content="b"))
        assert len(tmp_db.search("")) == 2

    def test_search_by_tag(self, tmp_db):
        tmp_db.create(Snippet(title="A", content="a", tags=["networking"]))
        tmp_db.create(Snippet(title="B", content="b", tags=["git"]))
        results = tmp_db.search("networking")
        assert len(results) == 1


class TestTogglePin:
    def test_pin_unpinned_snippet(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)
        result = tmp_db.toggle_pin(sample_snippet.id)
        assert result is True
        assert tmp_db.get_by_id(sample_snippet.id).pinned is True

    def test_unpin_pinned_snippet(self, tmp_db):
        s = Snippet(title="t", content="c", pinned=True)
        tmp_db.create(s)
        result = tmp_db.toggle_pin(s.id)
        assert result is False
        assert tmp_db.get_by_id(s.id).pinned is False

    def test_toggle_nonexistent_returns_false(self, tmp_db):
        assert tmp_db.toggle_pin("nonexistentid") is False


class TestCount:
    def test_empty_db_count_zero(self, tmp_db):
        assert tmp_db.count() == 0

    def test_count_reflects_creates(self, tmp_db):
        tmp_db.create(Snippet(title="A", content="a"))
        tmp_db.create(Snippet(title="B", content="b"))
        assert tmp_db.count() == 2


class TestSync:
    def test_new_instance_reads_existing_files(self, tmp_path):
        dir1 = tmp_path / "snippets"
        db1 = Database(dir1)
        db1.create(Snippet(title="Persisted", content="data"))

        db2 = Database(dir1)
        assert db2.count() == 1
        assert db2.get_all()[0].title == "Persisted"

    def test_file_added_externally_is_synced(self, tmp_path):
        from datetime import datetime

        from snip.storage.database import _to_file_text

        dir1 = tmp_path / "snippets"
        Database(dir1)

        s = Snippet(title="External", content="added externally")
        s.id = "externalabc1"
        s.created_at = datetime.now()
        s.updated_at = datetime.now()
        (dir1 / f"{s.id}.md").write_text(_to_file_text(s), encoding="utf-8")

        db2 = Database(dir1)
        assert db2.get_by_id("externalabc1") is not None


class TestMigration:
    def test_migrates_legacy_sqlite(self, tmp_path):
        import json
        from datetime import datetime

        snippets_dir = tmp_path / "snippets"
        old_db_path = tmp_path / "snip.db"

        conn = sqlite3.connect(old_db_path)
        conn.execute("""
            CREATE TABLE snippets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                content     TEXT NOT NULL,
                language    TEXT NOT NULL DEFAULT 'text',
                description TEXT NOT NULL DEFAULT '',
                tags        TEXT NOT NULL DEFAULT '[]',
                pinned      INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO snippets (title, content, language, description, tags, pinned, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("Old snippet", "old content", "python", "", json.dumps(["old"]), 0, now, now),
        )
        conn.commit()
        conn.close()

        db = Database(snippets_dir)
        assert db.count() == 1
        snippet = db.get_all()[0]
        assert snippet.title == "Old snippet"
        assert snippet.tags == ["old"]
        conn2 = sqlite3.connect(old_db_path)
        pragma = {row[1]: row[2] for row in conn2.execute("PRAGMA table_info(snippets)").fetchall()}
        conn2.close()
        assert pragma["id"] == "TEXT"

    def test_skips_migration_if_files_exist(self, tmp_path):
        import json
        from datetime import datetime

        snippets_dir = tmp_path / "snippets"
        snippets_dir.mkdir()
        old_db_path = tmp_path / "snip.db"

        conn = sqlite3.connect(old_db_path)
        conn.execute("""
            CREATE TABLE snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, content TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'text',
                description TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO snippets (title, content, language, description, tags, pinned, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("From old db", "content", "python", "", json.dumps([]), 0, now, now),
        )
        conn.commit()
        conn.close()

        existing = Snippet(title="Existing", content="already here")
        existing.id = "existingfile1"
        existing.created_at = datetime.now()
        existing.updated_at = datetime.now()
        (snippets_dir / f"{existing.id}.md").write_text(_to_file_text(existing), encoding="utf-8")

        db = Database(snippets_dir)
        titles = {s.title for s in db.get_all()}
        assert "Existing" in titles
        assert "From old db" not in titles


class TestFileFormat:
    def test_round_trip_preserves_content_with_separator(self, tmp_db):
        content = "line1\n---\nline2"
        s = tmp_db.create(Snippet(title="sep-test", content=content))
        fetched = tmp_db.get_by_id(s.id)
        assert fetched.content == content

    def test_round_trip_preserves_empty_tags(self, tmp_db):
        s = tmp_db.create(Snippet(title="t", content="c", tags=[]))
        fetched = tmp_db.get_by_id(s.id)
        assert fetched.tags == []

    def test_round_trip_preserves_description_with_colon(self, tmp_db):
        s = tmp_db.create(Snippet(title="t", content="c", description="key: value"))
        fetched = tmp_db.get_by_id(s.id)
        assert fetched.description == "key: value"

    def test_parse_file_invalid_raises(self):
        with pytest.raises((ValueError, KeyError)):
            _parse_file("no frontmatter here")


class TestVersionTracking:
    def test_create_snippet_creates_version_1(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)
        versions = tmp_db.get_versions(created.id)
        assert len(versions) == 1
        assert versions[0].version == 1
        assert versions[0].title == sample_snippet.title
        assert versions[0].content == sample_snippet.content
        assert versions[0].snippet_id == created.id

    def test_update_creates_new_version(self, tmp_db, sample_snippet):
        import time

        created = tmp_db.create(sample_snippet)
        time.sleep(0.001)

        created.content = "updated content"
        tmp_db.update(created)

        versions = tmp_db.get_versions(created.id)
        assert len(versions) == 2
        assert versions[0].version == 2
        assert versions[1].version == 1
        assert versions[0].content == "updated content"
        assert versions[1].content == sample_snippet.content

    def test_update_without_create_version_flag(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)
        versions_before = tmp_db.count_versions(created.id)

        created.content = "updated without version"
        tmp_db.update(created, create_version=False)

        versions_after = tmp_db.count_versions(created.id)
        assert versions_after == versions_before

    def test_get_version_retrieves_specific_version(self, tmp_db):
        snippet = Snippet(title="V1", content="content v1")
        created = tmp_db.create(snippet)

        created.title = "V2"
        created.content = "content v2"
        tmp_db.update(created)

        v1 = tmp_db.get_version(created.id, 1)
        v2 = tmp_db.get_version(created.id, 2)

        assert v1 is not None
        assert v1.version == 1
        assert v1.title == "V1"
        assert v1.content == "content v1"

        assert v2 is not None
        assert v2.version == 2
        assert v2.title == "V2"
        assert v2.content == "content v2"

    def test_get_version_returns_none_for_nonexistent(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)
        assert tmp_db.get_version(created.id, 999) is None
        assert tmp_db.get_version("nonexistent", 1) is None

    def test_restore_version(self, tmp_db):
        snippet = Snippet(title="Original", content="original content", tags=["orig"])
        created = tmp_db.create(snippet)

        created.title = "Modified"
        created.content = "modified content"
        created.tags = ["modified"]
        tmp_db.update(created)

        current = tmp_db.get_by_id(created.id)
        assert current.title == "Modified"
        assert current.content == "modified content"
        assert current.tags == ["modified"]

        restored = tmp_db.restore_version(created.id, 1)
        assert restored is not None
        assert restored.title == "Original"
        assert restored.content == "original content"
        assert restored.tags == ["orig"]

        versions = tmp_db.get_versions(created.id)
        assert len(versions) == 3
        assert versions[0].version == 3

    def test_restore_version_nonexistent_returns_none(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)
        assert tmp_db.restore_version("nonexistent", 1) is None
        assert tmp_db.restore_version(created.id, 999) is None

    def test_delete_removes_all_versions(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)

        created.content = "update 1"
        tmp_db.update(created)

        created.content = "update 2"
        tmp_db.update(created)

        versions_before = tmp_db.count_versions(created.id)
        assert versions_before == 3

        tmp_db.delete(created.id)
        versions_after = tmp_db.count_versions(created.id)
        assert versions_after == 0

    def test_count_versions_empty_snippet(self, tmp_db):
        assert tmp_db.count_versions("nonexistent") == 0

    def test_get_versions_empty_snippet(self, tmp_db):
        assert tmp_db.get_versions("nonexistent") == []

    def test_versions_ordered_descending(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)

        for i in range(5):
            created.content = f"update {i + 1}"
            tmp_db.update(created)

        versions = tmp_db.get_versions(created.id)
        assert len(versions) == 6

        version_numbers = [v.version for v in versions]
        assert version_numbers == [6, 5, 4, 3, 2, 1]

    def test_version_preserves_all_fields(self, tmp_db):
        snippet = Snippet(
            title="Test Title",
            content="line1\nline2\nline3",
            language="python",
            description="Test description",
            tags=["tag1", "tag2", "tag3"],
        )
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.title == "Test Title"
        assert version.content == "line1\nline2\nline3"
        assert version.language == "python"
        assert version.description == "Test description"
        assert version.tags == ["tag1", "tag2", "tag3"]
        assert version.snippet_id == created.id

    def test_toggle_pin_does_not_create_version(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)
        versions_before = tmp_db.count_versions(created.id)

        tmp_db.toggle_pin(created.id)
        versions_after = tmp_db.count_versions(created.id)

        assert versions_after == versions_before

    def test_multiple_updates_create_multiple_versions(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)

        for i in range(10):
            created.content = f"content version {i + 2}"
            tmp_db.update(created)

        versions = tmp_db.get_versions(created.id)
        assert len(versions) == 11

        for i, version in enumerate(versions):
            expected_version = 11 - i
            assert version.version == expected_version

    def test_version_has_timestamp(self, tmp_db, sample_snippet):
        import time

        created = tmp_db.create(sample_snippet)
        v1 = tmp_db.get_version(created.id, 1)
        assert v1 is not None
        assert v1.created_at is not None

        time.sleep(0.001)
        created.content = "updated"
        tmp_db.update(created)

        v2 = tmp_db.get_version(created.id, 2)
        assert v2 is not None
        assert v2.created_at > v1.created_at

    def test_version_short_summary(self, tmp_db):
        snippet = Snippet(title="Test", content="first line\nsecond line")
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.short_summary == "first line"


class TestVersionTrackingEdgeCases:
    def test_update_without_changes_still_creates_version(self, tmp_db, sample_snippet):
        import time

        created = tmp_db.create(sample_snippet)
        versions_before = tmp_db.count_versions(created.id)

        time.sleep(0.001)
        tmp_db.update(created)

        versions_after = tmp_db.count_versions(created.id)
        assert versions_after == versions_before + 1

    def test_empty_content_versions(self, tmp_db):
        snippet = Snippet(title="Empty", content="")
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.content == ""

    def test_special_characters_in_version_content(self, tmp_db):
        special_content = 'line with "quotes" and \'single quotes\' and \nnewlines'
        snippet = Snippet(title="Special", content=special_content)
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.content == special_content

    def test_unicode_content_in_version(self, tmp_db):
        unicode_content = "中文内容\n日本語\n한국어\nemoji: 🎉🚀✨"
        snippet = Snippet(title="Unicode", content=unicode_content)
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.content == unicode_content

    def test_restore_to_latest_version_creates_new_version(self, tmp_db, sample_snippet):
        created = tmp_db.create(sample_snippet)

        created.content = "update 1"
        tmp_db.update(created)

        versions_before_restore = tmp_db.count_versions(created.id)
        assert versions_before_restore == 2

        tmp_db.restore_version(created.id, 2)

        versions_after_restore = tmp_db.count_versions(created.id)
        assert versions_after_restore == 3

    def test_empty_tags_in_version(self, tmp_db):
        snippet = Snippet(title="No Tags", content="content", tags=[])
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.tags == []

    def test_very_long_content_in_version(self, tmp_db):
        long_content = "x" * 10000
        snippet = Snippet(title="Long", content=long_content)
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.content == long_content

    def test_version_for_snippet_without_description(self, tmp_db):
        snippet = Snippet(title="No Desc", content="content", description="")
        created = tmp_db.create(snippet)

        version = tmp_db.get_version(created.id, 1)
        assert version is not None
        assert version.description == ""

    def test_multiple_snippets_versions_independent(self, tmp_db):
        snippet1 = Snippet(title="Snippet 1", content="content 1")
        snippet2 = Snippet(title="Snippet 2", content="content 2")

        created1 = tmp_db.create(snippet1)
        created2 = tmp_db.create(snippet2)

        created1.content = "update 1-1"
        tmp_db.update(created1)

        created1.content = "update 1-2"
        tmp_db.update(created1)

        created2.content = "update 2-1"
        tmp_db.update(created2)

        assert tmp_db.count_versions(created1.id) == 3
        assert tmp_db.count_versions(created2.id) == 2

        versions1 = tmp_db.get_versions(created1.id)
        versions2 = tmp_db.get_versions(created2.id)

        assert all(v.snippet_id == created1.id for v in versions1)
        assert all(v.snippet_id == created2.id for v in versions2)


class TestVersionLimit:
    def test_versions_limited_to_50(self, tmp_db):
        snippet = Snippet(title="Test Limit", content="v1")
        created = tmp_db.create(snippet)

        for i in range(60):
            created.content = f"update {i + 2}"
            tmp_db.update(created)

        count = tmp_db.count_versions(created.id)
        assert count == 50

        versions = tmp_db.get_versions(created.id)
        version_numbers = [v.version for v in versions]

        assert version_numbers[0] == 61
        assert version_numbers[-1] == 12

        assert tmp_db.get_version(created.id, 1) is None
        assert tmp_db.get_version(created.id, 11) is None
        assert tmp_db.get_version(created.id, 12) is not None

    def test_versions_under_limit_not_pruned(self, tmp_db):
        snippet = Snippet(title="Test Under Limit", content="v1")
        created = tmp_db.create(snippet)

        for i in range(30):
            created.content = f"update {i + 2}"
            tmp_db.update(created)

        count = tmp_db.count_versions(created.id)
        assert count == 31

        assert tmp_db.get_version(created.id, 1) is not None
        assert tmp_db.get_version(created.id, 31) is not None

    def test_multiple_snippets_prune_independently(self, tmp_db):
        snippet1 = Snippet(title="Snippet 1", content="v1")
        snippet2 = Snippet(title="Snippet 2", content="v1")

        created1 = tmp_db.create(snippet1)
        created2 = tmp_db.create(snippet2)

        for i in range(60):
            created1.content = f"update {i + 2}"
            tmp_db.update(created1)

        for i in range(10):
            created2.content = f"update {i + 2}"
            tmp_db.update(created2)

        assert tmp_db.count_versions(created1.id) == 50
        assert tmp_db.count_versions(created2.id) == 11

        assert tmp_db.get_version(created1.id, 1) is None
        assert tmp_db.get_version(created2.id, 1) is not None
