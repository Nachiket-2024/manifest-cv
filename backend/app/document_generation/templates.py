"""
LaTeX document templates (claude.md's Phase 3 "template preview system") —
each wraps the same converted body (markdown_to_latex.markdown_to_latex_body)
in a different preamble/visual style. Adding a new visual style means adding
one entry here; the body conversion itself never needs to change.
"""

_CLASSIC_PREAMBLE = r"""
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\pagestyle{empty}
\setlist[itemize]{leftmargin=1.2em, itemsep=2pt, topsep=2pt}
\setlist[enumerate]{leftmargin=1.5em, itemsep=2pt, topsep=2pt}
\titleformat{\section}{\large\bfseries}{}{0em}{}[\vspace{-0.4em}\hrule]
\titlespacing{\section}{0pt}{1.2em}{0.6em}
\titleformat{\subsection}{\bfseries}{}{0em}{}
\titlespacing{\subsection}{0pt}{0.8em}{0.3em}
\setcounter{secnumdepth}{0}
"""

_MODERN_PREAMBLE = r"""
\documentclass[10pt]{article}
\usepackage[margin=0.75in]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{xcolor}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{hyperref}
\definecolor{accent}{HTML}{2C5F8A}
\pagestyle{empty}
\setlist[itemize]{leftmargin=1.2em, itemsep=2pt, topsep=2pt}
\setlist[enumerate]{leftmargin=1.5em, itemsep=2pt, topsep=2pt}
\titleformat{\section}{\large\bfseries\color{accent}}{}{0em}{}
\titlespacing{\section}{0pt}{1em}{0.5em}
\titleformat{\subsection}{\bfseries\color{accent}}{}{0em}{}
\titlespacing{\subsection}{0pt}{0.7em}{0.3em}
\setcounter{secnumdepth}{0}
"""

TEMPLATES: dict[str, dict[str, str]] = {
    "classic": {"label": "Classic", "preamble": _CLASSIC_PREAMBLE},
    "modern": {"label": "Modern", "preamble": _MODERN_PREAMBLE},
}


def list_templates() -> list[dict[str, str]]:
    return [{"id": template_id, "label": meta["label"]} for template_id, meta in TEMPLATES.items()]


def render_latex_document(template_id: str, body: str) -> str:
    if template_id not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_id}")

    preamble = TEMPLATES[template_id]["preamble"]
    return f"{preamble}\n\\begin{{document}}\n{body}\n\\end{{document}}\n"
