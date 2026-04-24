from datetime import datetime

from snip.models.snippet import SUPPORTED_LANGUAGES, Snippet, SnippetVersion


class TestSnippetDefaults:
    def test_timestamps_set_on_creation(self):
        s = Snippet(title="t", content="c")
        assert isinstance(s.created_at, datetime)
        assert isinstance(s.updated_at, datetime)

    def test_unknown_language_falls_back_to_text(self):
        s = Snippet(title="t", content="c", language="brainfuck")
        assert s.language == "text"

    def test_supported_language_preserved(self):
        s = Snippet(title="t", content="c", language="python")
        assert s.language == "python"

    def test_all_supported_languages_accepted(self):
        for lang in SUPPORTED_LANGUAGES:
            s = Snippet(title="t", content="c", language=lang)
            assert s.language == lang


class TestTagsDisplay:
    def test_no_tags_returns_empty(self):
        s = Snippet(title="t", content="c")
        assert s.tags_display == ""

    def test_tags_formatted_with_hash(self):
        s = Snippet(title="t", content="c", tags=["python", "cli"])
        assert s.tags_display == "#python #cli"


class TestShortDescription:
    def test_uses_description_when_set(self):
        s = Snippet(title="t", content="long content", description="Short desc")
        assert s.short_description == "Short desc"

    def test_falls_back_to_first_line_of_content(self):
        s = Snippet(title="t", content="first line\nsecond line")
        assert s.short_description == "first line"

    def test_truncates_long_description(self):
        s = Snippet(title="t", content="c", description="x" * 80)
        assert s.short_description.endswith("…")
        assert len(s.short_description) <= 61  # 60 chars + ellipsis


class TestMatches:
    def test_matches_title(self):
        s = Snippet(title="Hello World", content="c")
        assert s.matches("hello")

    def test_matches_content(self):
        s = Snippet(title="t", content="import sys")
        assert s.matches("import")

    def test_matches_tags(self):
        s = Snippet(title="t", content="c", tags=["networking"])
        assert s.matches("network")

    def test_matches_language(self):
        s = Snippet(title="t", content="c", language="python")
        assert s.matches("python")

    def test_no_match(self):
        s = Snippet(title="Hello", content="World", tags=["foo"])
        assert not s.matches("zzz_nomatch_zzz")

    def test_empty_query_always_matches(self):
        s = Snippet(title="t", content="c")
        assert s.matches("")

    def test_case_insensitive(self):
        s = Snippet(title="Hello World", content="c")
        assert s.matches("HELLO")


class TestSnippetVersion:
    def test_timestamp_set_on_creation(self):
        v = SnippetVersion(
            snippet_id="test123",
            title="Test",
            content="content",
            language="python",
            description="desc",
            tags=["tag1"],
            version=1,
        )
        assert isinstance(v.created_at, datetime)

    def test_snapshot_json_round_trip(self):
        original = SnippetVersion(
            snippet_id="abc123",
            title="My Snippet",
            content="print('hello')\nprint('world')",
            language="python",
            description="A test snippet",
            tags=["python", "test"],
            version=2,
            id="ver001",
        )
        snapshot_json = original.to_snapshot_json()
        restored = SnippetVersion.from_snapshot_json(
            snippet_id="abc123",
            version=2,
            snapshot_json=snapshot_json,
            created_at=original.created_at,
        )
        assert restored.title == original.title
        assert restored.content == original.content
        assert restored.language == original.language
        assert restored.description == original.description
        assert restored.tags == original.tags
        assert restored.version == original.version
        assert restored.snippet_id == original.snippet_id
        assert restored.created_at == original.created_at

    def test_short_summary_uses_first_line(self):
        v = SnippetVersion(
            snippet_id="test",
            title="Test",
            content="first line\nsecond line\nthird line",
            language="text",
            description="",
            tags=[],
            version=1,
        )
        assert v.short_summary == "first line"

    def test_short_summary_truncates_long_line(self):
        long_content = "x" * 100
        v = SnippetVersion(
            snippet_id="test",
            title="Test",
            content=long_content,
            language="text",
            description="",
            tags=[],
            version=1,
        )
        assert v.short_summary.endswith("…")
        assert len(v.short_summary) == 51

    def test_short_summary_empty_content(self):
        v = SnippetVersion(
            snippet_id="test",
            title="Test",
            content="   \n\t\n",
            language="text",
            description="",
            tags=[],
            version=1,
        )
        assert v.short_summary == ""

    def test_to_snippet_creates_new_snippet(self):
        v = SnippetVersion(
            snippet_id="old123",
            title="Versioned Title",
            content="versioned content",
            language="javascript",
            description="versioned desc",
            tags=["js", "old"],
            version=3,
        )
        snippet = v.to_snippet()
        assert snippet.title == "Versioned Title"
        assert snippet.content == "versioned content"
        assert snippet.language == "javascript"
        assert snippet.description == "versioned desc"
        assert snippet.tags == ["js", "old"]

    def test_to_snippet_modifies_existing(self):
        existing = Snippet(
            title="Original Title",
            content="original content",
            language="python",
            description="original desc",
            tags=["python", "new"],
        )
        original_created_at = existing.created_at
        original_updated_at = existing.updated_at

        v = SnippetVersion(
            snippet_id="abc123",
            title="Updated Title",
            content="updated content",
            language="javascript",
            description="updated desc",
            tags=["js", "updated"],
            version=2,
        )
        result = v.to_snippet(existing_snippet=existing)

        assert result is existing
        assert result.title == "Updated Title"
        assert result.content == "updated content"
        assert result.language == "javascript"
        assert result.description == "updated desc"
        assert result.tags == ["js", "updated"]
        assert result.created_at == original_created_at
        assert result.updated_at == original_updated_at
