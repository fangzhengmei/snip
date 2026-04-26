from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from snip.models.snippet import Snippet
from snip.utils.export import (
    IMPORT_FORMATS,
    _parse_csv_value,
    _yaml_parse_quoted,
    _yaml_parse_simple_value,
    export_csv,
    export_json,
    export_markdown,
    export_yaml,
    import_csv,
    import_from_file,
    import_from_string,
    import_markdown,
    import_yaml,
)


class TestParseCsvValue:
    def test_returns_none_for_none(self):
        assert _parse_csv_value(None) is None

    def test_returns_true_for_true(self):
        assert _parse_csv_value("true") is True
        assert _parse_csv_value("TRUE") is True
        assert _parse_csv_value("True") is True

    def test_returns_false_for_false(self):
        assert _parse_csv_value("false") is False
        assert _parse_csv_value("FALSE") is False
        assert _parse_csv_value("False") is False

    def test_returns_string_for_other_values(self):
        assert _parse_csv_value("hello") == "hello"
        assert _parse_csv_value("  test  ") == "test"


class TestYamlParseQuoted:
    def test_unquotes_double_quoted_string(self):
        assert _yaml_parse_quoted('"hello"') == "hello"

    def test_handles_escaped_double_quotes(self):
        assert _yaml_parse_quoted('"test \\"quoted\\""') == 'test "quoted"'

    def test_handles_escaped_newlines(self):
        assert _yaml_parse_quoted('"line1\\nline2"') == "line1\nline2"

    def test_handles_escaped_tabs(self):
        assert _yaml_parse_quoted('"a\\tb"') == "a\tb"

    def test_returns_original_if_not_quoted(self):
        assert _yaml_parse_quoted("hello") == "hello"


class TestYamlParseSimpleValue:
    def test_returns_true_for_true(self):
        assert _yaml_parse_simple_value("true") is True
        assert _yaml_parse_simple_value("TRUE") is True

    def test_returns_false_for_false(self):
        assert _yaml_parse_simple_value("false") is False
        assert _yaml_parse_simple_value("FALSE") is False

    def test_returns_none_for_null(self):
        assert _yaml_parse_simple_value("null") is None
        assert _yaml_parse_simple_value("NULL") is None

    def test_returns_none_for_empty_string(self):
        assert _yaml_parse_simple_value("") is None

    def test_returns_quoted_value_parsed(self):
        assert _yaml_parse_simple_value('"hello"') == "hello"


class TestImportCsv:
    def test_parses_basic_csv(self):
        csv_content = """id,title,content,language,description,tags,pinned
,Test,print('hi'),python,A description,"a, b",true
,Test2,code,text,,,false"""
        result = import_csv(csv_content)
        assert len(result) == 2
        assert result[0]["title"] == "Test"
        assert result[0]["content"] == "print('hi')"
        assert result[0]["language"] == "python"
        assert result[0]["description"] == "A description"
        assert result[0]["tags"] == ["a", "b"]
        assert result[0]["pinned"] is True

        assert result[1]["title"] == "Test2"
        assert result[1]["content"] == "code"
        assert result[1]["tags"] == []
        assert result[1]["pinned"] is False

    def test_empty_tags_string(self):
        csv_content = """id,title,content,tags
,Test,code,"""
        result = import_csv(csv_content)
        assert result[0]["tags"] == []

    def test_round_trip_with_export(self):
        snippets = [
            Snippet(
                title="Round Trip",
                content="print('test')",
                language="python",
                description="A test",
                tags=["tag1", "tag2"],
                pinned=True,
            )
        ]
        csv_str = export_csv(snippets)
        parsed = import_csv(csv_str)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Round Trip"
        assert parsed[0]["content"] == "print('test')"
        assert parsed[0]["language"] == "python"
        assert parsed[0]["description"] == "A test"
        assert parsed[0]["tags"] == ["tag1", "tag2"]
        assert parsed[0]["pinned"] is True


