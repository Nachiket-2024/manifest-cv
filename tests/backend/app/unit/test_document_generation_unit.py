import pytest

from backend.app.document_generation.markdown_to_latex import markdown_to_latex_body
from backend.app.document_generation.templates import (
    list_templates,
    render_latex_document,
)


def test_markdown_to_latex_handles_headings_lists_and_inline_markup():
    content = """# Experience
- **Python** & APIs
- _Remote_ work

1. Design
2. Ship

Contact: dev_user@example.com"""

    assert markdown_to_latex_body(content) == (
        "\\section*{Experience}\n"
        "\\begin{itemize}\n"
        "\\item \\textbf{Python} \\& APIs\n"
        "\\item \\textit{Remote} work\n"
        "\\end{itemize}\n"
        "\n"
        "\\begin{enumerate}\n"
        "\\item Design\n"
        "\\item Ship\n"
        "\\end{enumerate}\n"
        "\n"
        "Contact: dev\\_user@example.com"
    )


def test_markdown_to_latex_escapes_latex_special_characters():
    result = markdown_to_latex_body(r"100% {ready} \ path #1 ~ ^ $")

    assert result == r"100\% \{ready\} \textbackslash{} path \#1 \textasciitilde{} \textasciicircum{} \$"


def test_templates_expose_both_supported_styles_and_wrap_body():
    assert list_templates() == [
        {"id": "classic", "label": "Classic"},
        {"id": "modern", "label": "Modern"},
    ]
    assert render_latex_document("modern", "\\section*{Resume}").endswith(
        "\\begin{document}\n\\section*{Resume}\n\\end{document}\n"
    )


def test_render_latex_document_rejects_unknown_template():
    with pytest.raises(ValueError, match="Unknown template: missing"):
        render_latex_document("missing", "body")
