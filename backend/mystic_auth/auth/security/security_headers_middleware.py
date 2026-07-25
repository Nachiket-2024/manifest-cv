from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ...core.settings import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attaches a fixed set of security-hardening headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # X-Content-Type-Options: nosniff — stops browsers from MIME-sniffing a
        # response into executing as a different content type than declared
        # (e.g. treating a JSON error body as HTML/script).
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options / CSP default-src 'none': this is a JSON API with no
        # HTML pages of its own, so framing and inline scripts/styles are
        # categorically prevented at zero functional cost.
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # Forces browsers to only reach this origin over HTTPS for a year,
        # including subdomains — protects against protocol-downgrade and
        # cookie-sidejacking attacks on the access/refresh token cookies
        # (already secure=True, but HSTS closes the gap before the first
        # secure connection is established). Gated on ENVIRONMENT (checked
        # fresh per request, not cached, so it stays correct if settings
        # changed after import) since sending it in a non-production
        # deployment served over plain HTTP would pin HSTS for a full year
        # against real traffic sooner than intended, with no way to turn it
        # off short of a code change.
        if settings.ENVIRONMENT.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # This API never needs the browser to send a Referer header to third
        # parties, and URLs here can carry sensitive query params (e.g. OAuth2
        # state/code during the callback).
        response.headers["Referrer-Policy"] = "no-referrer"

        return response
