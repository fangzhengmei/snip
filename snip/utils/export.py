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
        if ext and ext in _FORMAT_EXPORT_FUNCS:
            fmt = ext
        elif ext:
            raise ValueError(
                f"Unknown file extension: '.{ext}'. "
                f"Supported formats: {', '.join(EXPORT_FORMATS)}. "
                f"Use --format to specify the format explicitly."
            )
        else:
            raise ValueError(
                "No file extension and no format specified. "
                f"Use --format to specify one of: {', '.join(EXPORT_FORMATS)}"
            )

    parent = path.parent
    if parent and not parent.exists():
        raise FileNotFoundError(
            f"Directory does not exist: {parent}. "
            f"Please create the directory first or choose a different path."
        )

    try:
        content = export(snippets, fmt)
        path.write_text(content, encoding="utf-8")
    except PermissionError:
        raise PermissionError(
            f"Permission denied: cannot write to '{path}'. "
            f"Please check your file permissions."
        )
    except OSError as e:
        raise OSError(
            f"Failed to write file '{path}': {e}"
        )


# ---------------------------------------------------------------------------
# Import functions
# ---------------------------------------------------------------------------

IMPORT_FORMATS = ["json", "markdown", "csv", "yaml", "yml", "md"]


def _parse_csv_value(value: str) -> Any:
    if value is None:
        return None
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def import_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    results: list[dict[str, Any]] = []
    for row in reader:
        item: dict[str, Any] = {}
        for key, value in row.items():
            item[key] = _parse_csv_value(value)
        if "tags" in item and isinstance(item["tags"], str):
            tags_str = item["tags"]
            if tags_str:
                item["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
            else:
                item["tags"] = []
        if "title" in item and "content" in item:
            results.append(item)
    return results


def _yaml_parse_quoted(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        inner = value[1:-1]
        result = []
        i = 0
        while i < len(inner):
            if inner[i] == "\\" and i + 1 < len(inner):
                next_char = inner[i + 1]
                if next_char == "n":
                    result.append("\n")
                elif next_char == "t":
                    result.append("\t")
                elif next_char == "r":
                    result.append("\r")
                else:
                    result.append(next_char)
                i += 2
            else:
                result.append(inner[i])
                i += 1
        return "".join(result)
    return value


def _yaml_parse_simple_value(value: str) -> Any:
    value = value.strip()
    if value.startswith('"'):
        return _yaml_parse_quoted(value)
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() == "null" or value == "":
        return None
    return value


def import_yaml(text: str) -> list[dict[str, Any]]:
    docs = text.split("\n---\n")
    results: list[dict[str, Any]] = []

    for doc in docs:
        lines = doc.strip().splitlines()
        if not lines:
            continue

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            indent_level = len(line) - len(stripped)

            if stripped.startswith("- ") and indent_level == 0:
                current_item: dict[str, Any] = {}
                remaining = stripped[2:]

                if ": " in remaining or remaining.endswith(":"):
                    if remaining.endswith(":"):
                        key = remaining[:-1].strip()
                        next_i = i + 1
                        is_list = False

                        while next_i < len(lines):
                            next_line = lines[next_i]
                            next_stripped = next_line.lstrip()
                            if next_stripped == "":
                                next_i += 1
                                continue
                            if next_stripped.startswith("- "):
                                is_list = True
                            break

                        if is_list:
                            list_items: list[Any] = []
                            j = next_i
                            while j < len(lines):
                                list_line = lines[j]
                                list_stripped = list_line.lstrip()
                                list_indent = len(list_line) - len(list_stripped)

                                if list_stripped == "":
                                    j += 1
                                    continue

                                if list_indent <= 0:
                                    break

                                if list_stripped.startswith("- "):
                                    item_val = list_stripped[2:].strip()
                                    if item_val == "|":
                                        multi_lines: list[str] = []
                                        k = j + 1
                                        while k < len(lines):
                                            ml_line = lines[k]
                                            ml_stripped = ml_line.lstrip()
                                            ml_indent = len(ml_line) - len(ml_stripped)
                                            if ml_stripped == "" or ml_indent > 0:
                                                multi_lines.append(ml_stripped)
                                                k += 1
                                            else:
                                                break
                                        while multi_lines and multi_lines[-1] == "":
                                            multi_lines.pop()
                                        list_items.append("\n".join(multi_lines))
                                        j = k
                                    else:
                                        list_items.append(_yaml_parse_simple_value(item_val))
                                        j += 1
                                else:
                                    j += 1
                            current_item[key] = list_items
                            i = j
                        else:
                            current_item[key] = None
                            i += 1
                    else:
                        key, val = remaining.split(": ", 1)
                        key = key.strip()
                        val = val.strip()

                        if val == "|":
                            multi_lines = []
                            j = i + 1
                            while j < len(lines):
                                ml_line = lines[j]
                                ml_stripped = ml_line.lstrip()
                                ml_indent = len(ml_line) - len(ml_stripped)

                                if ml_indent > 0 or ml_stripped == "":
                                    multi_lines.append(ml_stripped)
                                    j += 1
                                else:
                                    break
                            while multi_lines and multi_lines[-1] == "":
                                multi_lines.pop()
                            current_item[key] = "\n".join(multi_lines)
                            i = j
                        else:
                            current_item[key] = _yaml_parse_simple_value(val)
                            i += 1
                else:
                    i += 1

                while i < len(lines):
                    sub_line = lines[i]
                    sub_stripped = sub_line.lstrip()
                    sub_indent = len(sub_line) - len(sub_stripped)

                    if sub_stripped == "":
                        i += 1
                        continue

                    if sub_stripped.startswith("- ") and sub_indent == 0:
                        if current_item and (current_item.get("title") or current_item.get("content")):
                            results.append(current_item)
                        break

                    if ": " in sub_stripped or sub_stripped.endswith(":"):
                        if sub_stripped.endswith(":"):
                            key = sub_stripped[:-1].strip()
                            next_i = i + 1
                            is_list = False

                            while next_i < len(lines):
                                next_line = lines[next_i]
                                next_stripped = next_line.lstrip()
                                if next_stripped == "":
                                    next_i += 1
                                    continue
                                if next_stripped.startswith("- "):
                                    is_list = True
                                break

                            if is_list:
                                list_items = []
                                j = next_i
                                while j < len(lines):
                                    list_line = lines[j]
                                    list_stripped = list_line.lstrip()
                                    list_indent = len(list_line) - len(list_stripped)

                                    if list_stripped == "":
                                        j += 1
                                        continue

                                    if list_indent <= sub_indent:
                                        break

                                    if list_stripped.startswith("- "):
                                        item_val = list_stripped[2:].strip()
                                        if item_val == "|":
                                            multi_lines = []
                                            k = j + 1
                                            while k < len(lines):
                                                ml_line = lines[k]
                                                ml_stripped = ml_line.lstrip()
                                                ml_indent = len(ml_line) - len(ml_stripped)
                                                if ml_stripped == "" or ml_indent > list_indent + 2:
                                                    multi_lines.append(ml_stripped)
                                                    k += 1
                                                else:
                                                    break
                                            while multi_lines and multi_lines[-1] == "":
                                                multi_lines.pop()
                                            list_items.append("\n".join(multi_lines))
                                            j = k
                                        else:
                                            list_items.append(_yaml_parse_simple_value(item_val))
                                            j += 1
                                    else:
                                        j += 1
                                current_item[key] = list_items
                                i = j
                                continue

                            current_item[key] = None
                            i += 1
                        else:
                            key, val = sub_stripped.split(": ", 1)
                            key = key.strip()
                            val = val.strip()

                            if val == "|":
                                multi_lines = []
                                j = i + 1
                                while j < len(lines):
                                    ml_line = lines[j]
                                    ml_stripped = ml_line.lstrip()
                                    ml_indent = len(ml_line) - len(ml_stripped)

                                    if ml_indent > sub_indent or ml_stripped == "":
                                        multi_lines.append(ml_stripped)
                                        j += 1
                                    else:
                                        break
                                while multi_lines and multi_lines[-1] == "":
                                    multi_lines.pop()
                                current_item[key] = "\n".join(multi_lines)
                                i = j
                            else:
                                current_item[key] = _yaml_parse_simple_value(val)
                                i += 1
                    else:
                        i += 1

                if current_item and (current_item.get("title") or current_item.get("content")):
                    results.append(current_item)
            else:
                i += 1

    return results


def import_markdown(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    results: list[dict[str, Any]] = []

    current_item: dict[str, Any] | None = None
    in_code_block: bool = False
    code_block_language: str = "text"
    code_content: list[str] = []
    description_lines: list[str] = []
    tags_found: bool = False

    for line in lines:
        if line.startswith("# ") and not in_code_block:
            if current_item is not None:
                if description_lines:
                    current_item["description"] = "\n".join(description_lines).strip()
                if code_content:
                    current_item["content"] = "\n".join(code_content)
                    current_item["language"] = code_block_language or "text"
                if current_item.get("title") and current_item.get("content"):
                    results.append(current_item)

            title = line[2:].strip()
            current_item = {"title": title}
            in_code_block = False
            code_content = []
            description_lines = []
            tags_found = False

        elif line.startswith("```") and current_item is not None:
            if not in_code_block:
                lang = line[3:].strip()
                code_block_language = lang if lang else "text"
                in_code_block = True
                code_content = []
            else:
                in_code_block = False

        elif in_code_block:
            code_content.append(line)

        elif current_item is not None and line.strip() == "**Tags:**" or line.strip().startswith("**Tags:** "):
            tags_found = True
            tags_part = line.strip()[len("**Tags:**"):].strip()
            if tags_part:
                tags = [t.strip() for t in tags_part.split(",") if t.strip()]
                current_item["tags"] = tags
            else:
                current_item["tags"] = []

        elif current_item is not None and line.strip() == "---":
            pass

        elif current_item is not None and not tags_found:
            if line.strip() or description_lines:
                description_lines.append(line)

    if current_item is not None:
        if description_lines:
            current_item["description"] = "\n".join(description_lines).strip()
        if code_content:
            current_item["content"] = "\n".join(code_content)
            current_item["language"] = code_block_language or "text"
        if current_item.get("title") and current_item.get("content"):
            results.append(current_item)

    return results


_FORMAT_IMPORT_FUNCS: dict[str, Callable[[str], list[dict[str, Any]]]] = {
    "json": lambda t: json.loads(t) if t else [],
    "markdown": import_markdown,
    "md": import_markdown,
    "csv": import_csv,
    "yaml": import_yaml,
    "yml": import_yaml,
}


def import_from_string(text: str, fmt: str) -> list[dict[str, Any]]:
    normalized_fmt = fmt.lower()
    if normalized_fmt not in _FORMAT_IMPORT_FUNCS:
        raise ValueError(
            f"Unsupported format: {fmt}. "
            f"Supported formats: {', '.join(IMPORT_FORMATS)}"
        )
    try:
        return _FORMAT_IMPORT_FUNCS[normalized_fmt](text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ValueError(f"Failed to parse {fmt} format: {e}")


def import_from_file(file_path: str | Path, fmt: str | None = None) -> list[dict[str, Any]]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    text = path.read_text(encoding="utf-8")

    if fmt is None:
        ext = path.suffix.lower().lstrip(".")
        if ext and ext in _FORMAT_IMPORT_FUNCS:
            fmt = ext
        elif ext:
            raise ValueError(
                f"Unknown file extension: '.{ext}'. "
                f"Supported formats: {', '.join(IMPORT_FORMATS)}"
            )
        else:
            raise ValueError(
                "No file extension and no format specified. "
                f"Supported formats: {', '.join(IMPORT_FORMATS)}"
            )

    return import_from_string(text, fmt)
