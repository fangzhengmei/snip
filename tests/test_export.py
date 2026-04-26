import json
from unittest.mock import patch

import pytest

from snip.models.snippet import Snippet
from snip.storage.database import Database


def perform_export(db: Database) -> tuple[str, int, bool]:
    """Perform export and return (json_str, count, clipboard_success).

    This is a standalone function that replicates the export logic from
    MainScreen.action_export_snippets, so it can be tested without Textual.
    """
    data = db.export_to_json_list()
    json_str = json.dumps(data, indent=2)

    from snip.utils.clipboard import copy_to_clipboard
    clipboard_success = copy_to_clipboard(json_str)

    return json_str, len(data), clipboard_success


class TestPerformExport:
    def test_empty_db_exports_empty_array(self, tmp_db):
        with patch("snip.utils.clipboard.copy_to_clipboard", return_value=True) as mock_copy:
            json_str, count, success = perform_export(tmp_db)

        assert count == 0
        assert success is True
        assert json.loads(json_str) == []
        mock_copy.assert_called_once()

    def test_exports_single_snippet(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)

        with patch("snip.utils.clipboard.copy_to_clipboard", return_value=True) as mock_copy:
            json_str, count, success = perform_export(tmp_db)

        assert count == 1
        assert success is True
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["title"] == sample_snippet.title
        assert data[0]["content"] == sample_snippet.content
        mock_copy.assert_called_once()

    def test_exports_multiple_snippets(self, tmp_db):
        s1 = Snippet(title="A", content="a", language="python", tags=["tag1"], pinned=True)
        s2 = Snippet(title="B", content="b", description="desc", tags=["tag2", "tag3"])
        tmp_db.create(s1)
        tmp_db.create(s2)

        with patch("snip.utils.clipboard.copy_to_clipboard", return_value=True):
            json_str, count, _ = perform_export(tmp_db)

        assert count == 2
        data = json.loads(json_str)
        assert len(data) == 2
        titles = {d["title"] for d in data}
        assert titles == {"A", "B"}

    def test_clipboard_unavailable_returns_false(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)

        with patch("snip.utils.clipboard.copy_to_clipboard", return_value=False) as mock_copy:
            json_str, count, success = perform_export(tmp_db)

        assert count == 1
        assert success is False
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["title"] == sample_snippet.title
        mock_copy.assert_called_once()

    def test_empty_db_with_clipboard_unavailable(self, tmp_db):
        with patch("snip.utils.clipboard.copy_to_clipboard", return_value=False):
            json_str, count, success = perform_export(tmp_db)

        assert count == 0
        assert success is False
        assert json.loads(json_str) == []

    def test_exported_json_is_valid(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)

        with patch("snip.utils.clipboard.copy_to_clipboard", return_value=True):
            json_str, _, _ = perform_export(tmp_db)

        data = json.loads(json_str)
        assert isinstance(data, list)
        assert len(data) == 1
        snippet = data[0]
        assert "title" in snippet
        assert "content" in snippet
        assert "language" in snippet
        assert "description" in snippet
        assert "tags" in snippet
        assert "pinned" in snippet

    def test_exported_json_has_indentation(self, tmp_db, sample_snippet):
        tmp_db.create(sample_snippet)

        with patch("snip.utils.clipboard.copy_to_clipboard", return_value=True):
            json_str, _, _ = perform_export(tmp_db)

        assert "\n" in json_str
        assert "  " in json_str
