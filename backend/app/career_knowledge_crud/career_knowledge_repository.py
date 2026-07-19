from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..career_knowledge_table.career_knowledge_model import CareerKnowledgeBase


class CareerKnowledgeRepository:
    """
    Persistence layer for the single per-user career knowledge base. Every
    method is scoped by user_id at the query level — the caller
    (career_knowledge_routes.py) always passes the authenticated user's own
    id, never a caller-supplied owner field.
    """

    @staticmethod
    async def get_by_user_id(user_id: int, db: AsyncSession) -> CareerKnowledgeBase | None:
        stmt = select(CareerKnowledgeBase).where(CareerKnowledgeBase.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(user_id: int, raw_input: str, content: str, db: AsyncSession) -> CareerKnowledgeBase:
        # content is the AI-structured Markdown built from raw_input (see
        # ai_integration.gemini_client.structure_knowledge_base) — the
        # caller (career_knowledge_routes.py) generates it before calling
        # this, keeping this repository free of any AI-provider dependency.
        entry = CareerKnowledgeBase(user_id=user_id, raw_input=raw_input, content=content)
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def update(db_obj: CareerKnowledgeBase, update_data: dict, db: AsyncSession) -> CareerKnowledgeBase:
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(db_obj: CareerKnowledgeBase, db: AsyncSession) -> None:
        await db.delete(db_obj)
        await db.commit()


career_knowledge_repository = CareerKnowledgeRepository()