class TestImportMarkdown:
    def test_parses_basic_markdown(self):
        md_content = """# Test Title

This is a description

**Tags:** tag1, tag2

```python
print('hello')
print('world')
```
"""
        result = import_markdown(md_content)
        assert len(result) == 1
        assert result[0]["title"] == "Test Title"
        assert result[0]["description"] == "This is a description"
        assert result[0]["tags"] == ["tag1", "tag2"]
        assert result[0]["language"] == "python"
        assert result[0]["content"] == "print('hello')\nprint('world')"

    def test_parses_multiple_snippets(self):
        md_content = """# First

```python
code1
```

---

# Second

Description

**Tags:** test

```javascript
code2
```
"""
        result = import_markdown(md_content)
        assert len(result) == 2
        assert result[0]["title"] == "First"
        assert result[0]["content"] == "code1"
        assert result[1]["title"] == "Second"
        assert result[1]["description"] == "Description"
        assert result[1]["tags"] == ["test"]
        assert result[1]["content"] == "code2"

    def test_optional_fields(self):
        md_content = """# Minimal

```text
simple
```
"""
        result = import_markdown(md_content)
        assert len(result) == 1
        assert result[0]["title"] == "Minimal"
        assert result[0]["content"] == "simple"
        assert "description" not in result[0]
        assert "tags" not in result[0]

    def test_no_language_specified(self):
        md_content = """# Test

```
code
```
"""
        result = import_markdown(md_content)
        assert result[0]["language"] == "text"

    def test_round_trip_with_export(self):
        snippets = [
            Snippet(
                title="MD Round Trip",
                content="line1\nline2",
                language="python",
                description="This is a test",
                tags=["md", "test"],
                pinned=False,
            )
        ]
        md_str = export_markdown(snippets)
        parsed = import_markdown(md_str)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "MD Round Trip"
        assert parsed[0]["content"] == "line1\nline2"
        assert parsed[0]["language"] == "python"
        assert parsed[0]["description"] == "This is a test"
        assert parsed[0]["tags"] == ["md", "test"]


class TestImportYaml:
    def test_parses_basic_yaml(self):
        yaml_content = """- id: abc123
  title: Test
  content: |
    print('hello')
    print('world')
  language: python
  description: A description
  tags:
    - tag1
    - tag2
  pinned: true
"""
        result = import_yaml(yaml_content)
        assert len(result) == 1
        assert result[0]["title"] == "Test"
        assert result[0]["content"] == "print('hello')\nprint('world')"
        assert result[0]["language"] == "python"
        assert result[0]["description"] == "A description"
        assert result[0]["tags"] == ["tag1", "tag2"]
        assert result[0]["pinned"] is True

    def test_parses_multiple_documents(self):
        yaml_content = """- id: 1
  title: First
  content: |
    code1
  language: python
---
- id: 2
  title: Second
  content: |
    code2
  language: javascript
  tags:
    - test
"""
        result = import_yaml(yaml_content)
        assert len(result) == 2
        assert result[0]["title"] == "First"
        assert result[0]["content"] == "code1"
        assert result[1]["title"] == "Second"
        assert result[1]["content"] == "code2"
        assert result[1]["tags"] == ["test"]

    def test_handles_quoted_strings(self):
        yaml_content = '''- id: 1
  title: "\"Quoted\" Title"
  content: |
    code
  language: text
'''
        result = import_yaml(yaml_content)
        assert result[0]["title"] == '"Quoted" Title'

    def test_handles_special_characters_in_title(self):
        yaml_content = '''- id: 1
  title: "[starts with bracket"
  content: |
    code
  language: text
'''
        result = import_yaml(yaml_content)
        assert result[0]["title"] == "[starts with bracket"

    def test_round_trip_with_export(self):
        snippets = [
            Snippet(
                title='YAML "Round" Trip',
                content="line1\nline2\nline3",
                language="python",
                description="This has special: chars # comment",
                tags=["yaml", "test", "with spaces"],
                pinned=True,
            )
        ]
        yaml_str = export_yaml(snippets)
        parsed = import_yaml(yaml_str)
        assert len(parsed) == 1
        assert parsed[0]["title"] == 'YAML "Round" Trip'
        assert parsed[0]["content"] == "line1\nline2\nline3"
        assert parsed[0]["language"] == "python"
        assert parsed[0]["description"] == "This has special: chars # comment"
        assert parsed[0]["tags"] == ["yaml", "test", "with spaces"]
        assert parsed[0]["pinned"] is True


