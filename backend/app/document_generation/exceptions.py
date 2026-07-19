class LatexCompilationError(RuntimeError):
    """
    Raised when the tectonic LaTeX engine fails to produce a PDF (bad
    template output, missing packages, etc). Caught at the API route layer
    and turned into an HTTP 502 — the cause is the compilation toolchain,
    not a validation error in the request itself.
    """
