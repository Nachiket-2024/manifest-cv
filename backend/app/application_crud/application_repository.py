from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..application_table.application_model import ApplicationRecord


class ApplicationRepository:
    """
    Persistence layer for tracked applications. Every method is scoped by
    user_id at the query level — the caller (application_routes.py) always
    passes the authenticated user's own id.
    """

    @staticmethod
    async def get_by_id_and_user(application_id: int, user_id: int, db: AsyncSession) -> ApplicationRecord | None:
        stmt = select(ApplicationRecord).where(
            ApplicationRecord.id == application_id, ApplicationRecord.user_id == user_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(user_id: int, db: AsyncSession) -> list[ApplicationRecord]:
        stmt = (
            select(ApplicationRecord)
            .where(ApplicationRecord.user_id == user_id)
            .order_by(ApplicationRecord.application_date.desc(), ApplicationRecord.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create(user_id: int, fields: dict, db: AsyncSession) -> ApplicationRecord:
        entry = ApplicationRecord(user_id=user_id, **fields)
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def update(db_obj: ApplicationRecord, update_data: dict, db: AsyncSession) -> ApplicationRecord:
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(db_obj: ApplicationRecord, db: AsyncSession) -> None:
        await db.delete(db_obj)
        await db.commit()


application_repository = ApplicationRepository()