class TestImportFromString:
    def test_imports_json(self):
        json_str = json.dumps([{"title": "Test", "content": "code"}])
        result = import_from_string(json_str, "json")
        assert len(result) == 1
        assert result[0]["title"] == "Test"
        assert result[0]["content"] == "code"

    def test_imports_csv(self):
        csv_str = "title,content\nTest,code"
        result = import_from_string(csv_str, "csv")
        assert len(result) == 1
        assert result[0]["title"] == "Test"
        assert result[0]["content"] == "code"

    def test_imports_yaml(self):
        yaml_str = '- title: Test\n  content: |\n    code\n  language: text'
        result = import_from_string(yaml_str, "yaml")
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_imports_markdown(self):
        md_str = "# Test\n\n```\ncode\n```"
        result = import_from_string(md_str, "markdown")
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_unsupported_format_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            import_from_string("data", "html")

    def test_invalid_json_raises_error(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            import_from_string("not json", "json")


class TestImportFromFile:
    def test_imports_from_json_file(self, tmp_path):
        file_path = tmp_path / "test.json"
        file_path.write_text(json.dumps([{"title": "Test", "content": "code"}]))
        result = import_from_file(file_path)
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_imports_from_csv_file(self, tmp_path):
        file_path = tmp_path / "test.csv"
        file_path.write_text("title,content\nTest,code")
        result = import_from_file(file_path)
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_imports_from_yaml_file(self, tmp_path):
        file_path = tmp_path / "test.yml"
        file_path.write_text('- title: Test\n  content: |\n    code\n  language: text')
        result = import_from_file(file_path)
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_imports_from_markdown_file(self, tmp_path):
        file_path = tmp_path / "test.md"
        file_path.write_text("# Test\n\n```\ncode\n```")
        result = import_from_file(file_path)
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_explicit_format_overrides_extension(self, tmp_path):
        file_path = tmp_path / "test.xyz"
        file_path.write_text(json.dumps([{"title": "Test", "content": "code"}]))
        result = import_from_file(file_path, fmt="json")
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_unknown_extension_raises_error(self, tmp_path):
        file_path = tmp_path / "test.xyz"
        file_path.write_text("data")
        with pytest.raises(ValueError, match="Unknown file extension"):
            import_from_file(file_path)

    def test_no_extension_no_format_raises_error(self, tmp_path):
        file_path = tmp_path / "test"
        file_path.write_text("data")
        with pytest.raises(ValueError, match="No file extension and no format specified"):
            import_from_file(file_path)

    def test_file_not_found_raises_error(self, tmp_path):
        file_path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError, match="File not found"):
            import_from_file(file_path)


class TestFullRoundTrip:
    def test_json_round_trip(self):
        snippets = [
            Snippet(title="JSON Test", content="code", language="python", tags=["json"]),
            Snippet(title="Second", content="more code", language="text"),
        ]
        exported = export_json(snippets)
        imported = import_from_string(exported, "json")
        assert len(imported) == 2
        assert imported[0]["title"] == "JSON Test"
        assert imported[0]["content"] == "code"
        assert imported[1]["title"] == "Second"

    def test_csv_round_trip(self):
        snippets = [
            Snippet(
                title="CSV Test",
                content="print('hello')",
                language="python",
                description="A test",
                tags=["a", "b"],
                pinned=True,
            )
        ]
        exported = export_csv(snippets)
        imported = import_csv(exported)
        assert len(imported) == 1
        assert imported[0]["title"] == "CSV Test"
        assert imported[0]["content"] == "print('hello')"
        assert imported[0]["language"] == "python"
        assert imported[0]["description"] == "A test"
        assert imported[0]["tags"] == ["a", "b"]
        assert imported[0]["pinned"] is True

    def test_markdown_round_trip(self):
        snippets = [
            Snippet(
                title="MD Test",
                content="line1\nline2",
                language="python",
                description="Description",
                tags=["md", "test"],
            )
        ]
        exported = export_markdown(snippets)
        imported = import_markdown(exported)
        assert len(imported) == 1
        assert imported[0]["title"] == "MD Test"
        assert imported[0]["content"] == "line1\nline2"
        assert imported[0]["language"] == "python"
        assert imported[0]["description"] == "Description"
        assert imported[0]["tags"] == ["md", "test"]

    def test_yaml_round_trip(self):
        snippets = [
            Snippet(
                title='YAML "Quote" Test',
                content="line1\nline2\nline3",
                language="python",
                description="Has: special # chars",
                tags=["yaml", "test tag"],
                pinned=True,
            )
        ]
        exported = export_yaml(snippets)
        imported = import_yaml(exported)
        assert len(imported) == 1
        assert imported[0]["title"] == 'YAML "Quote" Test'
        assert imported[0]["content"] == "line1\nline2\nline3"
        assert imported[0]["language"] == "python"
        assert imported[0]["description"] == "Has: special # chars"
        assert imported[0]["tags"] == ["yaml", "test tag"]
        assert imported[0]["pinned"] is True


class TestImportFormatsConstant:
    def test_contains_all_supported_formats(self):
        assert "json" in IMPORT_FORMATS
        assert "markdown" in IMPORT_FORMATS
        assert "md" in IMPORT_FORMATS
        assert "csv" in IMPORT_FORMATS
        assert "yaml" in IMPORT_FORMATS
        assert "yml" in IMPORT_FORMATS
