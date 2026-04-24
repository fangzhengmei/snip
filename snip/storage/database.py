from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path

from snip.models.snippet import Snippet, SnippetVersion

_SEP = "\n---\n"
_MAX_VERSIONS = 50


def _now() -> datetime:
    return datetime.now()


def _parse_file(text: str) -> Snippet:
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter")
    rest = text[4:]
    sep = rest.index(_SEP)
    front = rest[:sep]
    content = rest[sep + len(_SEP):]

    meta: dict[str, str] = {}
    for line in front.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            meta[k] = v
        elif line.endswith(":"):
            meta[line[:-1]] = ""

    tags_raw = meta.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

    return Snippet(
        id=meta["id"],
        title=meta["title"],
        content=content,
        language=meta.get("language", "text"),
        description=meta.get("description", ""),
        tags=tags,
        pinned=meta.get("pinned", "false") == "true",
        created_at=datetime.fromisoformat(meta["created_at"]),
        updated_at=datetime.fromisoformat(meta["updated_at"]),
    )


def _to_file_text(snippet: Snippet) -> str:
    lines = [
        "---",
        f"id: {snippet.id}",
        f"title: {snippet.title}",
        f"language: {snippet.language}",
        f"description: {snippet.description}",
        f"tags: {', '.join(snippet.tags)}",
        f"pinned: {str(snippet.pinned).lower()}",
        f"created_at: {snippet.created_at.isoformat()}",
        f"updated_at: {snippet.updated_at.isoformat()}",
        "---",
        snippet.content,
    ]
    return "\n".join(lines)


