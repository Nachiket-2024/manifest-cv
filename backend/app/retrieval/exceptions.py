class RetrievalError(RuntimeError):
    """
    Raised when a call to Qdrant fails or times out. Caught at the API
    route layer and turned into an HTTP 502 — the cause is an external
    dependency, not a bug in the request itself. Mirrors
    ai_integration.exceptions.AIIntegrationError's role for Gemini; kept
    as its own type rather than reused because it's a different upstream
    dependency, even though route handlers generally catch both the same way.
    """
