from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..resume_table.resume_model import ResumeDraft


class ResumeRepository:
    """
    Persistence layer for resume drafts. Every method is scoped by user_id
    at the query level — the caller (resume_routes.py) always passes the
    authenticated user's own id, never a caller-supplied owner field, so one
    user's drafts are never reachable via another user's requests.
    """

    @staticmethod
    async def get_by_id_and_user(draft_id: int, user_id: int, db: AsyncSession) -> ResumeDraft | None:
        stmt = select(ResumeDraft).where(ResumeDraft.id == draft_id, ResumeDraft.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(user_id: int, db: AsyncSession) -> list[ResumeDraft]:
        stmt = (
            select(ResumeDraft)
            .where(ResumeDraft.user_id == user_id)
            .order_by(ResumeDraft.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create(user_id: int, job_description: str, resume_content: str, db: AsyncSession) -> ResumeDraft:
        entry = ResumeDraft(user_id=user_id, job_description=job_description, resume_content=resume_content)
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def update(db_obj: ResumeDraft, update_data: dict, db: AsyncSession) -> ResumeDraft:
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(db_obj: ResumeDraft, db: AsyncSession) -> None:
        await db.delete(db_obj)
        await db.commit()


resume_repository = ResumeRepository()
