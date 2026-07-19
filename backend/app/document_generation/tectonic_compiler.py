import asyncio
import tempfile
from pathlib import Path

from .exceptions import LatexCompilationError

# tectonic's first-ever compile in a fresh container fetches its LaTeX
# format bundle over the network (see docker/backend.Dockerfile); a stalled
# fetch, or a pathological .tex input, would otherwise hang this coroutine
# — and the request handling it — forever. 60s comfortably covers a cold
# bundle fetch plus a normal one-page resume compile with room to spare.
_COMPILE_TIMEOUT_SECONDS = 60


async def compile_latex_to_pdf(tex_source: str) -> bytes:
    """
    Compiles a self-contained .tex document to PDF using the tectonic
    engine (installed in the backend Docker image — see
    docker/backend.Dockerfile). Runs in an isolated temp directory per
    call so concurrent compilations never collide, and nothing written by
    tectonic (its own cache aside) outlives the call.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "resume.tex"
        tex_path.write_text(tex_source, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            "tectonic", str(tex_path), "--outdir", tmpdir, "--chatter", "minimal",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_COMPILE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            # communicate() already resumed if the process exits on its own;
            # kill() only fires here if it's genuinely still running.
            proc.kill()
            await proc.wait()
            raise LatexCompilationError(
                f"tectonic did not finish within {_COMPILE_TIMEOUT_SECONDS}s"
            ) from None

        if proc.returncode != 0:
            message = (stderr or stdout).decode(errors="replace").strip()
            raise LatexCompilationError(message or "tectonic exited with a non-zero status")

        pdf_path = Path(tmpdir) / "resume.pdf"
        if not pdf_path.exists():
            raise LatexCompilationError("tectonic did not produce a PDF")
        return pdf_path.read_bytes()
