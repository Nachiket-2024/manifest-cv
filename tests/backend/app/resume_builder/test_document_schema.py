import pytest
from pydantic import ValidationError

from backend.app.resume_builder.document_schema import validate_document
from backend.app.resume_builder.html_renderer import render_document_html
from backend.app.resume_builder.render_service import render_document_pdf
from backend.app.resume_builder.security import validate_content
from backend.app.resume_builder.templates import template_document


@pytest.mark.parametrize("template_key", ["classic_single_column", "modern_sidebar", "compact_technical", "academic"])
def test_every_template_renders_a_bounded_pdf(template_key: str) -> None:
    document = template_document(template_key)
    pdf = render_document_pdf(document)
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.count(b"/Type /Page ") == len(document.pages)


def test_document_rejects_unsafe_style_tokens() -> None:
    document = template_document("classic_single_column").model_dump(mode="json")
    document["blocks"][0]["style"] = {"color": "red; font-size: 100px"}
    with pytest.raises(ValidationError):
        validate_document(document)


def test_builtin_templates_are_valid_documents() -> None:
    assert len(template_document("modern_sidebar").blocks) == 7
    assert len(template_document("classic_single_column").pages[0].rows[0].columns) == 1


def test_document_rejects_unreferenced_blocks() -> None:
    document = template_document("classic_single_column").model_dump(mode="json")
    document["blocks"].append({"id": "unplaced", "type": "custom_text", "title": "Unplaced", "content": {}})
    with pytest.raises(ValidationError):
        validate_document(document)


def test_document_rejects_invalid_column_widths() -> None:
    document = template_document("modern_sidebar").model_dump(mode="json")
    document["pages"][0]["rows"][0]["columns"][0]["width"] = 0.9
    with pytest.raises(ValidationError):
        validate_document(document)


def test_document_rejects_executable_content_and_escapes_html() -> None:
    document = template_document("classic_single_column").model_dump(mode="json")
    document["blocks"][0]["content"] = {"text": "<script>alert(1)</script>"}
    with pytest.raises(ValidationError):
        validate_document(document)

    document["blocks"][0]["content"] = {"text": "<b>safe text</b>"}
    validated = validate_document(document)
    assert "&lt;b&gt;safe text&lt;/b&gt;" in render_document_html(validated)


def test_renderer_preserves_columns_and_pdf_structure() -> None:
    document = template_document("modern_sidebar")
    document.blocks[0].content = {"name": "Builder User", "headline": "Engineer"}

    html = render_document_html(document)
    pdf = render_document_pdf(document)

    assert 'grid-template-columns:32.00% 68.00%' in html
    assert b"Builder User" in pdf
    assert pdf.startswith(b"%PDF-1.4")


def test_renderer_paginates_long_content_and_uses_document_style() -> None:
    document = template_document("classic_single_column")
    document.paper = "letter"
    document.style.text_color = "#112233"
    document.style.accent_color = "#aa5500"
    document.style.spacing = 1.5
    document.blocks[1].content = {"text": "Candidate achievement " * 5000}

    pdf = render_document_pdf(document)

    assert pdf.count(b"/Type /Page ") > 1
    assert b"/MediaBox [0 0 612 792]" in pdf
    assert b"0.0667 0.1333 0.2000 rg" in pdf
    assert b"0.6667 0.3333 0.0000 rg" in pdf


def test_content_rejects_unsupported_url_schemes_and_deep_nesting() -> None:
    with pytest.raises(ValueError):
        validate_content("ftp://example.com/file.pdf")

    nested: object = "value"
    for _ in range(10):
        nested = {"nested": nested}
    with pytest.raises(ValueError):
        validate_content(nested)
