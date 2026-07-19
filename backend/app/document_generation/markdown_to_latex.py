"""
Converts the plain, AI-structured Markdown resumes this app generates
(headings, bullet/numbered lists, **bold**/*italic* text, and paragraphs —
see ai_integration/prompts.py's resume generation prompt) into a LaTeX body
fragment. Deliberately narrow: it targets exactly the Markdown shapes this
app itself produces, not arbitrary Markdown.
"""
import re

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
_NUMBERED_RE = re.compile(r"^\d+\.\s+(.*)$")

# Backslash must be escaped first, before the replacement text below (which
# itself contains backslashes) gets a chance to be re-escaped. `_` and `*`
# are deliberately excluded here — they're still needed as Markdown
# bold/italic delimiters at this point; see _inline_to_latex.
_LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_ESCAPE_RE = re.compile("|".join(re.escape(c) for c in _LATEX_SPECIAL_CHARS))

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*|_(.+?)_")


def _escape_latex(text: str) -> str:
    return _ESCAPE_RE.sub(lambda m: _LATEX_SPECIAL_CHARS[m.group(0)], text)


def _inline_to_latex(text: str) -> str:
    text = _escape_latex(text)
    text = _BOLD_RE.sub(lambda m: r"\textbf{" + m.group(1) + "}", text)
    text = _ITALIC_RE.sub(lambda m: r"\textit{" + (m.group(1) or m.group(2)) + "}", text)
    # Any underscore that wasn't consumed as an italic delimiter above (e.g.
    # inside an email address or username) is literal text, not markup —
    # escape it now that no further Markdown parsing will run over it.
    text = text.replace("_", r"\_")
    return text


def markdown_to_latex_body(content: str) -> str:
    """Returns a LaTeX fragment suitable for inclusion inside a document body."""
    lines = content.splitlines()
    out: list[str] = []
    list_mode: str | None = None  # "itemize" | "enumerate" | None

    def close_list():
        nonlocal list_mode
        if list_mode is not None:
            out.append(f"\\end{{{list_mode}}}")
            list_mode = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            close_list()
            out.append("")
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            close_list()
            level = len(heading_match.group(1))
            heading_text = _inline_to_latex(heading_match.group(2))
            command = "section*" if level == 1 else "subsection*" if level == 2 else "subsubsection*"
            out.append(f"\\{command}{{{heading_text}}}")
            continue

        bullet_match = _BULLET_RE.match(stripped)
        if bullet_match:
            if list_mode != "itemize":
                close_list()
                out.append("\\begin{itemize}")
                list_mode = "itemize"
            out.append(f"\\item {_inline_to_latex(bullet_match.group(1))}")
            continue

        numbered_match = _NUMBERED_RE.match(stripped)
        if numbered_match:
            if list_mode != "enumerate":
                close_list()
                out.append("\\begin{enumerate}")
                list_mode = "enumerate"
            out.append(f"\\item {_inline_to_latex(numbered_match.group(1))}")
            continue

        close_list()
        out.append(_inline_to_latex(stripped))

    close_list()
    return "\n".join(out)
