import json
from pathlib import Path

from snip.ui.screens.import_screen import ImportResult, parse_import_file


class TestImportResult:
    def test_success_with_data(self):
        data = [{"title": "test", "content": "test"}]
        result = ImportResult(success=True, data=data)
        assert result.success is True
        assert result.data == data
        assert result.error is None

    def test_failure_with_error(self):
        result = ImportResult(success=False, error="file not found")
        assert result.success is False
        assert result.data is None
        assert result.error == "file not found"

    def test_cancelled(self):
        result = ImportResult(success=False)
        assert result.success is False
        assert result.data is None
        assert result.error is None


class TestParseImportFile:
    def test_imports_valid_file(self, tmp_path):
        data = [
            {"title": "Test 1", "content": "content 1", "language": "python"},
            {"title": "Test 2", "content": "content 2"},
        ]
        json_file = tmp_path / "test_import.json"
        json_file.write_text(json.dumps(data))

        result = parse_import_file(str(json_file))

        assert result.success is True
        assert result.data == data
        assert result.error is None

    def test_file_not_found(self, tmp_path):
        result = parse_import_file(str(tmp_path / "nonexistent.json"))

        assert result.success is False
        assert result.data is None
        assert "file not found" in result.error

    def test_invalid_json(self, tmp_path):
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json {{{")

        result = parse_import_file(str(json_file))

        assert result.success is False
        assert result.data is None
        assert "JSON" in result.error or "json" in result.error

    def test_non_array_json(self, tmp_path):
        json_file = tmp_path / "non_array.json"
        json_file.write_text(json.dumps({"title": "single", "content": "test"}))

        result = parse_import_file(str(json_file))

        assert result.success is False
        assert result.data is None
        assert "array" in result.error

    def test_empty_array(self, tmp_path):
        json_file = tmp_path / "empty.json"
        json_file.write_text("[]")

        result = parse_import_file(str(json_file))

        assert result.success is True
        assert result.data == []
        assert result.error is None

    def test_path_with_tilde(self, tmp_path, monkeypatch):
        data = [{"title": "test", "content": "content"}]
        home_dir = tmp_path / "home" / "user"
        home_dir.mkdir(parents=True)
        json_file = home_dir / "backup.json"
        json_file.write_text(json.dumps(data))

        monkeypatch.setenv("HOME", str(home_dir))
        monkeypatch.setenv("USERPROFILE", str(home_dir))

        result = parse_import_file("~/backup.json")

        assert result.success is True
        assert result.data == data

    def test_absolute_path(self, tmp_path):
        data = [{"title": "test", "content": "content"}]
        json_file = tmp_path / "backup.json"
        json_file.write_text(json.dumps(data))

        result = parse_import_file(str(json_file.absolute()))

        assert result.success is True
        assert result.data == data
