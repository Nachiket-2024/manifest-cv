from .markdown_to_latex import markdown_to_latex_body
from .templates import render_latex_document
from .tectonic_compiler import compile_latex_to_pdf


async def render_resume_pdf(resume_content: str, template_id: str) -> tuple[str, bytes]:
    """Returns (tex_source, pdf_bytes) for one resume rendered with one template."""
    body = markdown_to_latex_body(resume_content)
    tex_source = render_latex_document(template_id, body)
    pdf_bytes = await compile_latex_to_pdf(tex_source)
    return tex_source, pdf_bytes
