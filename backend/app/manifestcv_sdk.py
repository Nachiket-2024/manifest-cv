"""
ManifestCV's own extension surface — the counterpart to mystic-auth's
`app.sdk`, but for glue ManifestCV's route modules need that mystic-auth
has no reason to provide. Not part of mystic-auth's template; nothing here
is ever reconciled against an upstream update.

Import from HERE rather than reaching into `user_crud`/other internals
directly, for the same one-file-to-discover/one-file-to-fix reasons as
`app.sdk` itself.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from .user_crud.user_crud_collector import user_crud


async def get_user_id_by_email(email: str, db: AsyncSession) -> int | None:
    """
    Resolves a user's DB id from their email — the only stable identifier
    mystic-auth's get_current_user dependency exposes (its returned dict
    carries email/role/permissions, never an id). ManifestCV feature tables
    use user_id as their foreign key, so every owner-scoped route needs
    this lookup once per request.
    """
    user = await user_crud.get_by_email(email, db)
    return user.id if user else None
