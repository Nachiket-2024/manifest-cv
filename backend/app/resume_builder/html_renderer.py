from html import escape

from .document_schema import ResumeDocument

_CSS_FONTS = {
    "inter": "Inter, Arial, sans-serif",
    "arial": "Arial, sans-serif",
    "georgia": "Georgia, serif",
    "source_sans": "'Source Sans 3', Arial, sans-serif",
}


def render_document_html(document: ResumeDocument) -> str:
    """Render validated content into a safe print-preview document."""
    blocks = {block.id: block for block in document.blocks}
    rows: list[str] = []
    for page in document.pages:
        for row in page.rows:
            columns: list[str] = []
            for column in row.columns:
                sections: list[str] = []
                for block_id in column.section_ids:
                    block = blocks[block_id]
                    if not block.visible:
                        continue
                    content: list[str] = []
                    for key, value in block.content.items():
                        if isinstance(value, str) and value.strip():
                            tag = "h3" if key in {"role", "company", "name", "headline"} else "p"
                            content.append(f"<{tag}>{escape(value).replace(chr(10), '<br>')}</{tag}>")
                        elif isinstance(value, list) and value:
                            items = [item for item in value if isinstance(item, (str, int, float)) and str(item).strip()]
                            if items:
                                content.append("<ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in items) + "</ul>")
                    sections.append(f'<section><h2>{escape(block.title)}</h2>{"".join(content)}</section>')
                columns.append(f'<div class="column">{"".join(sections)}</div>')
            widths = " ".join(f"{column.width * 100:.2f}%" for column in row.columns)
            rows.append(f'<div class="row" style="grid-template-columns:{widths}">{"".join(columns)}</div>')
    style = document.style
    return f"""<!doctype html><html><head><meta charset=\"utf-8\"><style>
@page {{ size: {document.paper}; margin: {style.margin}in; }}
* {{ box-sizing: border-box; }} body {{ color: {style.text_color}; font-family: {_CSS_FONTS[style.font_family]}; font-size: {style.font_size}pt; line-height: {1.35 * style.spacing}; margin: 0; }}
.row {{ display:grid; gap:1.25rem; margin-bottom:1rem; }} .column {{ min-width:0; }} section {{ break-inside:avoid; margin-bottom:{style.spacing}rem; }} h2 {{ color:{style.accent_color}; font-size:1.15em; margin:.2rem 0 .35rem; }} h3 {{ font-size:1em; margin:.1rem 0; }} p {{ margin:.15rem 0; white-space:normal; }} ul {{ margin:.15rem 0; padding-left:1.2rem; }}
</style></head><body>{"".join(rows)}</body></html>"""
