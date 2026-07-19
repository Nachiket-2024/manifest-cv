class AIIntegrationError(RuntimeError):
    """
    Raised when a call to the underlying AI provider (Gemini) fails or
    returns an unusable result. Caught at the API route layer and turned
    into an HTTP 502 — never allowed to surface as a generic validation or
    server error, since the cause is an external dependency, not a bug in
    the request itself.
    """
