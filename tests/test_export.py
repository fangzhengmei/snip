from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from snip.models.snippet import Snippet
from snip.utils.export import (
    EXPORT_FORMATS,
    export,
    export_csv,
    export_html,
    export_json,
    export_markdown,
    export_to_file,
    export_yaml,
)


class TestExportJson:
    def test_exports_snippets_as_json(self):
        snippets = [
            Snippet(title="Test", content="print('hello')", language="python", tags=["test"]),
        ]
        result = export_json(snippets)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["title"] == "Test"
        assert data[0]["content"] == "print('hello')"
        assert data[0]["language"] == "python"
        assert data[0]["tags"] == ["test"]

    def test_empty_list_returns_empty_array(self):
        result = export_json([])
        assert json.loads(result) == []

    def test_includes_all_fields(self):
        snippet = Snippet(
            title="Full",
            content="content",
            language="python",
            description="A description",
            tags=["a", "b"],
            pinned=True,
        )
        result = export_json([snippet])
        data = json.loads(result)[0]
        assert data["title"] == "Full"
        assert data["content"] == "content"
        assert data["language"] == "python"
        assert data["description"] == "A description"
        assert data["tags"] == ["a", "b"]
        assert data["pinned"] is True
        assert "created_at" in data
        assert "updated_at" in data


class TestExportMarkdown:
    def test_exports_snippets_as_markdown(self):
        snippets = [
            Snippet(title="Hello", content="print('hi')", language="python"),
        ]
        result = export_markdown(snippets)
        assert "# Hello" in result
        assert "```python" in result
        assert "print('hi')" in result
        assert "```" in result

    def test_includes_description(self):
        snippet = Snippet(
            title="Test",
            content="code",
            description="This is a test",
        )
        result = export_markdown([snippet])
        assert "This is a test" in result

    def test_includes_tags(self):
        snippet = Snippet(title="Test", content="code", tags=["python", "test"])
        result = export_markdown([snippet])
        assert "**Tags:** python, test" in result

    def test_multiple_snippets_separated(self):
        snippets = [
            Snippet(title="A", content="a"),
            Snippet(title="B", content="b"),
        ]
        result = export_markdown(snippets)
        assert "# A" in result
        assert "# B" in result
        assert "---" in result

    def test_empty_list_returns_empty_string(self):
        result = export_markdown([])
        assert result == ""


class TestExportCsv:
    def test_exports_snippets_as_csv(self):
        snippet = Snippet(
            title="Test",
            content="print('hello')",
            language="python",
            tags=["a", "b"],
            pinned=True,
        )
        result = export_csv([snippet])
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["title"] == "Test"
        assert rows[0]["content"] == "print('hello')"
        assert rows[0]["language"] == "python"
        assert rows[0]["tags"] == "a, b"
        assert rows[0]["pinned"] == "true"

    def test_csv_has_header(self):
        result = export_csv([])
        lines = result.strip().splitlines()
        assert len(lines) == 1
        header = lines[0]
        assert "title" in header
        assert "content" in header
        assert "language" in header


class TestExportYaml:
    def test_exports_snippets_as_yaml(self):
        snippet = Snippet(
            title="Test",
            content="line1\nline2",
            language="python",
            tags=["a", "b"],
        )
        result = export_yaml([snippet])
        assert "title: Test" in result
        assert "language: python" in result
        assert "tags:" in result
        assert "line1" in result
        assert "line2" in result

    def test_pinned_included(self):
        snippet = Snippet(title="Test", content="c", pinned=True)
        result = export_yaml([snippet])
        assert "pinned: true" in result

    def test_multiple_snippets(self):
        snippets = [
            Snippet(title="A", content="a"),
            Snippet(title="B", content="b"),
        ]
        result = export_yaml(snippets)
        assert "title: A" in result
        assert "title: B" in result
        assert "---" in result

    def test_empty_list_returns_empty_string(self):
        result = export_yaml([])
        assert result == ""


