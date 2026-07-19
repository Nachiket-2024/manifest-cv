import traceback

from fastapi.responses import JSONResponse
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..refresh_token_logic.refresh_token_service import refresh_token_service
from ..token_logic.jwt_service import jwt_service
from ...logging.logging_config import get_logger
from ...audit_log.audit_log_service import log_security_event, LOGOUT_ALL

logger = get_logger(__name__)


class LogoutAllHandler:
    """Revokes all refresh tokens for a user and clears authentication cookies."""

    async def handle_logout_all(
        self, refresh_token: str | None, db: AsyncSession = None, request: Request | None = None
    ) -> JSONResponse:
        try:
            if not refresh_token:
                return JSONResponse(
                    content={"error": "No refresh token cookie found"},
                    status_code=400
                )

            payload = await jwt_service.verify_token(refresh_token, expected_type="refresh")

            if not payload or "email" not in payload:
                return JSONResponse(
                    content={"error": "Invalid refresh token"},
                    status_code=400
                )

            email = payload["email"]

            revoked_count = await refresh_token_service.revoke_all_tokens_for_user(email)

            # Best-effort security audit entry for the logout-all outcome.
            await log_security_event(
                LOGOUT_ALL,
                db,
                user_email=email,
                success=revoked_count > 0,
                request=request,
                metadata={"revoked_count": revoked_count},
            )

            if revoked_count == 0:
                return JSONResponse(
                    content={"error": "No tokens to revoke"},
                    status_code=400
                )

            resp = JSONResponse(
                content={"message": f"Logged out from {revoked_count} devices"},
                status_code=200
            )
            resp.delete_cookie(key="access_token", httponly=True, secure=True, samesite="Strict")
            # path must match the path="/auth" refresh_token was set with
            # (token_cookie_handler.py), or the browser treats this as a different
            # cookie and never clears the real one.
            resp.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="Strict", path="/auth")

            return resp

        except Exception:
            logger.error("Error during logout-all logic:\n%s", traceback.format_exc())
            return JSONResponse(content={"error": "Internal Server Error"}, status_code=500)


logout_all_handler = LogoutAllHandler()
