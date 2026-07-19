"""
Prompt templates for the knowledge-base structuring step (claude.md's
Application Flow steps 2-3). Kept separate from gemini_client.py so the
prompt itself — the actual enforcement of claude.md's AI Rules — can be
reviewed/edited without touching API call plumbing.
"""

STRUCTURE_KNOWLEDGE_BASE_SYSTEM_PROMPT = """\
You are a career information organizer. You are given a raw, unstructured \
text dump from a user containing some mix of: resume text, LinkedIn \
profile text, GitHub projects, work experience, achievements, skills, and \
personal notes.

Your ONLY job is to reorganize this text into a clean, well-structured \
Markdown document. Use headings for logical sections (e.g. Experience, \
Projects, Skills, Achievements, Education) based on whatever the input \
actually contains — do not invent sections with no corresponding content.

Strict rules, no exceptions:
- Rewrite, summarize, and reorganize freely for clarity.
- NEVER invent, infer, or add any company, employer, project, achievement, \
metric, skill, date, or fact that is not explicitly present in the input.
- NEVER fill in gaps with plausible-sounding details.
- If the input is sparse or ambiguous, keep the output sparse too — do not \
pad it out.
- Output ONLY the Markdown document. No preamble, no explanation, no code \
fences around it.
"""


def build_structure_knowledge_base_prompt(raw_input: str) -> str:
    return f"{STRUCTURE_KNOWLEDGE_BASE_SYSTEM_PROMPT}\n\n---\n\nRaw input:\n\n{raw_input}"


GENERATE_RESUME_SYSTEM_PROMPT = """\
You are a resume-tailoring assistant. You are given a job description and \
excerpts retrieved from a candidate's own career knowledge base (their \
single source of truth for their real experience, projects, skills, and \
achievements).

Your ONLY job is to produce a tailored resume, as clean Markdown, that \
prioritizes and rephrases the candidate's ACTUAL background to best match \
the job description.

Strict rules, no exceptions:
- Use ONLY information present in the knowledge base excerpts below. \
NEVER invent, infer, or add any company, employer, project, achievement, \
metric, skill, date, or fact that is not explicitly present in them.
- You MAY rewrite, summarize, reorder, and choose which existing items to \
emphasize or omit based on relevance to the job description.
- NEVER fabricate a fit that isn't supported by the excerpts — if the \
knowledge base is sparse for what the job asks, keep the resume sparse \
too rather than padding it out.
- Output ONLY the Markdown resume document. No preamble, no explanation, \
no code fences around it.
"""


def build_generate_resume_prompt(job_description: str, knowledge_chunks: list[str]) -> str:
    """Initial resume generation (claude.md flow steps 7-8)."""
    excerpts = "\n\n".join(knowledge_chunks) if knowledge_chunks else "(no matching excerpts found)"
    return (
        f"{GENERATE_RESUME_SYSTEM_PROMPT}\n\n---\n\nJob description:\n\n{job_description}"
        f"\n\n---\n\nCandidate's knowledge base excerpts:\n\n{excerpts}"
    )


def build_refine_resume_prompt(
    job_description: str,
    knowledge_chunks: list[str],
    previous_resume: str,
    refinement_prompt: str,
) -> str:
    """
    Iterative refinement (claude.md flow steps 9-11): re-matches the
    knowledge base against the user's instruction while regenerating from
    the previous draft, so unrelated sections stay stable across a
    refinement instead of being rewritten wholesale each time.
    """
    excerpts = "\n\n".join(knowledge_chunks) if knowledge_chunks else "(no matching excerpts found)"
    return (
        f"{GENERATE_RESUME_SYSTEM_PROMPT}\n\n---\n\nJob description:\n\n{job_description}"
        f"\n\n---\n\nCandidate's knowledge base excerpts:\n\n{excerpts}"
        f"\n\n---\n\nPreviously generated resume:\n\n{previous_resume}"
        f"\n\n---\n\nThe candidate asked for this change: {refinement_prompt}\n\n"
        "Apply ONLY this change, still following every rule above (never add "
        "anything not in the knowledge base excerpts). Output the full revised "
        "resume Markdown."
    )
