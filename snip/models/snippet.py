from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

SUPPORTED_LANGUAGES = [
    "text", "python", "javascript", "typescript", "bash", "go", "rust",
    "c", "cpp", "java", "json", "yaml", "toml", "sql", "html", "css",
    "markdown", "dockerfile", "powershell", "ruby", "php", "swift", "kotlin",
]


@dataclass
class SnippetVersion:
    snippet_id: str
    title: str
    content: str
    language: str
    description: str
    tags: list[str]
    version: int
    id: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def short_summary(self) -> str:
        first_line = self.content.strip().splitlines()[0] if self.content.strip() else ""
        return first_line[:50] + ("…" if len(first_line) > 50 else "")

    def to_snapshot_json(self) -> str:
        return json.dumps({
            "title": self.title,
            "content": self.content,
            "language": self.language,
            "description": self.description,
            "tags": self.tags,
        }, ensure_ascii=False)

    @classmethod
    def from_snapshot_json(cls, snippet_id: str, version: int, snapshot_json: str, created_at: datetime | None = None) -> "SnippetVersion":
        data = json.loads(snapshot_json)
        return cls(
            snippet_id=snippet_id,
            title=data["title"],
            content=data["content"],
            language=data["language"],
            description=data["description"],
            tags=data["tags"],
            version=version,
            created_at=created_at,
        )

    def to_snippet(self, existing_snippet: Snippet | None = None) -> Snippet:
        if existing_snippet:
            existing_snippet.title = self.title
            existing_snippet.content = self.content
            existing_snippet.language = self.language
            existing_snippet.description = self.description
            existing_snippet.tags = self.tags
            return existing_snippet
        return Snippet(
            title=self.title,
            content=self.content,
            language=self.language,
            description=self.description,
            tags=self.tags,
        )


@dataclass
class Snippet:
    title: str
    content: str
    language: str = "text"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    pinned: bool = False
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
        if self.language not in SUPPORTED_LANGUAGES:
            self.language = "text"

    @property
    def tags_display(self) -> str:
        return " ".join(f"#{t}" for t in self.tags) if self.tags else ""

    @property
    def short_description(self) -> str:
        if self.description:
            return self.description[:60] + ("…" if len(self.description) > 60 else "")
        first_line = self.content.strip().splitlines()[0] if self.content.strip() else ""
        return first_line[:60] + ("…" if len(first_line) > 60 else "")

    def matches(self, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        return (
            q in self.title.lower()
            or q in self.description.lower()
            or q in self.content.lower()
            or any(q in tag.lower() for tag in self.tags)
            or q in self.language.lower()
        )
