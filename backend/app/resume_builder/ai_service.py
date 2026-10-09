"""Convert the existing grounded Gemini text generation into typed blocks."""
import re

from ..ai_integration.gemini_client import generate_resume


def markdown_to_blocks(markdown: str, existing: list[dict]) -> list[dict]:
    sections: dict[str, list[str]] = {}
    current = "summary"
    sections[current] = []
    for line in markdown.splitlines():
        heading = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if heading:
            current = heading.group(1).strip().lower()
            sections.setdefault(current, [])
        elif line.strip():
            sections.setdefault(current, []).append(line.strip().lstrip("-* "))
    result = []
    for block in existing:
        candidates = [block["title"].lower(), block["type"].replace("_", " ")]
        content = sections.get(next((key for key in sections if any(candidate in key or key in candidate for candidate in candidates)), ""), [])
        result.append({**block, "content": {"text": "\n".join(content), "bullets": content if block["type"] in {"experience", "project", "skills", "custom_list"} else []}})
    return result


async def generate_structured_document(job_description: str, chunks: list[str], document: dict) -> dict:
    generated = await generate_resume(job_description, chunks)
    return {**document, "blocks": markdown_to_blocks(generated, document["blocks"])}
