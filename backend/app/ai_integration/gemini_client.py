import asyncio

from google import genai
from google.genai import types

from ..core.settings import settings
from .prompts import (
    build_structure_knowledge_base_prompt,
    build_generate_resume_prompt,
    build_refine_resume_prompt,
)
from .exceptions import AIIntegrationError

# Embedding vector size — must match retrieval/qdrant_client.py's
# collection definition exactly, since Qdrant collections are fixed-size.
# gemini-embedding-001 is MRL-trained, so truncating its native output to
# this smaller dimensionality via output_dimensionality still yields a
# meaningful vector (unlike naively slicing an untrained model's output).
EMBEDDING_DIMENSIONS = 768

# Applied via asyncio.wait_for around every outbound Gemini call rather
# than the SDK's own per-request timeout option, so the behavior is
# identical (and easy to verify) across both the genai client's text and
# embedding methods without depending on SDK-version-specific config
# shapes. Without this, a stalled/slow Gemini response would hang the
# request indefinitely — the caller's own HTTP client would eventually give
# up, but this coroutine (and the connection it's serving) would not.
_REQUEST_TIMEOUT_SECONDS = 30

# Constructed lazily (on first use, not at import time) so importing this
# module never requires a valid GEMINI_API_KEY — matters for anything that
# imports the package without actually calling Gemini.
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


async def _generate_text(prompt: str, empty_result_error: str) -> str:
    """
    Shared plumbing for every plain text-generation call (structuring,
    resume generation/refinement) — keeps prompt construction (prompts.py)
    and error semantics (AIIntegrationError) consistent across callers.
    """
    client = _get_client()

    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt),
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise AIIntegrationError(
            f"Gemini content generation did not respond within {_REQUEST_TIMEOUT_SECONDS}s"
        ) from exc
    except Exception as exc:
        raise AIIntegrationError(f"Gemini content generation failed: {exc}") from exc

    text = (response.text or "").strip()
    if not text:
        raise AIIntegrationError(empty_result_error)
    return text


async def structure_knowledge_base(raw_input: str) -> str:
    """
    Reorganizes a user's raw career text dump into clean Markdown (claude.md
    Application Flow steps 2-3). Permitted: rewrite, summarize, reorganize.
    Prohibited: inventing anything not present in raw_input — enforced by
    the prompt in prompts.py; no code-level fact-checking happens here (an
    LLM call can't be made to structurally guarantee this — the prompt is
    the only lever available at this layer).
    """
    prompt = build_structure_knowledge_base_prompt(raw_input)
    return await _generate_text(prompt, "Gemini returned an empty structured knowledge base")


async def generate_resume(job_description: str, knowledge_chunks: list[str]) -> str:
    """
    Generates an initial tailored resume from semantically-matched
    knowledge base excerpts (claude.md flow steps 7-8). Same
    invent-nothing constraint as structure_knowledge_base, enforced via the
    prompt (see build_generate_resume_prompt).
    """
    prompt = build_generate_resume_prompt(job_description, knowledge_chunks)
    return await _generate_text(prompt, "Gemini returned an empty generated resume")


async def refine_resume(
    job_description: str,
    knowledge_chunks: list[str],
    previous_resume: str,
    refinement_prompt: str,
) -> str:
    """
    Regenerates a resume draft per the user's refinement instruction (flow
    steps 9-11), re-matching the knowledge base rather than only editing
    the previous text verbatim, so a request to "use different parts of
    the knowledge base" can actually pull in different excerpts.
    """
    prompt = build_refine_resume_prompt(job_description, knowledge_chunks, previous_resume, refinement_prompt)
    return await _generate_text(prompt, "Gemini returned an empty refined resume")


async def embed_text(text: str) -> list[float]:
    """
    Generates a semantic embedding vector for one chunk of text — used to
    index knowledge base sections in Qdrant (see
    retrieval/knowledge_retrieval_service.py) and to embed search queries
    against them.
    """
    client = _get_client()

    try:
        response = await asyncio.wait_for(
            client.aio.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
            ),
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise AIIntegrationError(
            f"Gemini embedding generation did not respond within {_REQUEST_TIMEOUT_SECONDS}s"
        ) from exc
    except Exception as exc:
        raise AIIntegrationError(f"Gemini embedding generation failed: {exc}") from exc

    if not response.embeddings:
        raise AIIntegrationError("Gemini returned no embedding")
    return list(response.embeddings[0].values)