class TestExportHtml:
    def test_exports_valid_html(self):
        snippet = Snippet(
            title="Test",
            content="print('hello')",
            language="python",
            tags=["test"],
            pinned=True,
        )
        result = export_html([snippet])
        assert "<!DOCTYPE html>" in result
        assert "<html>" in result
        assert "<title>Snippets</title>" in result
        assert "Test" in result
        assert "print(&#039;hello&#039;)" in result
        assert "python" in result
        assert "test" in result
        assert "Pinned" in result

    def test_includes_description(self):
        snippet = Snippet(
            title="Test",
            content="code",
            description="A description",
        )
        result = export_html([snippet])
        assert "A description" in result

    def test_html_escapes_content(self):
        snippet = Snippet(title="Test", content="<script>alert('xss')</script>")
        result = export_html([snippet])
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_empty_list_returns_valid_html(self):
        result = export_html([])
        assert "<!DOCTYPE html>" in result
        assert "<html>" in result
        assert "<body>" in result
        assert "</html>" in result
        assert '<div class="snippet">' not in result


class TestExportFunction:
    def test_default_format_is_json(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["title"] == "Test"

    def test_supports_json_format(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "json")
        data = json.loads(result)
        assert data[0]["title"] == "Test"

    def test_supports_markdown_format(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "markdown")
        assert "# Test" in result

    def test_supports_md_alias(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "md")
        assert "# Test" in result

    def test_supports_csv_format(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "csv")
        assert "title" in result

    def test_supports_yaml_format(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "yaml")
        assert "title: Test" in result

    def test_supports_yml_alias(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "yml")
        assert "title: Test" in result

    def test_supports_html_format(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "html")
        assert "<!DOCTYPE html>" in result

    def test_unsupported_format_raises_error(self):
        snippets = [Snippet(title="Test", content="c")]
        with pytest.raises(ValueError, match="Unsupported format"):
            export(snippets, "invalid")

    def test_unsupported_format_error_includes_supported_formats(self):
        snippets = [Snippet(title="Test", content="c")]
        with pytest.raises(ValueError) as exc_info:
            export(snippets, "invalid")
        error_msg = str(exc_info.value)
        assert "json" in error_msg
        assert "markdown" in error_msg
        assert "csv" in error_msg
        assert "yaml" in error_msg
        assert "html" in error_msg

    def test_export_to_file_with_unsupported_format_raises_error(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        file_path = tmp_path / "output.txt"
        with pytest.raises(ValueError, match="Unsupported format"):
            export_to_file(snippets, file_path, fmt="invalid")

    def test_case_insensitive_format(self):
        snippets = [Snippet(title="Test", content="c")]
        result = export(snippets, "JSON")
        data = json.loads(result)
        assert data[0]["title"] == "Test"

    def test_export_formats_constant(self):
        assert "json" in EXPORT_FORMATS
        assert "markdown" in EXPORT_FORMATS
        assert "csv" in EXPORT_FORMATS
        assert "yaml" in EXPORT_FORMATS
        assert "html" in EXPORT_FORMATS


class TestExportToFile:
    def test_exports_to_file(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        file_path = tmp_path / "output.json"
        export_to_file(snippets, file_path)
        content = file_path.read_text()
        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["title"] == "Test"

    def test_infers_format_from_extension(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        file_path = tmp_path / "output.md"
        export_to_file(snippets, file_path)
        content = file_path.read_text()
        assert "# Test" in content

    def test_infers_format_from_extension_csv(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        file_path = tmp_path / "output.csv"
        export_to_file(snippets, file_path)
        content = file_path.read_text()
        assert "title" in content

    def test_uses_explicit_format_over_extension(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        file_path = tmp_path / "output.json"
        export_to_file(snippets, file_path, fmt="markdown")
        content = file_path.read_text()
        assert "# Test" in content

    def test_defaults_to_json_for_unknown_extension(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        file_path = tmp_path / "output.xyz"
        export_to_file(snippets, file_path)
        content = file_path.read_text()
        data = json.loads(content)
        assert data[0]["title"] == "Test"

    def test_accepts_path_object(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        path_obj = tmp_path / "output.json"
        export_to_file(snippets, path_obj)
        assert path_obj.exists()

    def test_accepts_string_path(self, tmp_path):
        snippets = [Snippet(title="Test", content="c")]
        path_str = str(tmp_path / "output.json")
        export_to_file(snippets, path_str)
        assert Path(path_str).exists()


class TestSpecialCharacterEscaping:
    def test_json_escapes_double_quotes(self):
        snippet = Snippet(title='Test "quoted"', content='print("hello")')
        result = export_json([snippet])
        data = json.loads(result)
        assert data[0]["title"] == 'Test "quoted"'
        assert data[0]["content"] == 'print("hello")'

    def test_json_escapes_backslashes(self):
        snippet = Snippet(title="Test", content="C:\\Users\\test")
        result = export_json([snippet])
        data = json.loads(result)
        assert data[0]["content"] == "C:\\Users\\test"

    def test_json_escapes_newlines(self):
        snippet = Snippet(title="Test", content="line1\nline2\nline3")
        result = export_json([snippet])
        data = json.loads(result)
        assert data[0]["content"] == "line1\nline2\nline3"

    def test_json_escapes_special_unicode(self):
        snippet = Snippet(title="测试", content="emoji 🚀")
        result = export_json([snippet])
        data = json.loads(result)
        assert data[0]["title"] == "测试"
        assert data[0]["content"] == "emoji 🚀"

    def test_csv_escapes_commas(self):
        snippet = Snippet(title="Test, with, commas", content="a, b, c")
        result = export_csv([snippet])
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert rows[0]["title"] == "Test, with, commas"
        assert rows[0]["content"] == "a, b, c"

    def test_csv_escapes_double_quotes(self):
        snippet = Snippet(title='Test "quoted"', content='print("hi")')
        result = export_csv([snippet])
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert rows[0]["title"] == 'Test "quoted"'
        assert rows[0]["content"] == 'print("hi")'

    def test_csv_escapes_newlines(self):
        snippet = Snippet(title="Multiline\nTitle", content="line1\nline2")
        result = export_csv([snippet])
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert rows[0]["title"] == "Multiline\nTitle"
        assert rows[0]["content"] == "line1\nline2"

    def test_html_escapes_ampersand(self):
        snippet = Snippet(title="Test & more", content="if (a && b)")
        result = export_html([snippet])
        assert "Test &amp; more" in result
        assert "a &amp;&amp; b" in result

    def test_html_escapes_double_quotes(self):
        snippet = Snippet(title='Test "quote"', content='print("hi")')
        result = export_html([snippet])
        assert "Test &quot;quote&quot;" in result
        assert "print(&quot;hi&quot;)" in result

    def test_html_escapes_single_quotes(self):
        snippet = Snippet(title="Test 'quote'", content="print('hi')")
        result = export_html([snippet])
        assert "Test &#039;quote&#039;" in result
        assert "print(&#039;hi&#039;)" in result

    def test_html_escapes_greater_than(self):
        snippet = Snippet(title="Test >", content="if (x > y)")
        result = export_html([snippet])
        assert "Test &gt;" in result
        assert "x &gt; y" in result

    def test_html_escapes_less_than(self):
        snippet = Snippet(title="Test <", content="if (x < y)")
        result = export_html([snippet])
        assert "Test &lt;" in result
        assert "x &lt; y" in result

    def test_yaml_escapes_title_starting_with_dash(self):
        snippet = Snippet(title="- starts with dash", content="code")
        result = export_yaml([snippet])
        assert '"- starts with dash"' in result

    def test_yaml_escapes_title_starting_with_space(self):
        snippet = Snippet(title="  leading spaces", content="code")
        result = export_yaml([snippet])
        assert '"  leading spaces"' in result

    def test_yaml_escapes_title_with_double_quotes(self):
        snippet = Snippet(title='Test "quoted"', content="code")
        result = export_yaml([snippet])
        assert '"Test \\"quoted\\""' in result

    def test_yaml_escapes_title_with_newline(self):
        snippet = Snippet(title="Multiline\nTitle", content="code")
        result = export_yaml([snippet])
        assert '"Multiline\\nTitle"' in result

    def test_yaml_escapes_title_starting_with_special_chars(self):
        special_chars = ["[", "{", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`"]
        for char in special_chars:
            title = char + " test"
            snippet = Snippet(title=title, content="code")
            result = export_yaml([snippet])
            if char == '"':
                assert 'title: "\\" test"' in result
            else:
                assert f'title: "{char} test"' in result

    def test_markdown_preserves_content_with_backticks(self):
        snippet = Snippet(title="Test", content="code with `backticks`")
        result = export_markdown([snippet])
        assert "code with `backticks`" in result

    def test_markdown_preserves_content_with_hashes(self):
        snippet = Snippet(title="Test", content="# Not a header\n## Also not")
        result = export_markdown([snippet])
        assert "# Not a header" in result
        assert "## Also not" in result
