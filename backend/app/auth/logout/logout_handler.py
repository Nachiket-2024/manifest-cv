import traceback

from fastapi.responses import JSONResponse
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..refresh_token_logic.refresh_token_service import refresh_token_service
from ...logging.logging_config import get_logger
from ...audit_log.audit_log_service import log_security_event, LOGOUT

logger = get_logger(__name__)


class LogoutHandler:
    """Revokes the refresh token, clears auth cookies, and returns the logout response."""

    def __init__(self):
        self.refresh_token_service = refresh_token_service

    async def handle_logout(
        self, refresh_token: str | None, db: AsyncSession = None, request: Request | None = None
    ) -> JSONResponse:
        try:
            if not refresh_token:
                return JSONResponse(
                    content={"error": "No refresh token cookie found"},
                    status_code=400
                )

            success = await self.refresh_token_service.revoke_refresh_token(refresh_token)

            # Best-effort security audit entry for the logout outcome.
            await log_security_event(LOGOUT, db, success=success, request=request)

            if not success:
                return JSONResponse(
                    content={"error": "Invalid refresh token or already revoked"},
                    status_code=400
                )

            resp = JSONResponse(
                content={"message": "Logged out successfully"},
                status_code=200
            )

            resp.delete_cookie(key="access_token", httponly=True, secure=True, samesite="Strict")

            # path must match the path="/auth" it was set with
            # (token_cookie_handler.py), or the browser treats this as a different
            # cookie and never clears it.
            resp.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="Strict", path="/auth")

            return resp

        except Exception:
            logger.error("Error during logout logic:\n%s", traceback.format_exc())
            return JSONResponse(
                content={"error": "Internal Server Error"},
                status_code=500
            )


logout_handler = LogoutHandler()
