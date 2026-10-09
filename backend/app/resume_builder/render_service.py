# The tuple is constructed from validated numeric style tokens; the dynamic
# model boundary otherwise widens it beyond the renderer's fixed RGB shape.
# mypy: disable-error-code=return-value

"""Bounded PDF rendering for structured resume documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from textwrap import wrap

from .document_schema import ResumeBlock, ResumeDocument, ResumeRow


@dataclass(frozen=True)
class _Line:
    text: str
    heading: bool = False


@dataclass(frozen=True)
class _PageRow:
    columns: tuple[tuple[float, tuple[_Line, ...]], ...]


_FONT_NAMES = {"inter": "Helvetica", "arial": "Helvetica", "source_sans": "Helvetica", "georgia": "Times-Roman"}


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _rgb(value: str) -> tuple[float, float, float]:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return (0.12, 0.16, 0.22)
    return tuple(int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))


def _block_lines(block: ResumeBlock, max_chars: int) -> list[_Line]:
    lines = [_Line(block.title, heading=True)]
    for value in block.content.values():
        if isinstance(value, str) and value.strip():
            lines.extend(_Line(line) for line in value.splitlines() if line.strip())
        elif isinstance(value, list):
            lines.extend(_Line(f"- {item}") for item in value if str(item).strip())
    wrapped: list[_Line] = []
    for line in lines:
        chunks = wrap(line.text, width=max_chars, replace_whitespace=False) or [""]
        wrapped.extend(_Line(chunk, heading=line.heading and index == 0) for index, chunk in enumerate(chunks))
    return wrapped + [_Line("")]


def _row_lines(row: ResumeRow, blocks: dict[str, ResumeBlock], max_chars: int) -> tuple[tuple[float, tuple[_Line, ...]], ...]:
    return tuple(
        (column.width, tuple(line for block_id in column.section_ids for line in _block_lines(blocks[block_id], max_chars) if blocks[block_id].visible))
        for column in row.columns
    )


def _paginate_rows(document: ResumeDocument, page_width: int, page_height: int) -> list[list[_PageRow]]:
    margin = int(document.style.margin * 72)
    line_height = max(9, int(11 * document.style.spacing))
    available_lines = max(1, (page_height - 2 * margin) // line_height)
    blocks = {block.id: block for block in document.blocks}
    pages: list[list[_PageRow]] = []
    for source_page in document.pages:
        pending = [_row_lines(row, blocks, max(12, (page_width - 2 * margin) // 5)) for row in source_page.rows]
        current: list[_PageRow] = []
        remaining = available_lines
        while pending:
            row = pending[0]
            row_height = max((len(lines) for _width, lines in row), default=1)
            capacity = max(1, remaining - (1 if current else 0))
            take = min(row_height, capacity)
            current.append(_PageRow(tuple((width, tuple(lines[:take])) for width, lines in row)))
            pending[0] = tuple((width, tuple(lines[take:])) for width, lines in row)
            remaining -= take + 1
            if all(not lines for _width, lines in pending[0]):
                pending.pop(0)
            if remaining <= 0 or (pending and take < row_height):
                pages.append(current)
                current, remaining = [], available_lines
        if current:
            pages.append(current)
    return pages or [[]]


def _page_stream(document: ResumeDocument, page_rows: list[_PageRow], page_width: int, page_height: int) -> bytes:
    margin = int(document.style.margin * 72)
    line_height = max(9, int(11 * document.style.spacing))
    body_rgb, accent_rgb = _rgb(document.style.text_color), _rgb(document.style.accent_color)
    font = _FONT_NAMES[document.style.font_family]
    font_resource = font.replace("-", "")
    commands = ["BT", f"/{font_resource} {document.style.font_size:g} Tf"]
    current_y = page_height - margin
    for row in page_rows:
        row_height = max((len(lines) for _width, lines in row.columns), default=1)
        x = margin
        available_width = page_width - 2 * margin
        for width, lines in row.columns:
            column_width = max(40, int(available_width * width))
            y = current_y
            for line in lines:
                rgb = accent_rgb if line.heading else body_rgb
                commands.append(f"{rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} rg")
                commands.extend([f"1 0 0 1 {x} {y} Tm", f"({_escape(line.text[:180])}) Tj"])
                y -= line_height
            x += column_width
        current_y -= row_height * line_height + line_height
    commands.append("ET")
    return "\n".join(commands).encode()


def render_document_pdf(document: ResumeDocument) -> bytes:
    """Render all content into bounded pages without silently dropping lines."""
    page_width, page_height = (612, 792) if document.paper == "letter" else (595, 842)
    streams = [_page_stream(document, rows, page_width, page_height) for rows in _paginate_rows(document, page_width, page_height)]
    objects: list[bytes] = [b""]
    page_ids: list[int] = []
    content_ids: list[int] = []
    font_name = _FONT_NAMES[document.style.font_family]
    resource_name = font_name.replace("-", "")
    for stream in streams:
        content_ids.append(len(objects) + 1)
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_ids.append(len(objects) + 1)
        objects.append(b"")
    font_id = len(objects) + 1
    objects.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /{font_name} >>".encode())
    pages_id, catalog_id = len(objects) + 1, len(objects) + 2
    objects.extend([b"", b""])
    for index, page_id in enumerate(page_ids):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /{resource_name} {font_id} 0 R >> >> /Contents {content_ids[index]} 0 R >>"
        ).encode()
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] /Count {len(page_ids)} >>".encode()
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, obj in enumerate(objects[1:], 1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(objects)} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)
