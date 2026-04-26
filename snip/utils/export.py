from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Callable, Sequence

from snip.models.snippet import Snippet

EXPORT_FORMATS = ["json", "markdown", "csv", "yaml", "html"]


def _snippet_to_dict(snippet: Snippet) -> dict[str, Any]:
    return {
        "id": snippet.id,
        "title": snippet.title,
        "content": snippet.content,
        "language": snippet.language,
        "description": snippet.description,
        "tags": snippet.tags,
        "pinned": snippet.pinned,
        "created_at": snippet.created_at.isoformat() if snippet.created_at else None,
        "updated_at": snippet.updated_at.isoformat() if snippet.updated_at else None,
    }


def export_json(snippets: Sequence[Snippet]) -> str:
    data = [_snippet_to_dict(s) for s in snippets]
    return json.dumps(data, indent=2, ensure_ascii=False)


def export_markdown(snippets: Sequence[Snippet]) -> str:
    lines: list[str] = []
    for snippet in snippets:
        lines.append(f"# {snippet.title}")
        lines.append("")
        if snippet.description:
            lines.append(snippet.description)
            lines.append("")
        if snippet.tags:
            lines.append(f"**Tags:** {', '.join(snippet.tags)}")
            lines.append("")
        lines.append(f"```{snippet.language}")
        lines.append(snippet.content)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def export_csv(snippets: Sequence[Snippet]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "id", "title", "content", "language", "description", "tags", "pinned",
        "created_at", "updated_at"
    ])
    for snippet in snippets:
        tags_str = ", ".join(snippet.tags) if snippet.tags else ""
        writer.writerow([
            snippet.id or "",
            snippet.title,
            snippet.content,
            snippet.language,
            snippet.description,
            tags_str,
            str(snippet.pinned).lower(),
            snippet.created_at.isoformat() if snippet.created_at else "",
            snippet.updated_at.isoformat() if snippet.updated_at else "",
        ])
    return output.getvalue()


def export_yaml(snippets: Sequence[Snippet]) -> str:
    lines: list[str] = []
    for i, snippet in enumerate(snippets):
        if i > 0:
            lines.append("---")
        lines.append("- id: " + (snippet.id or ""))
        lines.append("  title: " + _yaml_escape(snippet.title))
        lines.append("  content: |")
        for line in snippet.content.splitlines():
            lines.append("    " + line)
        lines.append("  language: " + snippet.language)
        if snippet.description:
            lines.append("  description: " + _yaml_escape(snippet.description))
        if snippet.tags:
            lines.append("  tags:")
            for tag in snippet.tags:
                lines.append("    - " + _yaml_escape(tag))
        lines.append("  pinned: " + str(snippet.pinned).lower())
        if snippet.created_at:
            lines.append("  created_at: " + snippet.created_at.isoformat())
        if snippet.updated_at:
            lines.append("  updated_at: " + snippet.updated_at.isoformat())
    return "\n".join(lines)


def _yaml_escape(value: str) -> str:
    needs_quoting = (
        "\n" in value
        or value.startswith((" ", "-", "[", "{", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`"))
        or '"' in value
        or "\\" in value
        or ":" in value
        or "#" in value
    )
    if needs_quoting:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return value


def export_html(snippets: Sequence[Snippet]) -> str:
    lines: list[str] = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        "<title>Snippets</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }",
        ".snippet { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }",
        ".snippet h2 { margin-top: 0; color: #333; }",
        ".meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }",
        ".tags .tag { display: inline-block; background: #e0e0e0; padding: 2px 8px; border-radius: 4px; margin-right: 5px; font-size: 0.85em; }",
        ".pinned { color: #e65100; font-weight: bold; }",
        "pre { background: #282c34; color: #abb2bf; padding: 15px; border-radius: 6px; overflow-x: auto; }",
        "code { font-family: 'Fira Code', 'Consolas', monospace; }",
        ".description { color: #555; font-style: italic; margin-bottom: 15px; }",
        "</style>",
        "</head>",
        "<body>",
    ]

    for snippet in snippets:
        lines.append('<div class="snippet">')
        lines.append(f"  <h2>{_html_escape(snippet.title)}</h2>")

        meta_parts: list[str] = []
        if snippet.pinned:
            meta_parts.append('<span class="pinned">📌 Pinned</span>')
        if snippet.language and snippet.language != "text":
            meta_parts.append(f"<span>Language: {_html_escape(snippet.language)}</span>")

        if meta_parts:
            lines.append(f'  <div class="meta">{" | ".join(meta_parts)}</div>')

        if snippet.description:
            lines.append(f'  <p class="description">{_html_escape(snippet.description)}</p>')

        if snippet.tags:
            tag_spans = "".join(f'<span class="tag">{_html_escape(t)}</span>' for t in snippet.tags)
            lines.append(f'  <div class="tags">{tag_spans}</div>')

        lines.append(f"  <pre><code>{_html_escape(snippet.content)}</code></pre>")
        lines.append("</div>")

    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines)


def _html_escape(value: str) -> str:
    return (value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;"))


_FORMAT_EXPORT_FUNCS: dict[str, Callable[[Sequence[Snippet]], str]] = {
    "json": export_json,
    "markdown": export_markdown,
    "md": export_markdown,
    "csv": export_csv,
    "yaml": export_yaml,
    "yml": export_yaml,
    "html": export_html,
}


def export(snippets: Sequence[Snippet], fmt: str = "json") -> str:
    normalized_fmt = fmt.lower()
    if normalized_fmt not in _FORMAT_EXPORT_FUNCS:
        raise ValueError(
            f"Unsupported format: {fmt}. "
            f"Supported formats: {', '.join(EXPORT_FORMATS)}"
        )
    return _FORMAT_EXPORT_FUNCS[normalized_fmt](snippets)


def export_to_file(snippets: Sequence[Snippet], file_path: str | Path, fmt: str | None = None) -> None:
    path = Path(file_path)
    if fmt is None:
        ext = path.suffix.lower().lstrip(".")
        if ext in _FORMAT_EXPORT_FUNCS:
            fmt = ext
        else:
            fmt = "json"
    content = export(snippets, fmt)
    path.write_text(content, encoding="utf-8")