def _row_to_snippet(row: sqlite3.Row) -> Snippet:
    tags_raw = row["tags"]
    tags = json.loads(tags_raw) if tags_raw else []
    return Snippet(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        language=row["language"],
        description=row["description"],
        tags=tags,
        pinned=bool(row["pinned"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_snippet_legacy(row: sqlite3.Row) -> Snippet:
    tags_raw = row["tags"]
    try:
        tags = json.loads(tags_raw) if tags_raw else []
    except Exception:
        tags = []
    return Snippet(
        title=row["title"],
        content=row["content"],
        language=row["language"],
        description=row["description"],
        tags=tags,
        pinned=bool(row["pinned"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_version(row: sqlite3.Row) -> SnippetVersion:
    return SnippetVersion.from_snapshot_json(
        snippet_id=row["snippet_id"],
        version=row["version"],
        snapshot_json=row["snapshot"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class Database:
    def __init__(self, snippets_dir: Path) -> None:
        self._dir = snippets_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = snippets_dir.parent / "snip.db"
        self._ensure_gitignore()
        self._migrate_legacy()
        self._init_index()
        self._sync()

    def _ensure_gitignore(self) -> None:
        gi = self._dir.parent / ".gitignore"
        if not gi.exists():
            gi.write_text("snip.db\n", encoding="utf-8")
        elif "snip.db" not in gi.read_text(encoding="utf-8"):
            with gi.open("a", encoding="utf-8") as f:
                f.write("snip.db\n")

    def _migrate_legacy(self) -> None:
        if not self._db_path.exists():
            return
        if any(self._dir.glob("*.md")):
            return
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            pragma = {row["name"]: row["type"] for row in conn.execute("PRAGMA table_info(snippets)").fetchall()}
            if pragma.get("id") != "INTEGER":
                conn.close()
                return
            rows = conn.execute("SELECT * FROM snippets ORDER BY id").fetchall()
            conn.close()
        except Exception:
            return
        for row in rows:
            try:
                snippet = _row_to_snippet_legacy(row)
                snippet.id = uuid.uuid4().hex[:12]
                self._write_file(snippet)
            except Exception:
                continue
        self._db_path.unlink()

    def _init_index(self) -> None:
        with closing(self._connect()) as conn:
            pragma = {
                row["name"]: row["type"]
                for row in conn.execute("PRAGMA table_info(snippets)").fetchall()
            }
            if pragma.get("id") == "INTEGER":
                conn.execute("DROP TABLE snippets")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snippets (
                    id          TEXT PRIMARY KEY,
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snippet_versions (
                    id          TEXT PRIMARY KEY,
                    snippet_id  TEXT NOT NULL,
                    version     INTEGER NOT NULL,
                    snapshot    TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    UNIQUE(snippet_id, version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snippet_versions_snippet_id
                ON snippet_versions(snippet_id)
            """)
            conn.commit()

    def _sync(self) -> None:
        file_snippets = {s.id: s for s in self._read_all_files()}
        with closing(self._connect()) as conn:
            db_state = {
                row["id"]: row["updated_at"]
                for row in conn.execute("SELECT id, updated_at FROM snippets").fetchall()
            }
            for sid, snippet in file_snippets.items():
                if sid not in db_state or db_state[sid] != snippet.updated_at.isoformat():
                    self._upsert_index(conn, snippet)
            for sid in db_state:
                if sid not in file_snippets:
                    conn.execute("DELETE FROM snippets WHERE id = ?", (sid,))
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _read_all_files(self) -> list[Snippet]:
        snippets = []
        for path in sorted(self._dir.glob("*.md")):
            try:
                snippets.append(_parse_file(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return snippets

    def _write_file(self, snippet: Snippet) -> None:
        path = self._dir / f"{snippet.id}.md"
        path.write_text(_to_file_text(snippet), encoding="utf-8")

    def _delete_file(self, snippet_id: str) -> bool:
        path = self._dir / f"{snippet_id}.md"
        if not path.exists():
            return False
        path.unlink()
        return True

    def _upsert_index(self, conn: sqlite3.Connection, snippet: Snippet) -> None:
        conn.execute(
            """
            INSERT OR REPLACE INTO snippets
                (id, title, content, language, description, tags, pinned, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snippet.id,
                snippet.title,
                snippet.content,
                snippet.language,
                snippet.description,
                json.dumps(snippet.tags),
                int(snippet.pinned),
                snippet.created_at.isoformat(),
                snippet.updated_at.isoformat(),
            ),
        )

    def _get_next_version(self, conn: sqlite3.Connection, snippet_id: str) -> int:
        row = conn.execute(
            "SELECT MAX(version) as max_ver FROM snippet_versions WHERE snippet_id = ?",
            (snippet_id,)
        ).fetchone()
        return (row["max_ver"] or 0) + 1

    def _prune_old_versions(self, conn: sqlite3.Connection, snippet_id: str) -> None:
        count_row = conn.execute(
            "SELECT COUNT(*) as n FROM snippet_versions WHERE snippet_id = ?",
            (snippet_id,)
        ).fetchone()
        count = count_row["n"]
        if count > _MAX_VERSIONS:
            excess = count - _MAX_VERSIONS
            conn.execute(
                """
                DELETE FROM snippet_versions
                WHERE snippet_id = ? AND version IN (
                    SELECT version FROM snippet_versions
                    WHERE snippet_id = ?
                    ORDER BY version ASC
                    LIMIT ?
                )
                """,
                (snippet_id, snippet_id, excess),
            )

    def _create_version(self, conn: sqlite3.Connection, snippet: Snippet, version: int | None = None) -> SnippetVersion:
        if version is None:
            version = self._get_next_version(conn, snippet.id)
        version_record = SnippetVersion(
            id=uuid.uuid4().hex[:12],
            snippet_id=snippet.id,
            title=snippet.title,
            content=snippet.content,
            language=snippet.language,
            description=snippet.description,
            tags=list(snippet.tags),
            version=version,
            created_at=_now(),
        )
        conn.execute(
            """
            INSERT INTO snippet_versions (id, snippet_id, version, snapshot, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                version_record.id,
                version_record.snippet_id,
                version_record.version,
                version_record.to_snapshot_json(),
                version_record.created_at.isoformat(),
            ),
        )
        self._prune_old_versions(conn, snippet.id)
        return version_record

    def create(self, snippet: Snippet) -> Snippet:
        now = _now()
        snippet.id = uuid.uuid4().hex[:12]
        snippet.created_at = now
        snippet.updated_at = now
        self._write_file(snippet)
        with closing(self._connect()) as conn:
            self._upsert_index(conn, snippet)
            self._create_version(conn, snippet, version=1)
            conn.commit()
        return snippet

    def get_all(self) -> list[Snippet]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM snippets ORDER BY pinned DESC, updated_at DESC"
            ).fetchall()
        return [_row_to_snippet(row) for row in rows]

    def get_by_id(self, snippet_id: str) -> Snippet | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM snippets WHERE id = ?", (snippet_id,)
            ).fetchone()
        return _row_to_snippet(row) if row else None

    def update(self, snippet: Snippet, create_version: bool = True) -> Snippet:
        snippet.updated_at = _now()
        self._write_file(snippet)
        with closing(self._connect()) as conn:
            self._upsert_index(conn, snippet)
            if create_version:
                self._create_version(conn, snippet)
            conn.commit()
        return snippet

    def delete(self, snippet_id: str) -> bool:
        deleted = self._delete_file(snippet_id)
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
            conn.execute("DELETE FROM snippet_versions WHERE snippet_id = ?", (snippet_id,))
            conn.commit()
        return deleted

    def search(self, query: str) -> list[Snippet]:
        return [s for s in self.get_all() if s.matches(query)]

    def toggle_pin(self, snippet_id: str) -> bool:
        snippet = self.get_by_id(snippet_id)
        if snippet is None:
            return False
        snippet.pinned = not snippet.pinned
        self.update(snippet, create_version=False)
        return snippet.pinned

    def count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) as n FROM snippets").fetchone()["n"]

    def get_versions(self, snippet_id: str) -> list[SnippetVersion]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM snippet_versions
                WHERE snippet_id = ?
                ORDER BY version DESC
                """,
                (snippet_id,)
            ).fetchall()
        return [_row_to_version(row) for row in rows]

    def get_version(self, snippet_id: str, version: int) -> SnippetVersion | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT * FROM snippet_versions
                WHERE snippet_id = ? AND version = ?
                """,
                (snippet_id, version)
            ).fetchone()
        return _row_to_version(row) if row else None

    def restore_version(self, snippet_id: str, version: int) -> Snippet | None:
        snippet = self.get_by_id(snippet_id)
        if snippet is None:
            return None
        version_record = self.get_version(snippet_id, version)
        if version_record is None:
            return None
        restored = version_record.to_snippet(existing_snippet=snippet)
        return self.update(restored, create_version=True)

    def count_versions(self, snippet_id: str) -> int:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as n FROM snippet_versions WHERE snippet_id = ?",
                (snippet_id,)
            ).fetchone()
            return row["n"]
