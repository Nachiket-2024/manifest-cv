import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ...core.settings import settings

# ManifestCV's template preview route (document_routes.py) is deliberately
# rendered by the frontend inside an <iframe>/<embed> (see
# frontend/src/api/document_api.ts::resumeTemplatePreviewUrl) — the browser's
# own PDF viewer displays it in place, without a round trip through JSON/JS.
# Every other route on this API has no legitimate reason to ever be framed,
# so the DENY/'none' default below is loosened only for this one path.
_FRAMEABLE_PATH_RE = re.compile(r"^/resumes/[^/]+/templates/[^/]+/preview$")


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
        # categorically prevented at zero functional cost — except the
        # template preview route, which the frontend embeds by design.
        #
        # The frontend and backend are different origins (e.g. localhost:5173
        # vs. localhost:8000 in dev; separate hosts in production), so
        # "SAMEORIGIN" is the wrong value here — it only permits framing by a
        # document on *this response's own* origin, which the frontend never
        # is, and browsers correctly refuse to render the frame at all (blank
        # <iframe>, net::ERR_ABORTED / ERR_BLOCKED_BY_RESPONSE in devtools).
        # X-Frame-Options has no cross-browser-supported way to name a
        # specific non-same origin (its ALLOW-FROM directive is deprecated
        # and ignored by Chrome/Edge), so it's omitted entirely for this
        # route; CSP's frame-ancestors — respected by every current browser,
        # and the mechanism XFO was superseded by for exactly this case —
        # names the real frontend origin instead.
        if _FRAMEABLE_PATH_RE.match(request.url.path):
            response.headers["Content-Security-Policy"] = (
                f"default-src 'none'; frame-ancestors {settings.FRONTEND_BASE_URL}"
            )
        else:
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
