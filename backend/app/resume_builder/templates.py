from copy import deepcopy
from typing import Any

from .document_schema import ResumeDocument


def _block(block_id: str, block_type: str, title: str, content: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"id": block_id, "type": block_type, "title": title, "visible": True, "content": content or {}}


_TEMPLATES: dict[str, dict[str, Any]] = {
    "classic_single_column": {
        "version": 1, "name": "Classic", "description": "A clear ATS ready single column resume.",
        "notes": "Best for straightforward applications and dense experience.",
        "document": {"schema_version": 1, "paper": "a4", "style": {"accent_color": "#2563eb"},
            "blocks": [_block("profile", "profile_header", "Profile"), _block("summary", "summary", "Summary"),
                       _block("experience", "experience", "Experience"), _block("projects", "project", "Projects"),
                       _block("education", "education", "Education"), _block("skills", "skills", "Skills"),
                       _block("custom", "custom_text", "Additional information")],
            "pages": [{"id": "page-1", "rows": [{"id": "row-1", "columns": [{"id": "main", "width": 1, "min_width": 1, "max_width": 1,
                "section_ids": ["profile", "summary", "experience", "projects", "education", "skills", "custom"]}]}]}]},
    },
    "modern_sidebar": {
        "version": 1, "name": "Modern Sidebar", "description": "A balanced two column layout with a strong visual hierarchy.",
        "notes": "Keep the sidebar concise for best print results.",
        "document": {"schema_version": 1, "paper": "a4", "style": {"accent_color": "#0f766e"},
            "blocks": [_block("profile", "profile_header", "Profile"), _block("contact", "contact", "Contact"),
                       _block("skills", "skills", "Skills"), _block("summary", "summary", "Summary"),
                       _block("experience", "experience", "Experience"), _block("projects", "project", "Projects"),
                       _block("education", "education", "Education")],
            "pages": [{"id": "page-1", "rows": [{"id": "row-1", "columns": [
                {"id": "sidebar", "width": .32, "min_width": .24, "max_width": .45, "section_ids": ["profile", "contact", "skills"]},
                {"id": "main", "width": .68, "min_width": .55, "max_width": .76, "section_ids": ["summary", "experience", "projects", "education"]}]}]}]},
    },
    "compact_technical": {
        "version": 1, "name": "Compact Technical", "description": "A focused layout for technical roles with room for projects and tools.",
        "notes": "A good fit when your skills and shipped work need equal weight.",
        "document": {"schema_version": 1, "paper": "a4", "style": {"font_family": "source_sans", "font_size": 9.5, "accent_color": "#7c3aed", "text_color": "#1f2937", "margin": 0.5, "spacing": 0.75, "density": "compact"},
            "blocks": [_block("profile", "profile_header", "Profile"), _block("summary", "summary", "Summary"),
                       _block("skills", "skills", "Technical skills"), _block("experience", "experience", "Experience"),
                       _block("projects", "project", "Selected projects"), _block("education", "education", "Education"),
                       _block("certifications", "certifications", "Certifications")],
            "pages": [{"id": "page-1", "rows": [{"id": "row-1", "columns": [{"id": "main", "width": 1, "min_width": 1, "max_width": 1,
                "section_ids": ["profile", "summary", "skills", "experience", "projects", "education", "certifications"]}]}]}]},
    },
    "academic": {
        "version": 1, "name": "Academic", "description": "A calm, publication ready layout for research, education, and specialist work.",
        "notes": "Use this when publications, awards, and teaching need to be easy to find.",
        "document": {"schema_version": 1, "paper": "a4", "style": {"font_family": "georgia", "font_size": 10, "accent_color": "#374151", "text_color": "#111827", "margin": 0.7, "spacing": 1, "density": "comfortable"},
            "blocks": [_block("profile", "profile_header", "Profile"), _block("summary", "summary", "Research focus"),
                       _block("education", "education", "Education"), _block("experience", "experience", "Experience"),
                       _block("publications", "publications", "Publications"), _block("awards", "awards", "Awards and grants"),
                       _block("skills", "skills", "Skills"), _block("languages", "languages", "Languages")],
            "pages": [{"id": "page-1", "rows": [{"id": "row-1", "columns": [{"id": "main", "width": 1, "min_width": 1, "max_width": 1,
                "section_ids": ["profile", "summary", "education", "experience", "publications", "awards", "skills", "languages"]}]}]}]},
    },
}


def list_templates() -> list[dict[str, Any]]:
    return [{"template_key": key, **{k: v for k, v in value.items() if k != "document"}} for key, value in _TEMPLATES.items()]


def get_template(key: str) -> dict[str, Any] | None:
    value = _TEMPLATES.get(key)
    return deepcopy(value) if value else None


def template_document(key: str) -> ResumeDocument:
    value = get_template(key)
    if value is None:
        raise KeyError(key)
    return ResumeDocument.model_validate(value["document"])
